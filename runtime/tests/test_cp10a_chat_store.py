"""CP-10a stages 0 and 1 (D-77): the chat store inventory and the one link table."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid

from kel import chat_links as links_module
from kel.chat_links import ChatLinks, resolve
from kel.chatstore import inventory, main as chatstore_main, markdown, plan_rows
from kel.core import Store


def _record(root, donor, cid):
    folder = Path(root) / 'aion-session-map'
    folder.mkdir(exist_ok=True)
    (folder / (hashlib.sha256(donor.encode()).hexdigest() + '.json')).write_text(json.dumps({donor: cid}))


def _digest(root):
    out = {}
    for path in sorted(Path(root).rglob('*.json')):
        out[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.data = Path(self.tmp.name)
        self.engine_root = self.data / 'engine'
        self.store = Store(self.engine_root)
        from kel.projects import Projects
        Projects(self.store)  # the conversations table
        env = patch.dict(os.environ, {}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop('KEL_CHAT_STORE', None)

    def _cleanup(self):
        links_module._overrides.pop(str(self.engine_root), None)
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def conversation(self, cid=None, messages=0, title='t'):
        cid = cid or str(uuid.uuid4())
        with self.store.transaction() as db:
            db.execute('INSERT INTO conversations(id,project_id,title,created) VALUES(?,?,?,?)',
                       (cid, 'default', title, time.time()))
            for index in range(messages):
                db.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)',
                           (cid, 'user' if index % 2 == 0 else 'assistant', 'words %d' % index, time.time()))
        return cid


class ConflictRuleTests(unittest.TestCase):
    def test_the_side_with_messages_wins_and_a_single_side_is_kept(self):
        weights = {'a': (True, 0), 'b': (True, 3), 'c': (False, 0)}
        weigh = weights.__getitem__
        self.assertEqual(resolve([('c', 'session-map')], weigh), ('c', 'single'))
        self.assertEqual(resolve([('a', 'session-map'), ('b', 'donor-extra')], weigh), ('b', 'has-messages'))
        self.assertEqual(resolve([('c', 'session-map'), ('a', 'donor-extra')], weigh), (None, 'none-has-messages'))
        self.assertEqual(resolve([('b', 'session-map'), ('b', 'donor-extra')], weigh), ('b', 'single'))
        weights['a'] = (True, 1)
        self.assertEqual(resolve([('a', 'session-map'), ('b', 'donor-extra')], weigh),
                         ('a', 'has-messages-precedence'), 'several with messages: the first in precedence order')


class LinkTableTests(_Base):
    def test_import_folds_session_records_then_the_legacy_map_then_donor_links(self):
        live = self.conversation(messages=2)
        dead = str(uuid.uuid4())
        empty = self.conversation()
        _record(self.engine_root, 'd-session', live)
        (self.engine_root / 'aion-conversations.json').write_text(json.dumps({'d-legacy': empty}))
        before = _digest(self.engine_root)
        links = ChatLinks(self.store)
        result = links.import_links({'d-extra': dead, 'd-session': live})
        self.assertEqual(result['conflicts'], [])
        self.assertEqual(links.live(), {'d-session': live, 'd-legacy': empty, 'd-extra': dead})
        self.assertEqual(_digest(self.engine_root), before, 'the files are never rewritten')
        again = links.import_links({'d-extra': dead, 'd-session': live})
        self.assertEqual((again['added'], again['conflicts']), (0, []), 'import is idempotent')

    def test_conflicting_links_resolve_by_the_side_that_has_messages(self):
        talked = self.conversation(messages=3)
        silent = self.conversation()
        _record(self.engine_root, 'chat-1', silent)
        _record(self.engine_root, 'chat-2', str(uuid.uuid4()))
        links = ChatLinks(self.store)
        result = links.import_links({'chat-1': talked, 'chat-2': str(uuid.uuid4())})
        self.assertEqual(links.conversation_for('chat-1'), talked, "the donor's link wins: it has the messages")
        self.assertIsNone(links.conversation_for('chat-2'), 'no side has messages: the chat is unlinked')
        self.assertEqual(sorted(c['donor'] for c in result['conflicts']), ['chat-1', 'chat-2'])
        logged = {c['donor']: c for c in links.conflicts()}
        self.assertEqual(logged['chat-1']['winner'], talked)
        self.assertEqual(len(logged['chat-2']['rows']), 2)
        self.assertTrue(all(row['retired'] for row in logged['chat-2']['rows']), 'both sides kept, retired')
        with self.store.transaction() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM chat_links WHERE donor_id='chat-2'").fetchone()[0], 2)

    def test_an_unlinked_chat_gets_a_fresh_link_that_later_imports_keep(self):
        _record(self.engine_root, 'chat', 'gone-a')
        links = ChatLinks(self.store)
        links.import_links({'chat': 'gone-b'})
        self.assertIsNone(links.conversation_for('chat'))
        fresh = str(uuid.uuid4())
        self.assertEqual(links.link('chat', fresh, 'acp'), fresh)
        links.import_links({'chat': 'gone-b'})
        self.assertEqual(links.conversation_for('chat'), fresh, 'the old sides are known: nothing re-resolves')
        self.assertEqual(links.donor_for(fresh), 'chat')

    def test_a_new_link_never_replaces_one_that_has_messages(self):
        talked = self.conversation(messages=1)
        links = ChatLinks(self.store)
        links.link('chat', talked, 'acp')
        self.assertEqual(links.link('chat', str(uuid.uuid4()), 'adopt'), talked)
        empty = str(uuid.uuid4())
        links.link('other', empty, 'acp')
        newer = str(uuid.uuid4())
        self.assertEqual(links.link('other', newer, 'adopt'), newer, 'an empty reserved link may be replaced')
        links.retire('other', 'app chat gone')
        self.assertIsNone(links.conversation_for('other'))
        with self.store.transaction() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM chat_links WHERE donor_id='other'").fetchone()[0], 2,
                             'retiring keeps the rows')

    def test_more_than_twenty_chats_all_keep_their_link(self):
        extra = {}
        for index in range(45):
            extra['donor-%02d' % index] = self.conversation(messages=1 if index % 3 else 0)
        links = ChatLinks(self.store)
        links.import_links(extra)
        self.assertEqual(links.live(), extra)
        # A new process (a restart) reads the same links from the table.
        links_module._imported.discard(str(self.store.db_path))
        self.assertEqual(ChatLinks(Store(self.engine_root)).live(), extra)


class SwitchTests(_Base):
    def test_engine_is_the_default_and_legacy_reads_the_files(self):
        cid = self.conversation(messages=1)
        _record(self.engine_root, 'chat', cid)
        links = ChatLinks(self.store)
        self.assertEqual(links.mode(), 'engine', 'D-80: the one chat store is the default')
        links.set_mode('legacy')
        self.assertEqual(links.mode(), 'legacy')
        self.assertEqual(links.resolve_donor('chat'), cid)
        self.assertEqual(links.resolve_conversation(cid), 'chat')
        self.assertEqual(links.live(), {}, 'legacy never writes the table')

    def test_env_and_the_desktop_override_win_over_the_setting(self):
        links = ChatLinks(self.store)
        links.set_mode('engine')
        self.assertEqual(links.mode(), 'engine')
        with patch.dict(os.environ, {'KEL_CHAT_STORE': 'legacy'}):
            self.assertEqual(links.mode(), 'legacy')
            links.override('engine')
            self.assertEqual(links.mode(), 'engine', 'the desktop hands its switch to the engine')
            links.override(None)
            self.assertEqual(links.mode(), 'legacy')
        with self.assertRaises(ValueError):
            links.set_mode('both')

    def test_switching_back_to_legacy_gives_the_old_answer_and_the_files_are_unchanged(self):
        talked = self.conversation(messages=2)
        _record(self.engine_root, 'chat', str(uuid.uuid4()))  # D names a conversation that is gone
        (self.engine_root / 'aion-conversations.json').write_text(json.dumps({'chat': talked}))
        links = ChatLinks(self.store)
        links.set_mode('legacy')
        before = _digest(self.engine_root)
        legacy_answer = links.resolve_donor('chat')
        links.set_mode('engine')
        self.assertEqual(links.resolve_donor('chat'), talked, 'engine: the side with messages wins')
        links.set_mode('legacy')
        self.assertEqual(links.resolve_donor('chat'), legacy_answer, 'legacy: exactly the old answer')
        self.assertEqual(_digest(self.engine_root), before)

    def test_projects_read_through_the_switch(self):
        from kel.projects import Projects
        talked = self.conversation(messages=1)
        _record(self.engine_root, 'chat', 'gone')
        projects = Projects(self.store)
        ChatLinks(self.store).import_links({'chat': talked})
        ChatLinks(self.store).set_mode('legacy')
        self.assertEqual(projects.conversation_for_donor('chat'), 'gone', 'legacy: the session record')
        ChatLinks(self.store).set_mode('engine')
        self.assertEqual(projects.conversation_for_donor('chat'), talked)
        self.assertEqual(projects.donor_for_conversation(talked), 'chat')


class RouteTests(_Base):
    def setUp(self):
        super().setUp()
        os.environ['KEL_REVIEWER'] = 'none'
        os.environ['KEL_SKIP_TELEMETRY'] = '1'
        from kel.service import Service
        self.service = Service(self.data / 'svc')
        self.service.engine.adapters = {}
        self.service.stop.set()
        self.addCleanup(self.service.shutdown)
        self.addCleanup(lambda: links_module._overrides.pop(str(self.service.store.root), None))

    def test_the_route_imports_links_and_answers_lookups(self):
        act = self.service.action
        self.assertEqual(act('/api/chat-link', {'action': 'mode'})['mode'], 'engine', 'D-80: the default')
        self.assertEqual(act('/api/chat-link', {'action': 'mode', 'override': 'legacy'})['mode'], 'legacy')
        self.assertEqual(act('/api/chat-link', {'action': 'mode', 'override': 'engine'})['mode'], 'engine')
        created = act('/api/conversation', {})['id']
        result = act('/api/chat-link', {'action': 'import', 'links': {'donor-a': created}})
        self.assertEqual(result['links'], {'donor-a': created})
        self.assertEqual(act('/api/chat-link', {'donor': 'donor-a'})['conversation'], created)
        fresh = str(uuid.uuid4())
        self.assertEqual(act('/api/chat-link', {'action': 'link', 'donor': 'donor-b', 'conversation': fresh,
                                                'source': 'acp'})['conversation'], fresh)
        self.assertEqual(self.service.projects.links.view(conversation=fresh)['donor'], 'donor-b')
        act('/api/chat-link', {'action': 'retire', 'donor': 'donor-b'})
        self.assertNotIn('donor-b', act('/api/chat-link', {})['links'])
        self.assertEqual(act('/api/chat-link', {'action': 'mode', 'override': None})['mode'], 'engine')


class InventoryTests(_Base):
    """A synthetic Data folder with every class (no real text)."""

    def donor_db(self):
        store = self.data / 'store'
        store.mkdir()
        db = sqlite3.connect(store / 'aionui-backend.db')
        db.executescript('''
            CREATE TABLE conversations(id TEXT PRIMARY KEY, name TEXT, extra TEXT, pinned INTEGER, created_at INTEGER,
                                       updated_at INTEGER, archived_at INTEGER);
            CREATE TABLE messages(id TEXT PRIMARY KEY, conversation_id TEXT, msg_id TEXT, type TEXT, content TEXT,
                                  position TEXT, status TEXT, hidden INTEGER, created_at INTEGER);''')
        return db

    def chat(self, db, donor, extra=None, rows=(), archived=None):
        db.execute('INSERT INTO conversations VALUES(?,?,?,?,?,?,?)',
                   (donor, 'Chat ' + donor, json.dumps(extra or {}), 0, 1789357421822, 1789357421822, archived))
        for index, (kind, position, text) in enumerate(rows):
            db.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?)',
                       (donor + '-%d' % index, donor, donor + '-%d' % index, kind, json.dumps({'content': text}),
                        position, 'finish', 0, 1789357421822 + index))

    def build(self):
        both = self.conversation(messages=0)
        with self.store.transaction() as db:
            db.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)', (both, 'user', 'hello', 1))
            db.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)', (both, 'assistant', 'one', 2))
            db.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)', (both, 'assistant', 'two', 3))
        engine_only = self.conversation(messages=2)
        empty = self.conversation()
        orphan = self.conversation(messages=1)
        db = self.donor_db()
        # linked: two engine replies merged into one donor row, plus a donor-only reply
        _record(self.engine_root, 'linked', both)
        self.chat(db, 'linked', rows=[('text', 'right', 'hello'), ('text', 'left', 'one\n\ntwo'),
                                      ('text', 'left', 'only here'), ('acp_tool_call', 'left', '')])
        (self.engine_root / 'aion-conversations.json').write_text(json.dumps({'engine-only': engine_only}))
        self.chat(db, 'engine-only', extra={'kel_conversation_id': engine_only})
        self.chat(db, 'linked-empty', extra={'kel_conversation_id': empty})
        self.chat(db, 'dead-empty', extra={'kel_conversation_id': str(uuid.uuid4())}, archived=1)
        _record(self.engine_root, 'dead-words', str(uuid.uuid4()))
        self.chat(db, 'dead-words', extra={'kel_conversation_id': str(uuid.uuid4())},
                  rows=[('text', 'right', 'secret words'), ('tips', 'left', 'failed')])
        self.chat(db, 'unlinked-words', rows=[('text', 'right', 'secret words')])
        self.chat(db, 'unlinked-empty')
        db.commit()
        db.close()
        return orphan

    def test_every_chat_gets_one_class_and_a_row_plan_without_text(self):
        orphan = self.build()
        donor_file = self.data / 'store' / 'aionui-backend.db'
        before = hashlib.sha256(donor_file.read_bytes()).hexdigest()
        report = inventory(self.data)
        self.assertEqual(hashlib.sha256(donor_file.read_bytes()).hexdigest(), before, 'read-only')
        classes = {c['donor_id']: c['class'] for c in report['chats']}
        self.assertEqual(classes, {'linked': 'linked', 'engine-only': 'linked-engine-only',
                                   'linked-empty': 'linked-empty', 'dead-empty': 'dead-empty',
                                   'dead-words': 'dead-donor-words', 'unlinked-words': 'unlinked-donor-words',
                                   'unlinked-empty': 'unlinked-empty'})
        linked = next(c for c in report['chats'] if c['donor_id'] == 'linked')
        self.assertEqual(linked['plan_summary'], {'same': 3, 'donor-only': 1, 'donor-tool': 1})
        dead = next(c for c in report['chats'] if c['donor_id'] == 'dead-words')
        self.assertEqual(dead['conflict']['rule'], 'none-has-messages')
        self.assertIsNone(dead['conflict']['stage1_winner'])
        self.assertEqual(report['totals']['conflicts'], 1)
        self.assertEqual(report['totals']['donor_archived'], 1)
        self.assertEqual([c['conversation'] for c in report['engine_conversations_not_linked']], [orphan])
        self.assertNotIn('secret words', json.dumps(report))
        text = markdown(report)
        self.assertNotIn('secret words', text)
        self.assertIn('Chat unlinked-words', text)
        self.assertIn("## Chats whose words exist only in the app's store (2)", text)
        self.assertIn('## Chats whose links disagree (1)', text)
        shown = inventory(self.data, show_text=True)
        self.assertIn('secret words', json.dumps(shown), '--show-text is for review only')

    def test_the_command_writes_its_reports_and_fails_on_an_unknown_class(self):
        self.build()
        out = self.data / 'report.json'
        page = self.data / 'report.md'
        self.assertEqual(chatstore_main(['inventory', '--data', str(self.data), '--json', str(out),
                                         '--markdown', str(page)]), 0)
        self.assertEqual(json.loads(out.read_text(encoding='utf-8'))['totals']['donor_chats'], 7)
        self.assertTrue(page.read_text(encoding='utf-8').startswith('# Chat store report'))
        db = sqlite3.connect(self.data / 'store' / 'aionui-backend.db')
        db.execute("INSERT INTO conversations VALUES('odd','Odd','[1]',0,1,1,NULL)")
        db.commit()
        db.close()
        self.assertEqual(chatstore_main(['inventory', '--data', str(self.data), '--json', str(out)]), 2)

    def test_the_plan_uses_the_reconcile_rule(self):
        engine = [{'seq': 1, 'role': 'user', 'text': 'a'}, {'seq': 2, 'role': 'assistant', 'text': 'b'},
                  {'seq': 3, 'role': 'assistant', 'text': 'c'}]
        donor = [{'id': 'r1', 'type': 'text', 'position': 'right', 'content': json.dumps({'content': 'a'})},
                 {'id': 'r2', 'type': 'text', 'position': 'left', 'content': json.dumps({'content': 'b\n\nextra'})}]
        plans = [(p['store'], p['plan']) for p in plan_rows(engine, donor)]
        self.assertEqual(plans, [('engine', 'same'), ('engine', 'same'), ('engine', 'engine-only'), ('donor', 'partial')])


class _EngineClient:
    """The ACP host's client, answered by a real link table (no HTTP)."""

    def __init__(self, store, conversations):
        self.data = Path(store.root)
        self.links = ChatLinks(store)
        self.conversations = conversations
        self.calls = []

    def call(self, route, payload=None):
        self.calls.append((route, payload))
        if route.startswith('/api/chat-link'):
            if payload is not None:
                return self.links.apply(payload)
            from urllib.parse import parse_qs, urlparse
            query = parse_qs(urlparse(route).query)
            return self.links.view((query.get('donor') or [None])[0], (query.get('conversation') or [None])[0])
        raise AssertionError('unexpected call ' + route)

    def state(self, conversation='main'):
        return {'conversations': [{'id': cid} for cid in self.conversations], 'messages': []}


class HostTests(_Base):
    def host(self, conversations=()):
        from kel.acp_host import ACPHost
        self.client = _EngineClient(self.store, list(conversations))
        return ACPHost(self.client, lambda event: None, .01)

    def test_engine_mode_opens_the_chat_the_table_links_not_the_session_record(self):
        talked = self.conversation(messages=2)
        stale = str(uuid.uuid4())
        _record(self.engine_root, 'chat', stale)
        before = _digest(self.engine_root)
        host = self.host([talked])
        ChatLinks(self.store).set_mode('engine')
        ChatLinks(self.store).import_links({'chat': talked})
        with patch.dict(os.environ, {'AIONUI_CONVERSATION_ID': 'chat'}):
            self.assertEqual(host.dispatch('session/new', {'cwd': str(self.data)}), {'sessionId': 'kel:' + talked})
        self.assertEqual(_digest(self.engine_root), before, 'the session record is left as it was')

    def test_legacy_mode_keeps_the_session_record_answer(self):
        talked = self.conversation(messages=2)
        stale = str(uuid.uuid4())
        _record(self.engine_root, 'chat', stale)
        host = self.host([talked])
        ChatLinks(self.store).import_links({'chat': talked})
        ChatLinks(self.store).set_mode('legacy')
        with patch.dict(os.environ, {'AIONUI_CONVERSATION_ID': 'chat'}):
            self.assertEqual(host.dispatch('session/new', {'cwd': str(self.data)}), {'sessionId': 'kel:' + stale})

    def test_engine_mode_links_a_new_chat_in_the_table_and_keeps_a_record_for_rollback(self):
        host = self.host()
        ChatLinks(self.store).set_mode('engine')
        with patch.dict(os.environ, {'AIONUI_CONVERSATION_ID': 'new-chat'}):
            session = host.dispatch('session/new', {'cwd': str(self.data)})['sessionId']
        cid = session[4:]
        self.assertEqual(ChatLinks(self.store).conversation_for('new-chat'), cid)
        record = json.loads(links_module.record_path(self.engine_root, 'new-chat').read_text())
        self.assertEqual(record, {'new-chat': cid}, 'a switch back to legacy still finds the new chat')
        # A restarted host recognises the reserved (not yet created) chat through the table.
        fresh = self.host()
        self.assertEqual(fresh.dispatch('session/load', {'sessionId': session}), {})

    def test_engine_mode_reopens_a_dead_link_as_a_reserved_chat(self):
        gone = str(uuid.uuid4())
        host = self.host()
        ChatLinks(self.store).set_mode('engine')
        ChatLinks(self.store).import_links({'chat': gone})
        with patch.dict(os.environ, {'AIONUI_CONVERSATION_ID': 'chat'}):
            self.assertEqual(host.dispatch('session/new', {'cwd': str(self.data)}), {'sessionId': 'kel:' + gone},
                             'the chat and Kel agree on one conversation; its first message creates it')

    def test_an_engine_without_the_table_means_the_legacy_files(self):
        from kel.acp_host import ACPHost
        cid = str(uuid.uuid4())
        _record(self.engine_root, 'chat', cid)

        class Old:
            data = self.engine_root

            def call(self, route, payload=None):
                raise RuntimeError('Not found')

            def state(self, conversation='main'):
                return {'conversations': [], 'messages': []}

        host = ACPHost(Old(), lambda event: None, .01)
        with patch.dict(os.environ, {'AIONUI_CONVERSATION_ID': 'chat'}):
            self.assertEqual(host.dispatch('session/new', {'cwd': str(self.data)}), {'sessionId': 'kel:' + cid})


if __name__ == '__main__':
    unittest.main()
