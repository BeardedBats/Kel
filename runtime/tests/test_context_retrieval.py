"""Retrieval evaluates relevant scoped records before size/recency caps."""
import contextlib
import tempfile
import unittest
from pathlib import Path

from kel.composer import Composer
from kel.context import Context
from kel.core import Store, digest
from kel.memory import Memory
from kel.projectmap import ProjectMap


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'project'
        self.root.mkdir()
        self.store = Store(Path(self.tmp.name) / 'data')
        self.context = Context(self.store)
        self.context.project('Example', root=str(self.root), project_id='p')
        self.memory = Memory(self.store)
        self.composer = Composer(self.store, self.memory, ProjectMap(self.store))

    def fact(self, topic, summary, **kwargs):
        return self.memory.record('p', 'fact', topic, {'statement': summary}, summary,
                                  source_type='repo_inspection', **kwargs)

    def refs(self, packet):
        return [s['ref'] for s in packet['sources'] if s['kind'] == 'memories']

    def test_older_relevant_fact_survives_more_than_two_hundred_new_records(self):
        wanted = self.fact('release.rollback', 'Restore the rollback snapshot before restarting.')
        for index in range(205):
            self.fact('unrelated.' + str(index), 'Coffee equipment notes number ' + str(index))
        packet = self.composer.build('p', 'How do I restore the rollback snapshot?')
        self.assertEqual(self.refs(packet), [wanted])

    def test_confirmed_decisions_survive_optional_record_cap(self):
        decisions = [self.memory.record('p', 'decision', 'choice.' + str(i), {'statement': 'Keep option ' + str(i)},
                     'Keep option ' + str(i), source_type='user_instruction', actor='user', user_confirmed=1)
                     for i in range(16)]
        packet = self.composer.build('p', 'Write the document')
        self.assertEqual(set(self.refs(packet)), set(decisions))

    def test_paraphrased_stop_query_finds_cancel_guidance_without_irrelevant_recall(self):
        wanted = self.fact('work.control', 'Cancel active background work from its card.')
        self.fact('coffee.notes', 'Coffee equipment requires cleaning.')
        packet = self.composer.build('p', 'How should I stop it?')
        self.assertEqual(self.refs(packet), [wanted])

    def test_changed_source_is_stale_and_omitted_from_context(self):
        source = self.root / 'readme.txt'
        source.write_bytes(b'old')
        mid = self.fact('deployment', 'Deploy the old build.', source_ref='readme.txt', source_digest=digest(b'old'))
        source.write_bytes(b'new')
        packet = self.composer.build('p', 'Explain deployment')
        self.assertNotIn(mid, self.refs(packet))
        self.assertEqual(packet['context_status']['freshness']['stale'], [mid])
        self.assertTrue(self.memory.proposals('p'))

    def test_outside_reference_is_never_read(self):
        from unittest.mock import patch
        (self.root.parent / 'outside.txt').write_bytes(b'prior')
        mid = self.fact('deployment', 'Prior deployment fact.', source_ref='../outside.txt', source_digest=digest(b'prior'))
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('outside source read')):
            packet = self.composer.build('p', 'Explain deployment')
        self.assertEqual(packet['context_status']['freshness']['checked'], 0)
        self.assertEqual(packet['context_status']['freshness']['unknown'], [{'ref': mid, 'state': 'unknown'}])

    def test_cross_project_record_and_forgotten_record_are_excluded(self):
        self.context.project('Other', project_id='other')
        other = self.memory.record('other', 'fact', 'deployment', {'statement': 'private'}, 'private deployment', source_type='repo_inspection')
        forgotten = self.fact('deployment', 'Forgotten deployment')
        self.memory.forget(forgotten)
        packet = self.composer.build('p', 'Explain deployment')
        self.assertNotIn(other, self.refs(packet))
        self.assertNotIn(forgotten, self.refs(packet))

    def test_chat_digest_does_not_turn_confirmed_decision_into_a_missing_file(self):
        mid = self.memory.record('p', 'decision', 'deploy.target', {'statement': 'Use staging'},
                                'Use staging for deployment.', source_type='user_instruction',
                                source_ref='chat:1', source_digest=digest(b'user statement'),
                                actor='user', user_confirmed=1)
        packet = self.composer.build('p', 'Write a guide')
        self.assertIn(mid, self.refs(packet))
        self.assertEqual(self.memory.records('p', status='stale'), [])
