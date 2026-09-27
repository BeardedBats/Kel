"""D-54 — Projects as the one context boundary.

Migration 32 (`v2-projects`) classifies every project row and tidies the donor's plumbing without
deleting anything; `Projects` owns the active project, chat bindings and scope; the service routes
(`/api/project`, `/api/conversation`, state/work filters, Knowledge/Map/Recipes scope, Activity) are
thin calls into it.
"""
import contextlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid

from kel import projects as P
from kel.activity import timeline
from kel.context import Context
from kel.core import PolicyError, Store
from kel.engine import compile_document
from kel.projects import ALL, GENERAL, Projects, ensure_schema, job_projects


class _Temp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.base = Path(self.tmp.name)

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def folder(self, name):
        path = self.base / 'folders' / name
        path.mkdir(parents=True, exist_ok=True)
        return str(path)


class MigrationTests(_Temp):
    """An 8-row fixture shaped like the real data: General, two user projects, five plumbing rows."""

    def setUp(self):
        super().setUp()
        self.store = Store(self.base / 'engine')
        Context(self.store)  # default + main, as every real store has
        user_root = str(Path.home() / 'Code' / 'my-app')  # classification never needs it to exist
        self.rows = {
            'user-app': ('My app', user_root),
            'user-notes': ('Notes', None),
            'temp': ('Temp', tempfile.gettempdir()),
            'work': ('work', str(self.store.root)),
            'store-conv': ('store', str(self.store.root.parent / 'store' / 'conversations' / 'users' / 'x')),
            'acp-name': ('acp-temp-25613169', None),
            'acp-owner': ('acp-temp-a14ea887', None),
        }
        with self.store.transaction() as db:
            for pid, (name, root) in self.rows.items():
                db.execute('INSERT INTO projects VALUES(?,?,?,?,?)', (pid, name, root, '', time.time()))
            self.chats = {}
            for pid in self.rows:
                self.chats[pid] = [str(uuid.uuid4()) for _ in range(2)]
                for cid in self.chats[pid]:
                    db.execute('INSERT INTO conversations VALUES(?,?,?,?)', (cid, pid, 'chat', time.time()))
            # The one plumbing project that owns something (a test command) keeps its chats.
            db.execute('CREATE TABLE IF NOT EXISTS project_tests(project_id TEXT PRIMARY KEY,command TEXT)')
            db.execute('INSERT INTO project_tests VALUES(?,?)', ('acp-owner', json.dumps(['pytest'])))

    def meta(self):
        with contextlib.closing(self.store.connect()) as db:
            return {r['project_id']: dict(r) for r in db.execute('SELECT * FROM project_meta')}

    def test_only_empty_plumbing_is_moved_and_archived_and_every_move_is_logged(self):
        self.assertTrue(ensure_schema(self.store))
        meta = self.meta()
        self.assertEqual(len(meta), 8)
        self.assertEqual(meta[GENERAL]['kind'], 'general')
        for pid in ('user-app', 'user-notes'):
            self.assertEqual(meta[pid]['kind'], 'user', pid)
            self.assertIsNone(meta[pid]['archived'])
        for pid in ('temp', 'work', 'store-conv', 'acp-name', 'acp-owner'):
            self.assertEqual(meta[pid]['kind'], 'system', pid)
            self.assertIsNotNone(meta[pid]['archived'], pid)
        with contextlib.closing(self.store.connect()) as db:
            where = {r['id']: r['project_id'] for r in db.execute('SELECT id,project_id FROM conversations')}
            moves = [dict(r) for r in db.execute('SELECT * FROM project_moves')]
            projects = {r['id'] for r in db.execute('SELECT id FROM projects')}
            ledger = db.execute('SELECT * FROM schema_migrations WHERE version=32').fetchone()
            active = db.execute("SELECT value FROM project_prefs WHERE scope='active'").fetchone()['value']
        for pid in ('temp', 'work', 'store-conv', 'acp-name'):
            self.assertTrue(all(where[c] == GENERAL for c in self.chats[pid]), pid)
        self.assertTrue(all(where[c] == 'acp-owner' for c in self.chats['acp-owner']), 'an owner keeps its chats')
        self.assertTrue(all(where[c] == pid for pid in ('user-app', 'user-notes') for c in self.chats[pid]))
        self.assertEqual(len(moves), 8)
        self.assertEqual({m['to_project'] for m in moves}, {GENERAL})
        self.assertEqual({m['from_project'] for m in moves}, {'temp', 'work', 'store-conv', 'acp-name'})
        self.assertEqual(len(projects), 8, 'nothing is deleted')
        self.assertEqual(ledger['name'], 'v2-projects')
        note = json.loads(ledger['note'])
        self.assertEqual((note['chats_moved'], note['archived'], note['flagged_only'], note['user']), (8, 5, 1, 2))
        self.assertEqual(active, ALL)

    def test_the_migration_runs_once(self):
        self.assertTrue(ensure_schema(self.store))
        self.assertFalse(ensure_schema(self.store))
        with contextlib.closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM project_moves').fetchone()[0], 8)


class ProjectsTests(_Temp):
    def setUp(self):
        super().setUp()
        self.store = Store(self.base / 'engine')
        self.context = Context(self.store)
        self.projects = Projects(self.store)

    def test_a_partial_rename_keeps_folder_and_context(self):
        made = self.projects.create('Site', root=self.folder('site'), context='Use tabs.',
                                    test_command=['npm', 'test'])
        after = self.projects.update(made['id'], {'name': 'Website'})
        self.assertEqual(after['name'], 'Website')
        self.assertEqual(after['root'], made['root'])
        self.assertEqual(after['context'], 'Use tabs.')
        self.assertEqual(after['test_command'], ['npm', 'test'])
        self.assertTrue(after['has_folder'])
        self.assertEqual(after['kind'], 'user')

    def test_a_new_folder_revokes_remembered_permissions(self):
        pid = self.projects.create('Site', root=self.folder('a'))['id']
        self.context.grant(pid, {'kind': 'command', 'command': 'npm test'})
        self.assertTrue(self.context.allowed(pid, {'kind': 'command', 'command': 'npm test'}))
        self.projects.update(pid, {'context': 'only notes'})
        self.assertTrue(self.context.allowed(pid, {'kind': 'command', 'command': 'npm test'}),
                        'changing notes alone keeps permissions')
        self.projects.update(pid, {'root': self.folder('b')})
        self.assertFalse(self.context.allowed(pid, {'kind': 'command', 'command': 'npm test'}))

    def test_a_null_test_command_clears_it(self):
        pid = self.projects.create('Site', test_command=['pytest'])['id']
        self.assertEqual(self.projects.update(pid, {'test_command': None})['test_command'], None)
        with contextlib.closing(self.store.connect()) as db:
            self.assertIsNone(db.execute('SELECT 1 FROM project_tests WHERE project_id=?', (pid,)).fetchone())

    def test_set_active_rejects_archived_and_plumbing_projects(self):
        pid = self.projects.create('Old')['id']
        self.projects.archive(pid)
        with self.assertRaises(PolicyError):
            self.projects.set_active(pid)
        with self.store.transaction() as db:
            db.execute('INSERT INTO projects VALUES(?,?,?,?,?)', ('acp-x', 'acp-temp-1a2b', None, '', time.time()))
        with self.assertRaises(PolicyError):
            self.projects.set_active('acp-x')
        with self.assertRaises(PolicyError):
            self.projects.update('acp-x', {'name': 'Mine now'})
        self.assertNotIn('acp-x', [r['id'] for r in self.projects.list(include_archived=True)])
        self.assertIn('acp-x', [r['id'] for r in self.projects.list(include_archived=True, include_system=True)])
        self.assertEqual(self.projects.set_active(GENERAL), {'active': GENERAL})
        self.assertEqual(self.projects.set_active(ALL), {'active': ALL})

    def test_archiving_the_active_project_falls_back_to_all_projects(self):
        pid = self.projects.create('Site')['id']
        self.projects.set_active(pid)
        self.assertEqual(self.projects.active(), pid)
        archived = self.projects.archive(pid)
        self.assertTrue(archived['archived'])
        self.assertEqual(self.projects.active(), ALL)
        self.assertNotIn(pid, [r['id'] for r in self.projects.list()])
        self.assertIn(pid, [r['id'] for r in self.projects.list(include_archived=True)])
        self.assertFalse(self.projects.restore(pid)['archived'])

    def test_general_is_not_archivable_and_a_project_with_chats_is_not_deletable(self):
        with self.assertRaises(PolicyError):
            self.projects.archive(GENERAL)
        with self.assertRaises(PolicyError):
            self.projects.delete(GENERAL)
        pid = self.projects.create('Busy')['id']
        for _ in range(3):
            self.context.conversation(pid)
        with self.assertRaises(PolicyError) as refused:
            self.projects.delete(pid)
        self.assertEqual(str(refused.exception), 'This project still has 3 chats. Archive it instead.')
        empty = self.projects.create('Empty')['id']
        self.projects.set_active(empty)
        self.assertEqual(self.projects.delete(empty), {'ok': True, 'id': empty})
        self.assertEqual(self.projects.active(), ALL)
        with contextlib.closing(self.store.connect()) as db:
            self.assertIsNone(db.execute('SELECT 1 FROM projects WHERE id=?', (empty,)).fetchone())

    def test_resolve_new_order_is_explicit_binding_active_general(self):
        explicit = self.projects.create('Explicit')['id']
        bound = self.projects.create('Bound')['id']
        active = self.projects.create('Active')['id']
        self.assertEqual(self.projects.resolve_new(), GENERAL)
        self.projects.set_active(active)
        self.assertEqual(self.projects.resolve_new(), active)
        self.projects.bind('donor-1', bound)
        self.assertEqual(self.projects.resolve_new(None, 'donor-1'), bound)
        self.assertEqual(self.projects.resolve_new(explicit, 'donor-1'), explicit)
        self.projects.archive(bound)
        self.assertEqual(self.projects.resolve_new(None, 'donor-1'), active, 'an archived binding is skipped')
        with self.assertRaises(PolicyError):
            self.projects.resolve_new(bound)

    def test_bind_is_idempotent(self):
        pid = self.projects.create('Site')['id']
        for _ in range(3):
            self.assertEqual(self.projects.bind('donor-7', pid), {'donor': 'donor-7', 'project_id': pid})
        with contextlib.closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM project_bindings').fetchone()[0], 1)
        with self.assertRaises(PolicyError):
            self.projects.bind('', pid)

    def test_for_folder_reuses_the_live_project_and_refuses_plumbing(self):
        root = self.folder('repo')
        with patch.object(P, '_temp_roots', return_value=[]):
            first = self.projects.for_folder(root)
            self.assertEqual(first['name'], 'repo')
            self.assertEqual(self.projects.for_folder(root)['id'], first['id'])
            time.sleep(0.01)
            newer = self.projects.create('Also repo', root=root)
            self.assertEqual(self.projects.for_folder(root)['id'], newer['id'], 'the most recently updated one')
            with self.assertRaises(PolicyError):
                self.projects.for_folder(str(self.store.root))
        with self.assertRaises(PolicyError):
            self.projects.for_folder(tempfile.gettempdir())

    def test_of_a_donor_chat_is_pending_until_its_first_message(self):
        pid = self.projects.create('Site')['id']
        self.projects.bind('donor-9', pid)
        pending = self.projects.of(donor='donor-9')
        self.assertTrue(pending['pending'])
        self.assertEqual(pending['project']['id'], pid)
        cid = str(uuid.uuid4())
        folder = self.store.root / 'aion-session-map'
        folder.mkdir()
        import hashlib
        (folder / (hashlib.sha256(b'donor-9').hexdigest() + '.json')).write_text(json.dumps({'donor-9': cid}))
        self.assertEqual(self.projects.pending_project(cid), pid, 'a reserved chat resolves through its binding')
        created = self.projects.create_conversation(self.context, {'donor': 'donor-9', 'id': cid})
        self.assertEqual(created, {'id': cid, 'project_id': pid})
        settled = self.projects.of(donor='donor-9')
        self.assertFalse(settled['pending'])
        self.assertEqual((settled['conversation'], settled['project']['id']), (cid, pid))
        self.projects.archive(pid)
        self.assertTrue(self.projects.of(conversation=cid)['project']['archived'], 'the chip can say archived')

    def test_job_projects_is_the_chat_project_and_the_contract_project(self):
        job = {'conversation': 'c1', 'contract': {'project_id': 'green'}}
        self.assertEqual(job_projects(job, {'c1': GENERAL}), {GENERAL, 'green'})
        self.assertEqual(job_projects({'conversation': 'c1', 'contract': {}}, {'c1': 'p'}), {'p'})


class ServiceProjectTests(_Temp):
    def setUp(self):
        super().setUp()
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('ANTHROPIC_API_KEY', None)
        os.environ.pop('KEL_INTERNAL_MODEL', None)
        os.environ['KEL_REVIEWER'] = 'none'
        os.environ['KEL_SKIP_TELEMETRY'] = '1'
        os.environ['KEL_TURN_MODEL'] = 'none'
        from kel.service import Service
        self.service = Service(self.base / 'engine')
        self.service.engine.adapters = {}
        self.service.stop.set()  # no supervision: jobs stay where the test puts them
        self.addCleanup(self.service.shutdown)
        self.store = self.service.store

    def act(self, path, data):
        return self.service.action(path, data)

    def a_job(self, conversation, project_id=None):
        contract = compile_document('Write the acceptance note with enough text to pass.', required=[])
        if project_id:
            contract['project_id'] = project_id
        return self.store.create(contract, conversation=conversation)

    def test_project_actions_round_trip_through_the_api(self):
        made = self.act('/api/project', {'action': 'create', 'name': 'Site', 'test_command': ['pytest']})
        self.assertEqual(made['kind'], 'user')
        for key in ('id', 'name', 'root', 'has_folder', 'test_command', 'kind', 'archived', 'conversations',
                    'open_work', 'needs_you', 'updated', 'last_active'):
            self.assertIn(key, made)
        listing = self.act('/api/project', {'action': 'list'})
        self.assertEqual(listing['active'], ALL)
        self.assertEqual(listing['projects'][0]['id'], GENERAL, 'General comes first')
        self.assertEqual(self.act('/api/project', {'action': 'set_active', 'id': made['id']}), {'active': made['id']})
        self.assertEqual(self.service.state()['active_project'], made['id'])
        legacy = self.act('/api/project', {'name': 'Legacy'})
        self.assertEqual(set(legacy), {'id'})
        self.assertEqual(Projects(self.store).row(legacy['id'])['kind'], 'user')
        with self.assertRaises(PolicyError):
            self.act('/api/project', {'action': 'nonsense'})

    def test_a_donor_chat_lands_in_its_bound_project(self):
        pid = self.act('/api/project', {'action': 'create', 'name': 'Site'})['id']
        other = self.act('/api/project', {'action': 'create', 'name': 'Other'})['id']
        self.act('/api/project', {'action': 'bind', 'donor': 'donor-3', 'project': pid})
        self.act('/api/project', {'action': 'set_active', 'id': other})  # a later switch does not win
        reserved = str(uuid.uuid4())
        created = self.act('/api/conversation', {'donor': 'donor-3', 'id': reserved})
        self.assertEqual(created, {'id': reserved, 'project_id': pid})
        self.assertEqual(self.act('/api/conversation', {'id': reserved}), created, 'an existing chat keeps its project')
        fresh = self.act('/api/conversation', {})
        self.assertEqual(fresh['project_id'], other, 'no binding: the active project')

    def test_state_and_work_filter_by_project_and_a_greenfield_job_shows_in_both(self):
        pid = self.act('/api/project', {'action': 'create', 'name': 'Site'})['id']
        general_chat = self.service.context.conversation(GENERAL)
        site_chat = self.service.context.conversation(pid)
        plain = self.a_job(general_chat)
        site = self.a_job(site_chat)
        green = self.a_job(general_chat, project_id=pid)  # a greenfield job made from a General chat
        ids = lambda state: {j['id'] for j in state['jobs']}
        self.assertEqual(ids(self.service.state(ALL, pid)), {site, green})
        self.assertEqual(ids(self.service.state(ALL, GENERAL)), {plain, green})
        self.assertEqual(ids(self.service.state(ALL, ALL)), {plain, site, green})
        self.assertEqual(ids(self.service.state(ALL)), {plain, site, green})
        work_ids = lambda data: {row['job_id'] for row in data['work']['jobs']}
        site_work = self.service._work('main', pid)
        self.assertEqual(work_ids(site_work), {site, green})
        self.assertEqual(site_work['project_id'], pid)
        self.assertIsNotNone(site_work['memory'])
        everywhere = self.service._work('main', ALL)
        self.assertEqual(work_ids(everywhere), {plain, site, green})
        self.assertIsNone(everywhere['memory'])
        self.assertIsNone(everywhere['map'])
        related = {row['job_id']: row['related'] for row in everywhere['work']['jobs']}
        self.assertEqual(related[site]['project_id'], pid)
        self.assertEqual(related[green]['conversation'], general_chat)
        self.assertEqual(work_ids(self.service._work(general_chat)), {plain, green}, 'a chat still reads its own jobs')
        # Activity counts the same jobs Work does for a project.
        rows = timeline(self.store, project_id=pid)['entries']
        self.assertEqual({row['job_id'] for row in rows if row['job_id']}, work_ids(site_work))
        self.assertEqual({row['project_id'] for row in rows if row['job_id']}, {pid})
        via_api = self.act('/api/activity', {'project': pid})['entries']
        self.assertEqual({row['job_id'] for row in via_api if row['job_id']}, {site, green})

    def test_scope_refuses_writes_across_all_projects_and_to_archived_projects(self):
        pid = self.act('/api/project', {'action': 'create', 'name': 'Site'})['id']
        with self.assertRaises(PolicyError):
            self.act('/api/memory', {'action': 'forget', 'project': ALL, 'id': 'm1'})
        with self.assertRaises(PolicyError):
            self.act('/api/recipes', {'action': 'run', 'project': ALL, 'recipe_id': 'fix-bug'})
        with self.assertRaises(PolicyError) as refused:
            self.act('/api/map', {'action': 'stale', 'project': ALL})
        self.assertEqual(str(refused.exception), 'Choose a project to see its map.')
        self.assertIn('proposals', self.act('/api/memory', {'action': 'proposals', 'project': ALL}))
        listed = self.act('/api/recipes', {'action': 'list', 'project': ALL})['entries']
        self.assertTrue(any(item['scope'] == 'builtin' for item in listed))
        brief = self.act('/api/brief', {'action': 'create', 'project': pid, 'goal': 'Pick a host'})['id']
        self.assertEqual([b['brief_id'] for b in self.act('/api/brief', {'action': 'list', 'project': ALL})['briefs']],
                         [brief])
        with self.assertRaises(PolicyError):
            self.act('/api/brief', {'action': 'create', 'project': ALL, 'goal': 'Nowhere'})
        self.act('/api/project', {'action': 'archive', 'id': pid})
        self.assertIn('proposals', self.act('/api/memory', {'action': 'proposals', 'project': pid}),
                      'an archived project can still be read')
        with self.assertRaises(PolicyError):
            self.act('/api/map', {'action': 'refresh', 'project': pid})
        with self.assertRaises(PolicyError):
            self.act('/api/project', {'action': 'bind', 'donor': 'd', 'project': pid})

    def test_a_recipe_run_from_the_projects_page_lands_in_the_hidden_project_chat(self):
        pid = self.act('/api/project', {'action': 'create', 'name': 'Site'})['id']
        first = self.act('/api/recipes', {'action': 'run', 'project': pid, 'recipe_id': 'audit-and-repair'})
        self.assertTrue(first['submission'])
        second = self.act('/api/recipes', {'action': 'run', 'project': pid, 'recipe_id': 'audit-and-repair'})
        self.assertEqual(first['conversation'], second['conversation'], 'one hidden chat per project')
        self.assertEqual(self.service._project_of(first['conversation']), pid)
        rows = {c['id']: c for c in self.service.conversations()['conversations']}
        self.assertTrue(rows[first['conversation']].get('utility'))
        self.assertEqual(Projects(self.store).row(pid)['conversations'], 0, 'the hidden chat is not counted')
        chat = self.service.context.conversation(pid)
        inside = self.act('/api/recipes', {'action': 'run', 'project': pid, 'conversation': chat,
                                           'recipe_id': 'audit-and-repair'})
        self.assertEqual(inside['conversation'], chat, "a run from the project's own chat stays there")

    def test_a_coding_recipe_preview_says_what_the_project_is_missing(self):
        pid = self.act('/api/project', {'action': 'create', 'name': 'Site'})['id']
        preview = self.act('/api/recipes', {'action': 'preview', 'project': pid, 'recipe_id': 'fix-bug',
                                            'inputs': {'bug': 'the login button does nothing'}})
        self.assertTrue(preview['needs_project'])
        self.assertEqual(preview['project_id'], pid)
        self.assertEqual(preview['missing'], ['folder', 'test_command'])
        self.act('/api/project', {'action': 'update', 'id': pid, 'root': self.folder('site')})
        preview = self.act('/api/recipes', {'action': 'preview', 'project': pid, 'recipe_id': 'fix-bug',
                                            'inputs': {'bug': 'the login button does nothing'}})
        self.assertEqual(preview['missing'], ['test_command'])

    def test_a_reserved_chat_is_created_in_the_active_project(self):
        pid = self.act('/api/project', {'action': 'create', 'name': 'Site'})['id']
        self.act('/api/project', {'action': 'set_active', 'id': pid})
        reserved = str(uuid.uuid4())
        self.assertEqual(self.service._project_of(reserved), pid)
        self.assertEqual(self.service.rename_conversation(reserved, 'Plans')['id'], reserved)
        self.assertEqual(self.service._project_of(reserved), pid)


if __name__ == '__main__':
    unittest.main()
