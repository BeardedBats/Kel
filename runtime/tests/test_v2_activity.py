"""V2-08 — Activity 2.0: the historical timeline, its filters, and what a row may carry.

The timeline is a read over `events` plus the jobs the line already keeps. These pins hold it to
plain sentences, real filters, and the privacy rule: no contract, no request payload, no worker id.
"""
import json
import tempfile
import time
import unittest

from kel.activity import KINDS, sentence_for, timeline
from kel.context import Context
from kel.core import Store
from kel.engine import compile_document


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.store = Store(self.tmp.name)
        self.context = Context(self.store)
        self.project = self.context.project('Activity project', None, 'timeline tests')
        self.conversation = self.context.conversation(self.project)
        self.other = self.context.project('Activity other', None, 'timeline tests')

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def a_job(self, request='Write the acceptance note with enough text to pass.', conversation=None):
        contract = compile_document(request, required=[])
        return self.store.create(contract, conversation=conversation or self.conversation)

    def settle(self, job_id, state='CLOSED', verdict='VERIFIED', artifact=None):
        with self.store.transaction() as db:
            job = self.store._get(db, job_id)
            if artifact:
                job['milestones'][list(job['milestones'])[0]]['artifact'] = artifact
            job.update(state=state, verdict=verdict)
            self.store._save(db, job, 'test.settle')


class TimelineTests(Base):
    def test_the_timeline_is_plain_sentences_with_project_grouping(self):
        job_id = self.a_job()
        self.settle(job_id, artifact={'run_id': 'r1', 'path': 'result.md', 'sha256': 'abc'})
        result = timeline(self.store, project_id=self.project)
        rows = result['entries']
        self.assertTrue(rows, 'the timeline read nothing from a real job')
        self.assertEqual(result['kinds'], list(KINDS))
        kinds = {row['kind'] for row in rows}
        self.assertIn('work', kinds)
        for row in rows:
            self.assertIsInstance(row['what'], str)
            self.assertTrue(row['what'].strip(), 'a row without a sentence hides activity')
        started = [row for row in rows if row['type'] == 'job.created']
        self.assertTrue(started)
        self.assertEqual(started[0]['project_id'], self.project)
        self.assertTrue(started[0]['job_id'])

    def test_a_row_carries_its_result_evidence_and_recovery_hint(self):
        job_id = self.a_job()
        self.settle(job_id, state='CLOSED', verdict='FAILED',
                    artifact={'run_id': 'r1', 'path': 'result.md', 'sha256': 'deadbeef'})
        rows = [row for row in timeline(self.store, project_id=self.project)['entries']
                if row['job_id'] == job_id]
        self.assertTrue(rows)
        row = rows[0]
        self.assertTrue(row['failed'])
        self.assertTrue(row['can_retry'], 'a closed failed job offers recovery')
        self.assertEqual(row['result'], 'result.md')
        self.assertEqual(row['evidence'], 'deadbeef')
        self.assertEqual(row['state'], 'CLOSED')

    def test_filters_project_kind_failure_and_search(self):
        mine = self.a_job()
        self.settle(mine)
        theirs = self.a_job('Write something else entirely with enough text.', conversation=None)
        everything = timeline(self.store, project_id=None)
        self.assertGreaterEqual(len(everything['entries']), 2)
        only_mine = timeline(self.store, project_id=self.project)
        self.assertTrue(all(row['project_id'] in (self.project, None) for row in only_mine['entries']))
        kinds = timeline(self.store, kind='work')['entries']
        self.assertTrue(kinds, 'the work filter lost every work row')
        self.assertTrue(all(row['kind'] == 'work' for row in kinds))
        self.assertEqual(timeline(self.store, kind='learning')['entries'], [])
        self.assertTrue(timeline(self.store, query='acceptance')['entries'])
        self.assertEqual(timeline(self.store, query='nothing-matches-this-at-all')['entries'], [])
        failures = timeline(self.store, failures_only=True)['entries']
        self.assertTrue(all(row['failed'] for row in failures))
        since = timeline(self.store, since=time.time() + 60)['entries']
        self.assertEqual(since, [], 'a future window returns nothing')

    def test_the_timeline_never_copies_a_payload_into_a_row(self):
        job_id = self.a_job('Write the secret-bearing request text with enough length to matter.')
        for row in timeline(self.store, project_id=self.project)['entries']:
            self.assertNotIn('contract', row)
            self.assertNotIn('payload', row)
            self.assertNotIn('run_id', row)
            self.assertLessEqual(len(str(row.get('what'))), 220)
            self.assertNotIn('secret-bearing', str(row.get('what')) if row['type'] == 'run.claimed'
                             else '')

    def test_unknown_events_are_reported_rather_than_hidden(self):
        with self.store.transaction() as db:
            db.execute('INSERT INTO events(id,aggregate_id,revision,type,at,payload,dedupe)'
                       ' VALUES(?,?,?,?,?,?,NULL)',
                       ('ev-x', 'agg-x', 1, 'something.unmapped', time.time(), '{}'))
        rows = timeline(self.store, kind='other')['entries']
        self.assertTrue(rows, 'an unmapped event disappeared from the timeline')
        self.assertIn('something.unmapped', rows[0]['what'])

    def test_sentences_stay_plain_for_the_known_types(self):
        self.assertEqual(sentence_for('job.cancel', {}), 'This work was stopped.')
        self.assertIn('chose', sentence_for('run.claimed', {'detail': {'provider': 'codex'}}))
        self.assertIn('finished', sentence_for('worker.result_recorded',
                                               {'detail': {'outcome': 'SUCCESS'}}))
        self.assertIn('something.unmapped', sentence_for('something.unmapped', {}))
        self.assertIn('assessed', sentence_for('completion.assessed',
                                               {'detail': {'verdict': 'UNCERTAIN'}}))


if __name__ == '__main__':
    unittest.main()
