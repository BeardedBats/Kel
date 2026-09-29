"""D-81: the Memory folder is the agents' world.

Every AI tool reads and writes only inside `Memory` (anywhere in it, across projects) and its own
working copy; Kel's App, Data, source and Tools folders, Documents and the home folder are refused
with one plain sentence. `Memory\\Kel` is Kel's read-only mirror: settings without secrets, every chat
(archived and project-less ones too) and project knowledge, kept current and put back when changed.
A scratch copy of the installed layout only; no model is called.
"""
import contextlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

from kel import memory_folder, memory_mirror, projects, runtime_guard
from kel.core import Store

NODE = shutil.which('node')
HOOK = Path(runtime_guard.__file__).with_name('guard_hook.mjs')
REFUSAL = memory_folder.REFUSAL
from datetime import datetime  # noqa: E402
DAY = datetime.fromtimestamp(1789357421.822).strftime('%Y-%m-%d')  # the chats' local start date


class Layout(unittest.TestCase):
    """<base>\\Kel\\{App, Data\\{engine,store,host}, Kel, Tools, Memory\\Projects\\{alpha,beta}} and a home
    folder with Documents; KEL_MEMORY_ROOT points at the scratch Memory folder."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.kel = base / 'Kel'
        self.app, self.data, self.source, self.tools = (self.kel / n for n in ('App', 'Data', 'Kel', 'Tools'))
        self.engine = self.data / 'engine'
        for folder in (self.app, self.source, self.tools, self.engine, self.data / 'store', self.data / 'host'):
            folder.mkdir(parents=True)
        (self.app / 'Kel.exe').write_text('')
        (self.source / 'README.md').write_text('source')
        (self.tools / 'keys.txt').write_text('x')
        (self.engine / 'kel-credentials.json').write_text('{"a": 1}')
        self.memory = self.kel / 'Memory'
        self.alpha = self.memory / 'Projects' / 'alpha'
        self.beta = self.memory / 'Projects' / 'beta'
        for folder in (self.alpha, self.beta):
            folder.mkdir(parents=True)
        (self.beta / 'notes.md').write_text('beta notes')
        self.home = base / 'home'
        (self.home / 'Documents').mkdir(parents=True)
        (self.home / 'Documents' / 'private.txt').write_text('private')
        self.workspace = self.engine / 'repositories' / 'job'
        self.workspace.mkdir(parents=True)
        self.logs = self.engine / 'native-logs' / 'run1'
        self.temp = self.engine / 'sessions' / 'run1'
        self.temp.mkdir(parents=True)
        env = mock.patch.dict(os.environ, {'KEL_MEMORY_ROOT': str(self.memory), 'KEL_DATA_DIR': str(self.engine),
                                           'USERPROFILE': str(self.home), 'KEL_PROTECTED_PATHS': str(self.app),
                                           'TEMP': str(self.temp), 'TMP': str(self.temp)})
        env.start()
        self.addCleanup(env.stop)
        for key in ('AIONUI_DATA_DIR', 'KEL_HOST_DATA_DIR', 'KEL_PROJECTS_ROOT'):
            os.environ.pop(key, None)
        roots = mock.patch('kel.runtime_guard._credential_roots', return_value=[self.home / '.ssh'])
        roots.start()
        self.addCleanup(roots.stop)


class LocationTests(Layout):
    def test_new_projects_go_to_memory_projects(self):
        self.assertEqual(Path(projects.projects_root()), self.memory / 'Projects')
        from kel.authorize import project_creation_root
        self.assertEqual(project_creation_root(), (self.memory / 'Projects').resolve())
        folder = projects.new_project_folder('Little app')
        self.assertEqual(folder.parent, self.memory / 'Projects')

    def test_default_is_beside_the_installed_app_and_created_on_demand(self):
        os.environ.pop('KEL_MEMORY_ROOT')
        with mock.patch('kel.containment.app_roots', return_value=[self.app]):
            self.assertEqual(memory_folder.memory_root(self.engine), self.kel / 'Memory')
        shutil.rmtree(self.memory)
        with mock.patch('kel.containment.app_roots', return_value=[]):
            root = memory_folder.ensure(self.engine)  # beside Data when the app cannot be seen
        self.assertEqual(root, self.kel / 'Memory')
        self.assertTrue((root / 'Projects').is_dir() and (root / 'Kel').is_dir())

    def test_kels_own_folders_are_the_memory_folders_neighbours(self):
        names = {p.name for p in memory_folder.neighbours(self.engine)}
        self.assertEqual(names, {'App', 'Data', 'Kel', 'Tools'})


@unittest.skipUnless(NODE, 'Node.js runs the Claude Code guard hook')
class AllowListTests(Layout):
    def setUp(self):
        super().setUp()
        self.policy = runtime_guard.write_policy(self.engine, self.workspace, self.logs, self.temp)

    def hook(self, tool, args):
        payload = json.dumps({'tool_name': tool, 'tool_input': args, 'cwd': str(self.workspace),
                              'hook_event_name': 'PreToolUse'})
        out = subprocess.run([NODE, str(HOOK)], input=payload, capture_output=True, text=True, timeout=30,
                             env=dict(os.environ, KEL_GUARD_POLICY=str(self.policy)),
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)['hookSpecificOutput']['permissionDecisionReason'] if out.stdout.strip() else None

    def test_anywhere_inside_memory_is_allowed_including_across_projects(self):
        self.assertIsNone(self.hook('Write', {'file_path': str(self.alpha / 'out.md'), 'content': 'x'}))
        self.assertIsNone(self.hook('Read', {'file_path': str(self.beta / 'notes.md')}))
        self.assertIsNone(self.hook('Edit', {'file_path': str(self.beta / 'notes.md'), 'old_string': 'a', 'new_string': 'b'}))
        self.assertIsNone(self.hook('Grep', {'pattern': 'x', 'path': str(self.memory)}))
        self.assertIsNone(self.hook('Bash', {'command': 'cp "%s" "%s"' % (self.beta / 'notes.md', self.alpha / 'copy.md')}))
        self.assertIsNone(self.hook('Write', {'file_path': str(self.workspace / 'calc.py'), 'content': 'x'}))
        self.assertIsNone(self.hook('Bash', {'command': 'python -m pytest -q 2>/dev/null && git status'}))

    def test_everything_outside_memory_is_refused_in_plain_words(self):
        outside = {'Data': self.engine / 'kel-credentials.json', 'App': self.app / 'Kel.exe',
                   'Kel source': self.source / 'README.md', 'Tools': self.tools / 'keys.txt',
                   'Documents': self.home / 'Documents' / 'private.txt', 'home': self.home / 'x.txt'}
        for name, path in outside.items():
            for tool, args in (('Read', {'file_path': str(path)}), ('Write', {'file_path': str(path), 'content': 'x'}),
                               ('Bash', {'command': 'cat "%s"' % path}),
                               ('PowerShell', {'command': 'Get-Content %s' % path})):
                reason = self.hook(tool, args)
                self.assertIsNotNone(reason, '%s %s' % (tool, name))
                self.assertIn(REFUSAL, reason, '%s %s' % (tool, name))

    def test_paths_hidden_in_code_and_parent_hops_are_refused(self):
        secret = str(self.home / 'Documents' / 'private.txt').replace('\\', '/')
        self.assertIsNotNone(self.hook('Bash', {'command': "node -e \"require('fs').readFileSync('%s')\"" % secret}))
        self.assertIsNotNone(self.hook('Bash', {'command': 'cat ../../../Tools/keys.txt'}))
        self.assertIsNotNone(self.hook('Bash', {'command': 'cat ~/Documents/private.txt'}))

    def test_system_and_tool_folders_stay_readable_but_not_writable(self):
        windows = os.environ.get('SystemRoot') or os.environ.get('WINDIR')
        if not windows:
            self.skipTest('Windows only')
        self.assertIsNone(self.hook('Read', {'file_path': str(Path(windows) / 'win.ini')}))
        self.assertIsNone(self.hook('Bash', {'command': '"%s" /c echo hi' % (Path(windows) / 'System32' / 'cmd.exe')}))
        self.assertIsNone(self.hook('Bash', {'command': '/usr/bin/env python --version'}))
        self.assertIn(REFUSAL, self.hook('Write', {'file_path': str(Path(windows) / 'x.txt'), 'content': 'x'}))

    def test_the_mirror_is_readable_but_never_written(self):
        mirror = self.memory / 'Kel'
        mirror.mkdir()
        (mirror / 'settings.json').write_text('{}')
        self.assertIsNone(self.hook('Read', {'file_path': str(mirror / 'settings.json')}))
        reason = self.hook('Write', {'file_path': str(mirror / 'settings.json'), 'content': '{}'})
        self.assertIn('read-only copy', reason)
        settings = runtime_guard.claude_settings(self.policy, NODE, self.workspace)
        deny = settings['permissions']['deny']
        self.assertTrue(any(rule.startswith('Edit(') and rule.endswith('/Memory/Kel/**)') for rule in deny))
        for name in ('Tools', 'App'):
            self.assertTrue(any(rule.startswith('Read(') and ('/Kel/%s/**)' % name) in rule for rule in deny), name)
        self.assertFalse(any('/Kel/Memory/**' in rule for rule in deny))


class RequestRefusalTests(Layout):
    def test_requests_outside_memory_get_the_one_plain_sentence(self):
        for text in ('summarise %s' % (self.home / 'Documents' / 'private.txt'),
                     'copy calc.py to %s' % (self.tools / 'calc.py'),
                     "save it in Kel's data folder", 'read ~/.ssh/id_rsa'):
            self.assertEqual(runtime_guard.request_refusal(text, self.engine), REFUSAL, text)

    def test_memory_the_projects_own_folder_and_web_links_pass(self):
        own = self.home / 'Documents' / 'Kel Projects' / 'calc'
        for text in ('read %s and write a summary to %s' % (self.beta / 'notes.md', self.alpha / 'summary.md'),
                     'fix %s' % (own / 'calc.py'), 'look at https://example.com/a/b and add multiply to calc.py'):
            self.assertIsNone(runtime_guard.request_refusal(text, self.engine, own), text)

    def test_changing_kels_mirror_or_settings_is_refused(self):
        text = 'edit %s' % (self.memory / 'Kel' / 'settings.json')
        self.assertEqual(runtime_guard.request_refusal(text, self.engine), memory_folder.MIRROR_REFUSAL)
        self.assertEqual(runtime_guard.request_refusal("change Kel's settings to Ask first", self.engine),
                         memory_folder.MIRROR_REFUSAL)
        self.assertIsNone(runtime_guard.request_refusal('read %s' % (self.memory / 'Kel' / 'settings.json'), self.engine))


class MirrorTests(Layout):
    """Kel's settings, both chat stores and project knowledge, mirrored without a secret."""

    def setUp(self):
        super().setUp()
        self.store = Store(self.engine)
        from kel.context import Context
        from kel.projects import Projects
        Context(self.store)
        Projects(self.store)
        with self.store.transaction() as db:
            db.execute("INSERT INTO projects VALUES('p1','Alpha',?,'Use tabs. api_key=sk-abcdefghijklmnopqrstuv',0)",
                       (str(self.alpha),))
            db.execute("CREATE TABLE IF NOT EXISTS provider_credentials(provider TEXT, fields TEXT, credential_ref TEXT,"
                       " created REAL, updated REAL)")
            db.execute("INSERT INTO provider_credentials VALUES('anthropic','api_key','sk-ant-SECRETSECRETSECRETSECRET',0,0)")
            db.execute("CREATE TABLE IF NOT EXISTS model_prefs(scope TEXT, provider TEXT, model TEXT, updated REAL)")
            db.execute("INSERT INTO model_prefs VALUES('chat','claude','claude-opus-5-5',0)")
        self.engine_chat = str(uuid.uuid4())
        with self.store.transaction() as db:
            db.execute('INSERT INTO conversations VALUES(?,?,?,?)', (self.engine_chat, 'p1', 'Engine only chat', 1789357421))
            db.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)',
                       (self.engine_chat, 'user', 'my token is ghp_abcdefghijklmnopqrstuvwxyz123456', 1))
            db.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)',
                       (self.engine_chat, 'assistant', 'Noted, without keeping it.', 2))
        donor = sqlite3.connect(self.data / 'store' / 'aionui-backend.db')
        donor.executescript('''
            CREATE TABLE conversations(id TEXT PRIMARY KEY, name TEXT, extra TEXT, pinned INTEGER, created_at INTEGER,
                                       updated_at INTEGER, archived_at INTEGER);
            CREATE TABLE messages(id TEXT PRIMARY KEY, conversation_id TEXT, msg_id TEXT, type TEXT, content TEXT,
                                  position TEXT, status TEXT, hidden INTEGER, created_at INTEGER);''')
        for cid, name, archived, rows in (('d1', 'Plans for Friday', None, [('right', 'what is on Friday?'), ('left', 'A walk.')]),
                                          ('d2', 'Old: archived chat', 1789357421822, [('right', 'archived words')])):
            donor.execute('INSERT INTO conversations VALUES(?,?,?,?,?,?,?)', (cid, name, '{}', 0, 1789357421822,
                                                                             1789357421822, archived))
            for i, (position, text) in enumerate(rows):
                donor.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?)', ('%s-%d' % (cid, i), cid, 'm', 'text',
                              json.dumps({'content': text}), position, 'finish', 0, 1789357421822 + i))
        donor.commit()
        donor.close()
        config = {'ui.zoomFactor': 1.1, 'model.config': [{'name': 'x', 'apiKey': 'sk-live-0123456789abcdefghij'}],
                  'webui.password': 'hunter2hunter2'}
        import base64
        import urllib.parse
        (self.data / 'host' / 'config').mkdir()
        (self.data / 'host' / 'config' / 'aionui-config.txt').write_text(
            base64.b64encode(urllib.parse.quote(json.dumps(config)).encode()).decode())

    def everything(self):
        root = self.memory / 'Kel'
        return {p.relative_to(root).as_posix(): p.read_text(encoding='utf-8') for p in root.rglob('*') if p.is_file()}

    def test_secrets_are_absent(self):
        memory_mirror.sync(self.engine)
        text = '\n'.join(self.everything().values())
        for secret in ('sk-ant-SECRET', 'sk-abcdefghijklmnop', 'ghp_abcdefghij', 'sk-live-0123', 'hunter2'):
            self.assertNotIn(secret, text)
        settings = json.loads((self.memory / 'Kel' / 'settings.json').read_text(encoding='utf-8'))
        memory_mirror.assert_clean(settings)
        self.assertNotIn('provider_credentials', json.dumps(settings))
        self.assertEqual(settings['desktop']['ui.zoomFactor'], 1.1)
        self.assertEqual(settings['engine']['model_prefs'][0]['model'], 'claude-opus-5-5')
        with self.assertRaises(ValueError):
            memory_mirror.assert_clean({'a': {'api_key': 'x'}})
        with self.assertRaises(ValueError):
            memory_mirror.assert_clean({'note': 'sk-ant-abcdefghijklmnopqrstuvwxyz'})

    def test_every_chat_is_a_markdown_file_archived_and_project_less_ones_too(self):
        memory_mirror.sync(self.engine)
        names = set(self.everything())
        self.assertIn('chats/No project/%s Plans for Friday.md' % DAY, names)
        self.assertIn('chats/No project/%s Old archived chat.md' % DAY, names)
        self.assertTrue(any(n.startswith('chats/Alpha/') and n.endswith('Engine only chat.md') for n in names), names)
        friday = self.everything()['chats/No project/%s Plans for Friday.md' % DAY]
        self.assertIn('## You\n\nwhat is on Friday?', friday)
        self.assertIn('## Kel\n\nA walk.', friday)
        self.assertIn('Archived', self.everything()['chats/No project/%s Old archived chat.md' % DAY])
        self.assertIn('Use tabs.', self.everything()['knowledge/Alpha/notes.md'])

    def test_the_mirror_follows_changes(self):
        stop = threading.Event()
        self.addCleanup(stop.set)
        keeper = memory_mirror.Keeper(self.engine, stop, poll=0.05, quiet=0.1, check=0.2).start()
        deadline = time.time() + 10
        while not (self.memory / 'Kel' / 'settings.json').exists() and time.time() < deadline:
            time.sleep(0.05)
        with self.store.transaction() as db:
            db.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)',
                       (self.engine_chat, 'user', 'a brand new line', 3))
        chat = next(p for p in (self.memory / 'Kel' / 'chats' / 'Alpha').iterdir())
        while 'a brand new line' not in chat.read_text(encoding='utf-8') and time.time() < deadline:
            time.sleep(0.05)
        self.assertIn('a brand new line', chat.read_text(encoding='utf-8'))
        self.assertIsNone(keeper.error)

    def test_the_mirror_is_read_only_changes_are_put_back(self):
        memory_mirror.sync(self.engine)
        settings = self.memory / 'Kel' / 'settings.json'
        original = settings.read_text(encoding='utf-8')
        with self.assertRaises(OSError):
            settings.write_text('{"authority": "changed"}')  # marked read-only
        os.chmod(settings, 0o666)
        settings.write_text('{"authority": "changed"}')
        (self.memory / 'Kel' / 'agent-note.md').write_text('mine')
        self.assertEqual(memory_mirror.tampered(self.engine), ['agent-note.md', 'settings.json'])
        # A run's settle puts it back and says so in one sentence; the step stands.
        result = {'outcome': 'SUCCESS', 'text': 'Done.'}
        self.assertIsNone(runtime_guard.settle(self.store, None, 'run1', None, self.logs, result))
        self.assertIn('Kel put back Memory\\Kel', result['text'])
        self.assertEqual(settings.read_text(encoding='utf-8'), original)
        self.assertFalse((self.memory / 'Kel' / 'agent-note.md').exists())
        self.assertTrue(any((self.engine / memory_mirror.STATE_DIR / memory_mirror.REVERTED).iterdir()))
        self.assertEqual(memory_mirror.tampered(self.engine), [])


class CodexSandboxTests(Layout):
    """Codex 0.157.1 needs `:root` read in both Windows sandboxes; only the elevated one enforces the
    `deny` entries that keep reads out of everything around the Memory folder."""

    def profile(self, **kw):
        argv = runtime_guard.codex_config(True, None, self.workspace, self.engine, self.temp, **kw)
        return argv, next(a for a in argv if a.startswith('permissions.kel.filesystem='))

    def test_until_the_one_time_approval_codex_writes_only_memory_but_reads_are_open(self):
        argv, profile = self.profile()
        self.assertIn("'%s'=\"write\"" % self.memory, profile)
        self.assertIn("'%s'=\"write\"" % self.temp, profile)
        self.assertNotIn('deny', profile)
        if os.name == 'nt':
            self.assertIn('windows.sandbox="unelevated"', argv)
        state = memory_folder.status(self.engine)
        self.assertFalse(state['codex_reads_blocked'])
        self.assertIn('reads outside it are not yet blocked for Codex', state['codex'])

    def test_elevated_denies_kels_folders_and_the_persons_own_but_never_what_a_run_needs(self):
        (self.home / 'Desktop' / 'photos').mkdir(parents=True)
        (self.home / '.claude').mkdir()
        denied = {Path(p) for p in runtime_guard.codex_deny_paths(self.engine, self.workspace, self.temp)}
        for path in (self.app, self.source, self.tools, self.data / 'store', self.data / 'host',
                     self.engine / 'kel-credentials.json', self.home / 'Documents', self.home / 'Desktop',  # Memory is not on this Desktop
                     self.home / '.claude'):
            self.assertIn(path.resolve(), denied, path)
        for path in (self.memory, self.data, self.engine, self.workspace, self.temp, self.kel):
            self.assertFalse(any(p == path.resolve() or path.resolve().is_relative_to(p) for p in denied), path)
        argv, profile = self.profile(elevated=True)
        self.assertIn("'%s'=\"deny\"" % self.tools.resolve(), profile)
        if os.name == 'nt':
            self.assertIn('windows.sandbox="elevated"', argv)

    @unittest.skipUnless(os.name == 'nt', 'Windows sandbox')
    def test_an_elevated_run_that_finds_codex_not_ready_falls_back_without_a_prompt(self):
        from kel.appserver import CodexConnection
        from kel.host_runtime import HostConnection
        memory_folder._save_codex_state(self.engine, mode='elevated', setup='done')
        self.assertTrue(memory_folder.codex_elevated(self.engine))
        started = []

        def fake_init(conn, workspace, logs, process_argv=None):
            started.append(process_argv)
            conn.workspace, conn.logs = str(workspace), Path(logs)

        with mock.patch.object(CodexConnection, '__init__', fake_init),                 mock.patch.object(CodexConnection, 'close', lambda conn: None),                 mock.patch.object(CodexConnection, 'call', return_value={'status': 'updateRequired'}),                 mock.patch('kel.host_runtime.executable', lambda name: ['C:/bin/codex.exe']),                 mock.patch('kel.runtime_guard.codex_mcp_servers', return_value=[]):
            conn = HostConnection(self.workspace, self.logs, provider='codex')
        self.assertIn('windows.sandbox="elevated"', started[0])
        self.assertIn('windows.sandbox="unelevated"', started[1])
        self.assertFalse(conn.elevated)
        self.assertFalse(memory_folder.codex_elevated(self.engine))
        self.assertTrue(memory_folder.status(self.engine)['codex_setup_available'])


if __name__ == '__main__':
    unittest.main()
