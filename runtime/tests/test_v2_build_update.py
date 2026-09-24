"""Kibble Build Update — the acceptance suite for the D-46 backend contract.

The pins the handoff asks for, in order: **isolation** (the mission works through the existing
coding machinery and nothing writes into the source checkout; the candidate lives under the engine's
own `candidates/<id>/`), **denied actions** (`promote` refuses in plain words for every state; a
review only a person can give), **failed tests** (an unverified mission still yields a reviewable
candidate — never an approved one), **unresolved findings** (they are listed, and Fix Capture's own
statuses are never rewritten), **candidate creation** (assembled once the mission settles, its report
on disk), and the structural proof that **candidate creation cannot trigger promotion**.
"""
import contextlib
import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from kel.build_update import BuildUpdate
from kel.core import PolicyError, Store
from kel.dogfood import Dogfood
from kel.memory import ensure_schema as ensure_memory_schema
from kel.workforce import ensure_schema as ensure_workforce_schema

TESTS = ['python', '-m', 'unittest']


def make_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'init', '-q', str(path)], check=True, capture_output=True)
    (path / 'app.py').write_text('VALUE = 1\n', encoding='utf-8')
    subprocess.run(['git', '-C', str(path), 'add', '-A'], check=True, capture_output=True)
    subprocess.run(['git', '-C', str(path), '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost',
                    'commit', '-q', '-m', 'baseline'], check=True, capture_output=True)
    return path


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.store = Store(Path(self.tmp.name) / 'data')
        ensure_workforce_schema(self.store)
        ensure_memory_schema(self.store)
        self.dogfood = Dogfood(self.store)
        self.repo = make_repo(Path(self.tmp.name) / 'source')
        self.builder = BuildUpdate(self.store)
        self.fix_a = self.dogfood.save('The save button is cut off on small windows.',
                                       route='/settings', version='2.1.0')['id']
        self.fix_b = self.dogfood.save('The transcript box loses focus after dictation.',
                                       route='/home', version='2.1.0')['id']

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def start(self, findings=None):
        result = self.builder.start(findings or [self.fix_a, self.fix_b],
                                    source_root=self.repo, tests=TESTS)
        return result['mission']['id'], result['job']

    def settle(self, job_id, *, verdict='VERIFIED', artifact=None):
        with self.store.transaction() as db:
            job = self.store._get(db, job_id)
            if artifact is not None:
                job['milestones']['code']['artifact'] = artifact
            job.update(state='CLOSED', verdict=verdict)
            self.store._save(db, job, 'test.settle')

    def seed_evidence(self, run_id, tests='2 tests failed:\nFAILED test_save_button', workspace=None):
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS code_evidence(run_id TEXT PRIMARY KEY,'
                       'workspace TEXT,manifest TEXT,patch TEXT,patch_digest TEXT,tests TEXT,'
                       'baseline_tests TEXT,at REAL)')
            db.execute("INSERT OR REPLACE INTO code_evidence VALUES(?,?,?,?,?,?,?,?)",
                       (run_id, str(workspace or self.repo), '{}', None, 'digest-x', tests,
                        'all green', time.time()))


class MissionTests(Base):
    def test_start_creates_a_mission_on_the_existing_work_machinery(self):
        mission_id, job_id = self.start()
        mission = self.builder.status(mission_id)['mission']
        self.assertEqual(mission['source_root'], str(self.repo))
        self.assertTrue(mission['baseline_revision'])
        self.assertEqual([item['id'] for item in mission['findings']], [self.fix_a, self.fix_b])
        self.assertEqual(mission['findings'][0]['route'], '/settings')
        self.assertEqual(mission['findings'][0]['version'], '2.1.0')
        job = self.store.get(job_id)
        self.assertEqual(job['contract']['kind'], 'coding')
        self.assertEqual(job['contract']['root'], str(self.repo))
        self.assertEqual(job['contract']['test_command'], TESTS)
        self.assertIn(self.fix_a, job['contract']['request'])
        with contextlib.closing(self.store.connect()) as db:
            self.assertIsNone(db.execute('SELECT * FROM build_candidates').fetchone(),
                              'no candidate exists until the mission settles')

    def test_start_refuses_unknown_or_closed_findings(self):
        with self.assertRaises(PolicyError):
            self.start(['FIX-9999'])
        self.dogfood.set_status(self.fix_a, 'FIXED')
        with self.assertRaises(PolicyError) as raised:
            self.start([self.fix_a])
        self.assertIn('open findings', str(raised.exception))

    def test_start_refuses_a_sensitive_a_non_repo_or_a_dirty_source(self):
        with self.assertRaises(PolicyError) as raised:
            self.builder.start([self.fix_a], source_root=self.store.root, tests=TESTS)
        self.assertIn('will not use', str(raised.exception))
        plain = Path(self.tmp.name) / 'plain'
        plain.mkdir()
        with self.assertRaises(PolicyError) as raised:
            self.builder.start([self.fix_a], source_root=plain, tests=TESTS)
        # Kel's own sentence, not a raw git message (V2-18 measured the leak).
        self.assertIn('not a Git repository', str(raised.exception))
        (self.repo / 'app.py').write_text('VALUE = 2\n', encoding='utf-8')
        with self.assertRaises(PolicyError) as raised:
            self.builder.start([self.fix_a], source_root=self.repo, tests=TESTS)
        self.assertIn('uncommitted changes', str(raised.exception))


class CandidateTests(Base):
    def test_candidate_is_not_created_before_the_mission_settles(self):
        mission_id, _job = self.start()
        result = self.builder.candidate(mission_id)
        self.assertEqual(result['state'], 'BUILDING')
        self.assertIsNone(result['candidate'])

    def test_cancelled_mission_does_not_claim_a_build_or_create_a_candidate(self):
        mission_id, job_id = self.start()
        self.store.control(job_id, 'cancel')
        result = self.builder.candidate(mission_id)
        self.assertEqual(result, {'state': 'CANCELLED', 'candidate': None,
                                  'job_state': 'CANCELLED'})
        self.assertEqual(self.builder.status(mission_id)['job']['state'], 'CANCELLED')
        with contextlib.closing(self.store.connect()) as db:
            self.assertIsNone(db.execute('SELECT * FROM build_candidates').fetchone())
        self.assertFalse((self.store.root / 'candidates').exists())

    def test_candidate_assembles_after_settle_isolated_from_the_source(self):
        mission_id, job_id = self.start()
        self.settle(job_id)
        result = self.builder.candidate(mission_id)
        candidate = result['candidate']
        self.assertEqual(result['state'], 'READY_FOR_REVIEW')
        location = Path(candidate['artifact_location'])
        self.assertTrue(location.is_dir())
        self.assertTrue(str(location).startswith(str(self.store.root / 'candidates')))
        self.assertFalse(str(location).startswith(str(self.repo)),
                         'the candidate never lives in the source checkout')
        self.assertTrue((location / 'build-report.json').is_file())
        self.assertEqual(sorted(candidate['unresolved_findings']), sorted([self.fix_a, self.fix_b]))
        self.assertEqual(candidate['fixed_findings'], [],
                         'without verified evidence nothing is even claimed repaired')
        dirty = subprocess.run(['git', '-C', str(self.repo), 'status', '--porcelain'],
                               capture_output=True, text=True).stdout
        self.assertEqual(dirty.strip(), '', 'assembling a candidate never writes into the source')

    def test_failed_tests_yield_a_reviewable_candidate_never_an_approved_one(self):
        mission_id, job_id = self.start()
        self.seed_evidence('run-x')
        self.settle(job_id, artifact={'run_id': 'run-x', 'path': 'changes.md',
                                      'sha256': 'x', 'filename': 'changes.md'})
        candidate = self.builder.candidate(mission_id)['candidate']
        self.assertIn('FAILED', candidate['evidence']['tests'],
                      'test output is recorded verbatim')
        self.assertFalse(candidate['evidence']['verified'])
        self.assertEqual(candidate['review_state'], 'READY_FOR_REVIEW')
        self.assertTrue(any('did not reach verified evidence' in line
                            for line in candidate['limitations']))

    def test_the_evidence_note_describes_this_mission(self):
        mission_id, job_id = self.start()
        self.settle(job_id)
        candidate = self.builder.candidate(mission_id)['candidate']
        self.assertIn('no artifact', candidate['evidence']['note'])
        mission_id, job_id = self.start()
        self.seed_evidence('run-y')
        self.settle(job_id, artifact={'run_id': 'run-y', 'path': 'changes.md', 'sha256': 'y',
                                      'filename': 'changes.md'})
        candidate = self.builder.candidate(mission_id)['candidate']
        self.assertFalse(candidate['evidence']['verified'])
        self.assertNotIn('no artifact', candidate['evidence']['note'],
                         'a mission that did produce evidence never says otherwise')
        self.assertIn('did not verify', candidate['evidence']['note'])

    def _set_milestone(self, job_id, state):
        with self.store.transaction() as db:
            job = self.store._get(db, job_id)
            job['milestones']['code']['state'] = state
            self.store._save(db, job, 'test.milestone')

    def test_a_failed_mission_cannot_claim_a_verified_build(self):
        mission_id, job_id = self.start()
        self.seed_evidence('run-z')
        self._set_milestone(job_id, 'NEEDS_REPAIR')
        self.settle(job_id, verdict='FAILED',
                    artifact={'run_id': 'run-z', 'path': 'changes.md', 'sha256': 'z',
                              'filename': 'changes.md'})
        with patch('kel.coding.check_evidence', return_value='VERIFIED'):
            candidate = self.builder.candidate(mission_id)['candidate']
        self.assertFalse(candidate['evidence']['verified'],
                         "one run's evidence is not the mission's verdict")
        self.assertEqual(candidate['evidence']['mission_verdict'],
                         {'job': 'FAILED', 'milestone': 'NEEDS_REPAIR'})
        self.assertEqual(candidate['fixed_findings'], [])
        self.assertEqual(sorted(candidate['unresolved_findings']), sorted([self.fix_a, self.fix_b]))

    def test_a_passed_mission_claims_its_verified_build(self):
        mission_id, job_id = self.start()
        self.seed_evidence('run-z')
        self._set_milestone(job_id, 'ACCEPTED')
        self.settle(job_id, verdict='VERIFIED',
                    artifact={'run_id': 'run-z', 'path': 'changes.md', 'sha256': 'z',
                              'filename': 'changes.md'})
        with patch('kel.coding.check_evidence', return_value='VERIFIED'):
            candidate = self.builder.candidate(mission_id)['candidate']
        self.assertTrue(candidate['evidence']['verified'])
        self.assertNotIn('note', candidate['evidence'])
        self.assertEqual(sorted(candidate['fixed_findings']), sorted([self.fix_a, self.fix_b]))

    def test_readings_leave_fix_capture_as_built(self):
        mission_id, job_id = self.start()
        self.settle(job_id)
        self.builder.candidate(mission_id)
        self.assertEqual(self.dogfood.get(self.fix_a)['status'], 'OPEN',
                         'Build Update never rewrites Fix Capture statuses')


class ReviewTests(Base):
    def reviewed_candidate(self):
        mission_id, job_id = self.start()
        self.settle(job_id)
        return self.builder.candidate(mission_id)['candidate']

    def test_review_is_human_only(self):
        candidate = self.reviewed_candidate()
        with self.assertRaises(PolicyError) as raised:
            self.builder.review(candidate['id'], 'approve', actor='engine')
        self.assertIn('Only you', str(raised.exception))
        approved = self.builder.review(candidate['id'], 'approve', note='Looks right.')
        self.assertEqual(approved['review_state'], 'APPROVED')
        self.assertEqual(approved['reviewed_by'], 'user')
        with self.assertRaises(PolicyError):
            self.builder.review(candidate['id'], 'reject')

    def test_promote_refuses_in_every_state_and_changes_nothing(self):
        candidate = self.reviewed_candidate()
        self.builder.review(candidate['id'], 'approve', note='ok')
        before = subprocess.run(['git', '-C', str(self.repo), 'status', '--porcelain'],
                                capture_output=True, text=True).stdout
        for candidate_id in (candidate['id'], None):
            with self.assertRaises(PolicyError) as raised:
                self.builder.promote(candidate_id)
            self.assertIn('not part of Build Update', str(raised.exception))
        after = subprocess.run(['git', '-C', str(self.repo), 'status', '--porcelain'],
                               capture_output=True, text=True).stdout
        self.assertEqual(before, after, 'promotion attempts touch nothing')
        row = self.builder.status(candidate['mission_id'])['candidate']
        self.assertEqual(row['review_state'], 'APPROVED', 'the review state is unchanged by promote')

    def test_candidate_creation_cannot_trigger_promotion(self):
        candidate = self.reviewed_candidate()
        self.assertEqual(candidate['review_state'], 'READY_FOR_REVIEW')
        again = self.builder.candidate(candidate['mission_id'])
        self.assertEqual(again['candidate']['review_state'], 'READY_FOR_REVIEW',
                         're-assembling never approves')
        with self.assertRaises(PolicyError):
            self.builder.review(candidate['id'], 'approve', actor='kel')
        current = self.builder.status(candidate['mission_id'])['candidate']
        self.assertEqual(current['review_state'], 'READY_FOR_REVIEW')


if __name__ == '__main__':
    unittest.main()
