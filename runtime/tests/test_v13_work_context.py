"""V1.3 Gate 6: Work-context engine surface (work endpoint, memory/map/recipe actions)."""
import contextlib
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from kel.core import PolicyError, encode
from kel.service import Service


class WorkContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ANTHROPIC_API_KEY', None)
            os.environ.pop('KEL_INTERNAL_MODEL', None)
            os.environ['KEL_SKIP_TELEMETRY'] = '1'
            os.environ['KEL_REVIEWER'] = 'none'
            self.service = Service(self.tmp.name)
        self.service.engine.adapters.clear()
        self.context = self.service.context
        self.cid = self.context.conversation('default', title='Work chat')

    def tearDown(self):
        self.service.shutdown()
        self.tmp.cleanup()

    def rooted_project(self, name='Rooted'):
        root = Path(self.tmp.name) / name.lower()
        root.mkdir(exist_ok=True)
        (root / 'package.json').write_text('{"name":"demo"}', encoding='utf-8')
        pid = self.context.project(name, root=str(root), notes='', project_id=name.lower())
        with self.service.store.transaction() as db:
            db.execute('INSERT OR REPLACE INTO project_tests VALUES(?,?)',
                       (pid, encode(['python', '-m', 'pytest'])))
        cid = self.context.conversation(project_id=pid, title=name + ' chat')
        return pid, str(root), cid

    def wait_submission(self, sid, terminal=('DISPATCHED', 'FAILED', 'INTERRUPTED')):
        deadline = time.time() + 15
        while time.time() < deadline:
            with contextlib.closing(self.service.store.connect()) as db:
                row = db.execute('SELECT state FROM submissions WHERE id=?', (sid,)).fetchone()
            if row and row['state'] in terminal:
                return row['state']
            time.sleep(.05)
        raise TimeoutError('submission did not settle')

    def assistant_texts(self, cid):
        return '\n'.join(m['text'] for m in self.service.state(cid)['messages']
                         if m['role'] == 'assistant')

    def test_work_surface_sections(self):
        from kel.memory import Memory
        from kel.projectmap import ProjectMap
        pid, root, cid = self.rooted_project()
        memory = Memory(self.service.store)
        memory.record(pid, 'fact', 'test.command', dict(command='pytest'), 'Tests run with pytest.',
                      source_type='repo_inspection', source_ref='package.json')
        ProjectMap(self.service.store).refresh(pid, reason='test')
        work = self.service._work(cid)
        self.assertEqual(work['project_id'], pid)
        self.assertEqual(len(work['memory']['records']), 1)
        record = work['memory']['records'][0]
        for key in ('id', 'type', 'topic', 'summary', 'trust', 'status', 'source_type',
                    'source_ref', 'user_confirmed'):
            self.assertIn(key, record)
        self.assertEqual(work['memory']['conflicts'], [])
        self.assertEqual(work['map']['version'], 1)
        section_names = [section['name'] for section in work['map']['sections']]
        self.assertIn('execution', section_names)
        self.assertEqual([entry['recipe_id'] for entry in work['recipes']['entries']],
                         ['audit-and-repair', 'continue-work', 'fix-bug',
                          'research-then-implement', 'ship-release'])

    def test_memory_actions_confirm_edit_retract_forget(self):
        from kel.memory import Memory
        memory = Memory(self.service.store)
        mid = memory.propose('default', 'observation', 'style.naming',
                             dict(statement='Prefers kebab-case.'),
                             'Possible naming preference.', confidence=0.4)
        self.service._memory_action({'action': 'confirm', 'conversation': self.cid, 'id': mid})
        self.assertEqual(memory.records('default', status='active')[0]['trust'], 2)
        result = self.service._memory_action({'action': 'correct', 'conversation': self.cid,
                                              'id': mid, 'summary': 'Prefers kebab-case names.'})
        new_id = result['id']
        rows = {r['id']: r for r in memory.records('default', limit=50)}
        self.assertEqual(rows[mid]['status'], 'superseded')
        self.assertEqual(rows[new_id]['summary'], 'Prefers kebab-case names.')
        self.assertEqual(rows[new_id]['supersedes'], mid)
        self.service._memory_action({'action': 'retract', 'conversation': self.cid, 'id': new_id,
                                     'reason': 'wrong'})
        self.assertEqual(rows and memory.records('default', limit=50)[0]['status'], 'retracted')
        self.service._memory_action({'action': 'forget', 'conversation': self.cid, 'id': mid})
        forgotten = [r for r in memory.records('default', limit=50) if r['id'] == mid][0]
        self.assertEqual((forgotten['value'], forgotten['summary']), ('', ''))
        with self.assertRaises(PolicyError):
            self.service._memory_action({'action': 'bogus', 'conversation': self.cid})

    def test_memory_action_wrong_project_refused(self):
        from kel.memory import Memory
        other = self.context.project('Other', project_id='other')
        memory = Memory(self.service.store)
        mid = memory.record('other', 'fact', 'x.topic', dict(statement='other'),
                            'Other project fact.', source_type='repo_inspection', source_ref='x')
        with self.assertRaises(PolicyError) as cm:
            self.service._memory_action({'action': 'confirm', 'conversation': self.cid, 'id': mid})
        self.assertIn('another project', str(cm.exception))

    def test_map_actions_refresh_and_stale(self):
        pid, root, cid = self.rooted_project('Mapcase')
        first = self.service._map_action({'action': 'refresh', 'conversation': cid})
        self.assertEqual(first['version'], 1)
        (Path(root) / 'package.json').write_text('{"name":"demo","version":"2"}', encoding='utf-8')
        second = self.service._map_action({'action': 'refresh', 'conversation': cid})
        self.assertEqual(second['version'], 2)
        self.assertIn('execution', second['note'])
        stale = self.service._map_action({'action': 'stale', 'conversation': cid,
                                          'changed': ['package.json']})
        self.assertEqual(stale['sections'], ['architecture', 'execution'])
        with self.assertRaises(PolicyError) as cm:
            self.service._map_action({'action': 'refresh', 'conversation': self.cid})
        self.assertIn('no root', str(cm.exception))
    def test_recipes_preview_and_run_with_rooted_project(self):
        pid, root, cid = self.rooted_project('Recipecase')
        preview = self.service._recipes_action({'action': 'preview', 'conversation': cid,
                                                'recipe_id': 'fix-bug', 'inputs': {'bug': 'crash'}})
        self.assertEqual(preview['kind'], 'coding')
        self.assertEqual([m['id'] for m in preview['milestones']],
                         ['reproduce', 'fix', 'verify'])
        self.assertIn('crash', preview['request'])
        self.assertIn('UNCERTAIN', preview['terminal_states'])
        sid = self.service._recipes_action({'action': 'run', 'conversation': cid,
                                            'recipe_id': 'fix-bug',
                                            'inputs': {'bug': 'crash on save'}})['submission']
        self.assertEqual(self.wait_submission(sid), 'DISPATCHED')
        jobs = [j for j in self.service.store.list_jobs() if j['conversation'] == cid]
        self.assertEqual(len(jobs), 1)
        contract = jobs[0]['contract']
        self.assertEqual(contract['recipe']['id'], 'fix-bug')
        self.assertEqual(contract['kind'], 'coding')
        self.assertEqual(contract['root'], root)

    def test_recipe_run_missing_input_asks(self):
        pid, root, cid = self.rooted_project('Askcase')
        sid = self.service._recipes_action({'action': 'run', 'conversation': cid,
                                            'recipe_id': 'fix-bug', 'inputs': {}})['submission']
        self.assertEqual(self.wait_submission(sid), 'DISPATCHED')
        self.assertIn('needs the "bug" input', self.assistant_texts(cid))
        self.assertEqual([j for j in self.service.store.list_jobs() if j['conversation'] == cid],
                         [])

    def test_recipe_preview_needs_project_without_root(self):
        preview = self.service._recipes_action({'action': 'preview', 'conversation': self.cid,
                                                'recipe_id': 'fix-bug',
                                                'inputs': {'bug': 'x'}})
        self.assertTrue(preview.get('needs_project'))
        self.assertIn('test command', preview['message'].lower())

    def test_recipe_run_document_kind_without_project(self):
        preview = self.service._recipes_action({'action': 'preview', 'conversation': self.cid,
                                                'recipe_id': 'ship-release',
                                                'inputs': {'version': '1.0.0'}})
        self.assertEqual(len(preview['milestones']), 5)
        self.assertEqual(preview['recipe']['id'], 'ship-release')
        sid = self.service._recipes_action({'action': 'run', 'conversation': self.cid,
                                            'recipe_id': 'ship-release',
                                            'inputs': {'version': '1.0.0'}})['submission']
        self.assertEqual(self.wait_submission(sid), 'DISPATCHED')
        jobs = [j for j in self.service.store.list_jobs() if j['conversation'] == self.cid]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['contract']['kind'], 'mixed')

    def test_continue_work_recipe_creates_no_job(self):
        sid = self.service._recipes_action({'action': 'run', 'conversation': self.cid,
                                            'recipe_id': 'continue-work',
                                            'inputs': {}})['submission']
        self.assertEqual(self.wait_submission(sid), 'DISPATCHED')
        self.assertIn('no unfinished work', self.assistant_texts(self.cid).lower())
        self.assertEqual(self.service.store.list_jobs(), [])
        preview = self.service._recipes_action({'action': 'preview',
                                                'conversation': self.cid,
                                                'recipe_id': 'continue-work'})
        self.assertTrue(preview['continuation'])
        self.assertEqual(preview['stages'],
                         ['resolve', 'validate', 'preserve', 'resume', 'review'])

    def test_submit_rejects_bad_recipe_payload(self):
        with self.assertRaises(PolicyError):
            self.service.submit({'text': 'x', 'conversation': self.cid, 'kind': 'recipe',
                                 'recipe': {'recipe_id': 5}})

    def test_submit_packet_carries_context_sources(self):
        from kel.memory import Memory
        memory = Memory(self.service.store)
        mid = memory.record('default', 'decision', 'garden.plan',
                            dict(statement='Plant tomatoes in spring.'),
                            'Plant tomatoes in the garden in spring.',
                            source_type='user_instruction', actor='user', user_confirmed=1)
        sid = self.service.submit({'text': 'write a plan for the garden',
                                   'conversation': self.cid})
        self.assertEqual(self.wait_submission(sid), 'DISPATCHED')
        with contextlib.closing(self.service.store.connect()) as db:
            row = db.execute('SELECT packet FROM submission_packets WHERE id=?',
                             (sid,)).fetchone()
        packet = json.loads(row['packet'])
        context = packet.get('context_packet')
        self.assertTrue(context and context.get('sources'))
        refs = [s['ref'] for s in context['sources'] if s['kind'] == 'memories']
        self.assertIn(mid, refs)
        jobs = [j for j in self.service.store.list_jobs() if j['conversation'] == self.cid]
        self.assertTrue(jobs)
        worker_refs = [s['ref'] for s in
                       jobs[0]['contract']['context']['context_packet']['sources']
                       if s['kind'] == 'memories']
        self.assertIn(mid, worker_refs)

    def test_context_packet_is_project_scoped(self):
        from kel.memory import Memory
        memory = Memory(self.service.store)
        other = self.context.project('Other', project_id='other2')
        their_id = memory.record('other2', 'decision', 'garden.plan',
                                 dict(statement='Other project secret plan.'),
                                 'Other project plan.', source_type='user_instruction',
                                 actor='user', user_confirmed=1)
        sid = self.service.submit({'text': 'write a plan for the garden',
                                   'conversation': self.cid})
        self.assertEqual(self.wait_submission(sid), 'DISPATCHED')
        with contextlib.closing(self.service.store.connect()) as db:
            row = db.execute('SELECT packet FROM submission_packets WHERE id=?',
                             (sid,)).fetchone()
        raw = row['packet']
        self.assertNotIn('Other project secret plan.', raw)
        packet = json.loads(raw)
        refs = [s['ref'] for s in packet['context_packet']['sources']
                if s['kind'] == 'memories']
        self.assertNotIn(their_id, refs)

    def test_recipes_get_and_unknown_actions(self):
        info = self.service._recipes_action({'action': 'get', 'conversation': self.cid,
                                             'recipe_id': 'fix-bug'})
        self.assertEqual(info['scope'], 'builtin')
        self.assertEqual(info['version'], '1.0.0')
        with self.assertRaises(PolicyError):
            self.service._recipes_action({'action': 'get', 'conversation': self.cid,
                                          'recipe_id': 'nope'})
        with self.assertRaises(PolicyError):
            self.service._recipes_action({'action': 'bogus', 'conversation': self.cid})


if __name__ == '__main__':
    unittest.main()
