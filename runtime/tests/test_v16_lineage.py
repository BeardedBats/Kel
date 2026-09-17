"""V1.6 artifact lineage — engine verification.

Every produced work artifact gets a durable provenance row (project, conversation, job, milestone,
run, originating user turn, filename, digest, time) written in the same transaction as the artifact
itself. Replacing an artifact (a later run) chains the previous version instead of losing it, and
every version's text stays readable and integrity-checked. Scoped per job; versions ordered newest
first; a renamed milestone file keeps the chain.
"""
import contextlib
import json
import tempfile
import unittest
from pathlib import Path

from kel.context import Context
from kel.core import PolicyError, Store


def contract(request='Do the thing', filename='result.md', checks=None):
    return {'request': request,
            'milestones': [{'id': 'a', 'objective': 'Draft the thing', 'filename': filename,
                            'checks': checks or [{'kind': 'min_chars', 'value': 4}],
                            'depends_on': []}]}


class LineageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        Context(self.store).project('General', project_id='default')

    def produce(self, job, text, mid='a', event='e'):
        run = self.store.claim(job, mid)
        self.store.enqueue_result(event, run['id'], run['epoch'],
                                  {'outcome': 'SUCCESS', 'text': text})
        self.store.consume()
        return run

    def test_artifact_records_full_provenance(self):
        self.store.add_message('Do the thing', role='user', conversation='main')
        job = self.store.create(contract(), conversation='main')
        run = self.produce(job, 'The drafted report body.')
        rows = self.store.lineage(job)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['project_id'], 'default')
        self.assertEqual(row['conversation_id'], 'main')
        self.assertEqual(row['job_id'], job)
        self.assertEqual(row['milestone_id'], 'a')
        self.assertEqual(row['run_id'], run['id'])
        self.assertEqual(row['filename'], 'result.md')
        self.assertTrue(row['relpath'].replace('\\', '/').startswith('artifacts/'))
        self.assertIsNone(row['supersedes'])
        self.assertIsNone(row['superseded_by'])
        self.assertTrue(row['turn_ref'].startswith('message:'))
        with contextlib.closing(self.store.connect()) as db:
            # create() records the request as the conversation's user turn; that newest message is
            # the originating turn the lineage points at.
            seq = db.execute('SELECT MAX(seq) AS seq FROM messages').fetchone()['seq']
        self.assertEqual(row['turn_ref'], 'message:%s' % seq)
        # The current artifact in job data points at the lineage row.
        current = self.store.get(job)['milestones']['a']['artifact']
        self.assertEqual(current['lineage'], row['id'])
        self.assertEqual(current['sha256'], row['sha256'])
        # Any version's text is readable, integrity-checked.
        got = self.store.lineage_artifact(row['id'])
        self.assertEqual(got['text'], 'The drafted report body.')

    def test_tampered_version_is_refused(self):
        job = self.store.create(contract(), conversation='main')
        self.produce(job, 'Original text that is long enough.')
        row = self.store.lineage(job)[0]
        target = Path(self.tmp.name) / row['relpath']
        target.write_text('tampered', encoding='utf-8')
        with self.assertRaises(PolicyError):
            self.store.lineage_artifact(row['id'])

    def test_new_run_chains_previous_version(self):
        job = self.store.create(contract(), conversation='main')
        first_run = self.produce(job, 'v1', event='first')  # too short: the check fails
        self.assertEqual(self.store.verify(job, 'a'), 'FAILED')
        self.assertEqual(self.store.get(job)['milestones']['a']['state'], 'NEEDS_REPAIR')
        second_run = self.produce(job, 'v2 is long enough to pass.', event='second')
        rows = self.store.lineage(job, 'a')
        self.assertEqual(len(rows), 2)
        newest, oldest = rows[0], rows[1]
        self.assertEqual(newest['run_id'], second_run['id'])
        self.assertEqual(oldest['run_id'], first_run['id'])
        self.assertEqual(newest['supersedes'], oldest['id'])
        self.assertEqual(oldest['superseded_by'], newest['id'])
        # The previous version is not just recorded - its text is still readable.
        self.assertEqual(self.store.lineage_artifact(oldest['id'])['text'], 'v1')
        self.assertEqual(self.store.lineage_artifact(newest['id'])['text'],
                         'v2 is long enough to pass.')

    def test_renamed_artifact_keeps_the_chain(self):
        job = self.store.create(contract(filename='draft.md'), conversation='main')
        self.produce(job, 'v1', event='first')
        self.assertEqual(self.store.verify(job, 'a'), 'FAILED')
        revised = contract(filename='final-report.md')
        self.store.revise(job, revised, self.store.get(job)['revision'])
        run = self.store.claim(job, 'a')
        self.store.enqueue_result('second', run['id'], run['epoch'],
                                  {'outcome': 'SUCCESS', 'text': 'v2 final and long enough.'})
        self.store.consume()
        rows = self.store.lineage(job, 'a')
        self.assertEqual([r['filename'] for r in rows], ['final-report.md', 'draft.md'])
        self.assertEqual(rows[0]['supersedes'], rows[1]['id'])
        self.assertEqual(self.store.lineage_artifact(rows[1]['id'])['text'], 'v1')

    def test_lineage_is_job_scoped_and_project_resolved(self):
        Context(self.store).project('Side Project', project_id='side')
        with contextlib.closing(self.store.connect()) as db:
            db.execute("INSERT INTO conversations(id, project_id, title) VALUES('lab','side','Lab')")
        job_a = self.store.create(contract(), conversation='main')
        job_b = self.store.create(contract(), conversation='lab')
        self.produce(job_a, 'Main project text long enough.', event='event-a')
        self.produce(job_b, 'Side project text long enough.', event='event-b')
        main_rows = self.store.lineage(job_a)
        side_rows = self.store.lineage(job_b)
        self.assertEqual([r['project_id'] for r in main_rows], ['default'])
        self.assertEqual([r['project_id'] for r in side_rows], ['side'])
        self.assertEqual(self.store.lineage('missing-job'), [])

    def test_artifact_json_shape_survives_job_round_trip(self):
        job = self.store.create(contract(), conversation='main')
        self.produce(job, 'Round trip text long enough.')
        stored = self.store.get(job)
        artifact = stored['milestones']['a']['artifact']
        self.assertIn('lineage', artifact)
        self.assertEqual(self.store.verify(job, 'a'), 'VERIFIED')


if __name__ == '__main__':
    unittest.main()
