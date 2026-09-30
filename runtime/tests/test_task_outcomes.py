import json
import tempfile
import unittest
from pathlib import Path

from kel.context import Context
from kel.core import PolicyError, Store
from kel.task_outcomes import TaskOutcomes
from kel.usage import ensure


class TaskOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temporary.name))
        self.context = Context(self.store)
        self.outcomes = TaskOutcomes(self.store)
        self.job_id = self.store.create({'request': 'Review existing work', 'project_id': 'default',
            'milestones': [{'id': 'm1', 'objective': 'Result', 'filename': 'result.md',
                            'checks': [{'kind': 'min_chars', 'value': 1}]}]})

    def tearDown(self):
        self.temporary.cleanup()

    def close(self, verdict='VERIFIED'):
        if verdict == 'VERIFIED':
            run = self.store.claim(self.job_id, 'm1')
            self.store.enqueue_result('result-' + run['id'], run['id'], run['epoch'],
                                      {'outcome': 'SUCCESS', 'text': 'Checked result'})
            self.store.consume()
            self.store.verify(self.job_id, 'm1')
            self.store.assess(self.job_id)
            return
        with self.store.transaction() as db:
            job = self.store._get(db, self.job_id)
            job.update(state='CLOSED', verdict=verdict)
            self.store._save(db, job, 'job.assessed')

    def test_unknown_feedback_and_cost_never_imply_acceptance_or_free(self):
        self.close()
        result = self.outcomes.view(self.job_id, 'default')
        self.assertFalse(result['accepted_by_user'])
        self.assertIsNone(result['feedback'])
        self.assertIsNone(result['costs']['reported'])
        self.assertFalse(result['costs']['complete'])
        self.assertFalse(result['selection_changed'])

    def test_feedback_is_explicit_scoped_and_idempotent(self):
        with self.assertRaises(PolicyError):
            self.outcomes.feedback(self.job_id, 'default', 'useful')
        self.close()
        with self.assertRaises(PolicyError):
            self.outcomes.feedback(self.job_id, 'other', 'useful')
        self.outcomes.feedback(self.job_id, 'default', 'revision_requested')
        same = self.outcomes.feedback(self.job_id, 'default', 'revision_requested')
        self.assertEqual(same['feedback']['revision_requests'], 1)
        self.assertFalse(same['accepted_by_user'])
        accepted = self.outcomes.feedback(self.job_id, 'default', 'useful')
        self.assertTrue(accepted['accepted_by_user'])
        self.assertEqual(accepted['feedback']['revision_requests'], 1)
        self.assertEqual(self.outcomes.summary('other')['tasks'], [])

    def test_failed_checks_do_not_become_accepted(self):
        self.close('FAILED')
        with self.assertRaises(PolicyError):
            self.outcomes.feedback(self.job_id, 'default', 'useful')
        self.assertEqual(self.store.get(self.job_id)['verdict'], 'FAILED')

    def test_changed_work_does_not_inherit_useful_feedback(self):
        self.close()
        self.outcomes.feedback(self.job_id, 'default', 'useful')
        with self.store.transaction() as db:
            job = self.store._get(db, self.job_id)
            job['contract']['request'] = 'Revised work'
            job['contract_version'] += 1
            self.store._save(db, job, 'contract.revised')
        view = self.outcomes.view(self.job_id, 'default')
        self.assertFalse(view['accepted_by_user'])
        self.assertFalse(view['feedback_current'])
        artifact = self.store.get(self.job_id)['milestones']['m1']['artifact']
        (self.store.root / artifact['path']).write_text('Changed bytes', encoding='utf-8')
        self.assertFalse(self.outcomes.view(self.job_id, 'default')['accepted_by_user'])
        with self.assertRaises(PolicyError):
            self.outcomes.feedback(self.job_id, 'default', 'useful')

    def test_usage_includes_planning_without_double_counting_or_mixing_currencies(self):
        self.close()
        with self.store.transaction() as db:
            db.execute('CREATE TABLE submissions(id TEXT, job_id TEXT)')
            db.execute('INSERT INTO submissions VALUES(?,?)', ('s1', self.job_id))
            ensure(db)
            db.execute('DELETE FROM provider_usage')
            for call in [
                {'call_id':'plan', 'submission_id':'s1', 'cost_usd':0.3, 'cost_basis':'estimated', 'subscription':True, 'wall_ms':4},
                {'call_id':'work', 'job_id':self.job_id, 'submission_id':'s1', 'cost_usd':0.1, 'cost_basis':'reported', 'wall_ms':8},
                {'call_id':'check', 'job_id':self.job_id, 'cost_usd':None, 'cost_basis':'unknown'},
            ]:
                db.execute('INSERT INTO provider_usage(provider,at,data) VALUES(?,?,?)',
                           ('fixture', 1, json.dumps({'event':'run', **call})))
        view = self.outcomes.view(self.job_id, 'default')
        self.assertEqual(view['call_count'], 3)
        self.assertEqual(view['model_call_ms'], 12)
        self.assertEqual(view['duration_unknown_calls'], 1)
        self.assertEqual(view['costs']['reported'], 0.1)
        self.assertEqual(view['costs']['subscription_equivalent'], 0.3)
        self.assertEqual(view['costs']['unknown_calls'], 1)
        self.assertFalse(view['costs']['complete'])
