"""V1.3 Gate 3: context composer (KEL_V1.3_ARCHITECTURE.md 3-4; CTX-01..09)."""
import json
import tempfile
import unittest
from pathlib import Path

from kel.core import PolicyError, Store
from kel.context import Context
from kel.memory import Memory
from kel.projectmap import ProjectMap
from kel.composer import Composer, fence, sanitize_context


class ComposerCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.context = Context(self.store)
        self.p1 = self.context.project('One', project_id='p1')
        self.p2 = self.context.project('Two', project_id='p2')
        self.memory = Memory(self.store)
        self.maps = ProjectMap(self.store)
        self.composer = Composer(self.store, self.memory, self.maps)
        self.cid = self.context.conversation('p1')

    def test_ctx01_relevant_decision_included(self):
        mid = self.memory.record(self.p1, 'decision', 'deploy.target',
                                 dict(statement='Deploy to staging first.'),
                                 'Deploy to staging first.',
                                 source_type='user_instruction', actor='user', user_confirmed=1)
        packet = self.composer.build(self.p1, 'How should we deploy?', conversation_id=self.cid)
        self.assertEqual(packet['sources'][0]['kind'], 'request')
        refs = [s for s in packet['sources'] if s['kind'] == 'memories']
        self.assertEqual([s['ref'] for s in refs], [mid])
        self.assertEqual(refs[0]['trust'], 2)
        self.assertIn('user-confirmed', refs[0]['reason'])

    def test_ctx02_irrelevant_memory_not_included(self):
        self.memory.record(self.p1, 'fact', 'coffee.machine',
                           dict(statement='office coffee notes'),
                           'Office coffee machine notes.', source_type='repo_inspection',
                           source_ref='x')
        packet = self.composer.build(self.p1, 'Deploy the release', conversation_id=self.cid)
        self.assertEqual([s for s in packet['sources'] if s['kind'] == 'memories'], [])

    def test_ctx03_superseded_decision_excluded(self):
        first = self.memory.record(self.p1, 'decision', 'deploy.target',
                                   dict(statement='Deploy to staging.'),
                                   'Deploy to staging.', source_type='user_instruction',
                                   actor='user', user_confirmed=1)
        second = self.memory.correct(first, value=dict(statement='Deploy to prod after review.'),
                                     summary='Deploy to prod after review.')
        packet = self.composer.build(self.p1, 'deploy target question', conversation_id=self.cid)
        refs = [s['ref'] for s in packet['sources'] if s['kind'] == 'memories']
        self.assertEqual(refs, [second])

    def test_ctx04_conflicts_surfaced(self):
        self.memory.record(self.p1, 'decision', 'deploy.target', dict(statement='Deploy to A.'),
                           'Deploy to A.', source_type='user_instruction', actor='user',
                           user_confirmed=1)
        self.memory.record(self.p1, 'decision', 'deploy.target', dict(statement='Deploy to B.'),
                           'Deploy to B.', source_type='user_instruction', actor='user',
                           user_confirmed=1)
        packet = self.composer.build(self.p1, 'deploy target decision', conversation_id=self.cid)
        self.assertEqual(len(packet['conflicts']), 1)
        annotated = [s for s in packet['sources']
                     if s['kind'] == 'memories' and 'conflict' in s['reason']]
        self.assertEqual(len(annotated), 2)
    def test_ctx05_recent_window_is_bounded(self):
        for i in range(30):
            self.store.add_message('message %d %s' % (i, 'word ' * 100), role='user',
                                   conversation=self.cid)
        packet = self.composer.build(self.p1, 'anything', conversation_id=self.cid)
        recent = [s for s in packet['sources'] if s['kind'] == 'recent_turns']
        self.assertEqual(len(recent), 1)
        self.assertLessEqual(len(recent[0]['text'].splitlines()), 16)
        self.assertLessEqual(recent[0]['chars'], 8000)
        self.assertFalse(any('transcript' in s['kind'] for s in packet['sources']))

    def test_ctx06_packet_structure_persisted(self):
        packet = self.composer.build(self.p1, 'deploy please', conversation_id=self.cid)
        row = self.composer.packet(packet['packet_id'])
        self.assertIsNotNone(row)
        stored = json.loads(row['data'])
        for entry in stored['sources']:
            self.assertIsInstance(entry['text'], dict)   # structure only, non job-linked
            self.assertIn('sha256', entry['text'])
            self.assertIn('chars', entry['text'])

    def test_ctx07_project_isolation(self):
        mine = self.memory.record(self.p1, 'fact', 'deploy.marker', dict(statement='p1 marker'),
                                  'Project one marker.', source_type='repo_inspection',
                                  source_ref='m')
        theirs = self.memory.record(self.p2, 'fact', 'deploy.marker', dict(statement='p2 marker'),
                                    'Project two marker.', source_type='repo_inspection',
                                    source_ref='m')
        packet = self.composer.build(self.p1, 'deploy marker', conversation_id=self.cid)
        refs = [s['ref'] for s in packet['sources'] if s['kind'] == 'memories']
        self.assertEqual(refs, [mine])
        self.assertNotIn(theirs, refs)

    def test_ctx08_deterministic_packet_digest(self):
        self.memory.record(self.p1, 'decision', 'deploy.target',
                           dict(statement='Deploy to staging first.'),
                           'Deploy to staging first.', source_type='user_instruction',
                           actor='user', user_confirmed=1)
        one = self.composer.build(self.p1, 'deploy?', conversation_id=self.cid)
        two = self.composer.build(self.p1, 'deploy?', conversation_id=self.cid)
        self.assertEqual(one['packet_id'], two['packet_id'])

    def test_ctx09_budget_drops_turns_records_omissions(self):
        for _ in range(5):
            self.store.add_message('y' * 350, role='user', conversation=self.cid)
        self.memory.record(self.p1, 'decision', 'deploy.target', dict(statement='staging'),
                           'Deploy to staging first.', source_type='user_instruction',
                           actor='user', user_confirmed=1)
        packet = self.composer.build(self.p1, 'deploy now', conversation_id=self.cid,
                                     budget_chars=1000)
        kinds = [s['kind'] for s in packet['sources']]
        self.assertIn('request', kinds)
        self.assertIn('memories', kinds)
        self.assertNotIn('recent_turns', kinds)
        self.assertTrue(any(o['kind'] == 'recent_turns' and o['reason'] == 'budget'
                            for o in packet['omitted']))
        with self.assertRaises(PolicyError):
            self.composer.build(self.p1, 'r' * 1500, conversation_id=self.cid, budget_chars=1000)

    def test_fence_sanitizer_mirrors_donor_behaviour(self):
        text = 'before <memory-context>\n[source: x]\nsecret\n</memory-context> after'
        self.assertEqual(sanitize_context(text), 'before  after')
        self.assertEqual(sanitize_context('A <MEMORY-CONTEXT> b </Memory-Context> C'), 'A  C')
        fenced = fence('memory:m1', 'content')
        self.assertIn('<memory-context>', fenced)
        self.assertEqual(sanitize_context(fenced), '')


if __name__ == '__main__':
    unittest.main()
