"""Isolated Kibble intake, durable progress and self-update application boundary."""
import contextlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
import subprocess
from unittest.mock import Mock, patch

from kel.auto_apply import why_wait
from kel.context import Context
from kel.core import PolicyError, Store
from kel.dogfood import Dogfood
from kel.kibble_work import apply_work, progress, send, stage_images
from kel.projects import Projects
from kel.service import Service


class KibbleWorkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'engine')
        self.service = Service.__new__(Service)
        self.service.store = self.store
        self.service.context = Context(self.store)
        self.service.projects = Projects(self.store)
        self.service.handoff_lock = threading.RLock()
        self.service.lifecycle_lock = threading.RLock()
        self.service.draining = False
        self.service.wake = threading.Event()
        self.service.requests = Mock()
        self.service.commander = None
        self.dogfood = Dogfood(self.store)
        self.source = Path(self.tmp.name) / 'source'
        self.source.mkdir()
        with self.store.transaction() as db:
            db.execute('CREATE TABLE submissions(id TEXT PRIMARY KEY,conversation_id TEXT,text TEXT,state TEXT,error TEXT,job_id TEXT,created REAL)')
            db.execute('CREATE TABLE submission_packets(id TEXT PRIMARY KEY,packet TEXT,kind TEXT)')
            db.execute('CREATE TABLE message_files(submission_id TEXT,attachment_id TEXT,PRIMARY KEY(submission_id,attachment_id))')
            db.execute('CREATE TABLE submission_acks(submission_id TEXT PRIMARY KEY,message_seq INTEGER,title TEXT)')
        self.addCleanup(patch.stopall)
        patch('kel.kibble_work.source_root', return_value=self.source).start()

    def test_send_uses_real_durable_intake_and_keeps_finding_open(self):
        fix = self.dogfood.save('The tab stays selected after I leave it.')
        result = send(self.service, self.dogfood, fix['id'])
        self.assertEqual(result['status'], 'OPEN')
        self.assertEqual(result['work']['state'], 'PLANNING')
        self.assertFalse(result['work']['installed'])
        with contextlib.closing(self.store.connect()) as db:
            packet = json.loads(db.execute('SELECT packet FROM submission_packets').fetchone()[0])
            kind = db.execute('SELECT kind FROM submission_packets').fetchone()[0]
        self.assertEqual(kind, 'coding')
        with contextlib.closing(self.store.connect()) as db:
            association = db.execute('SELECT fix_id FROM kibble_work WHERE submission_id=?',
                                     (result['work']['submission_id'],)).fetchone()
        self.assertEqual(association['fix_id'], fix['id'])
        self.assertEqual(Path(packet['project']['root']), self.source)
        self.service.requests.submit.assert_called_once()

    def test_repeat_send_and_reopened_store_keep_same_submission(self):
        fix = self.dogfood.save('The button does nothing.')
        first = send(self.service, self.dogfood, fix['id'])
        second = send(self.service, self.dogfood, fix['id'])
        reopened = Dogfood(Store(self.store.root)).get(fix['id'])
        self.assertEqual(first['work']['submission_id'], second['work']['submission_id'])
        self.assertEqual(first['work']['submission_id'], reopened['work']['submission_id'])
        self.service.requests.submit.assert_called_once()

    def test_interrupted_intake_shows_real_error_without_resolving_finding(self):
        fix = self.dogfood.save('The pane does not open.')
        result = send(self.service, self.dogfood, fix['id'])
        with self.store.transaction() as db:
            db.execute("UPDATE submissions SET state='INTERRUPTED',error='The app closed.' WHERE id=?",
                       (result['work']['submission_id'],))
        reopened = self.dogfood.get(fix['id'])
        self.assertEqual(reopened['work']['state'], 'INTERRUPTED')
        self.assertEqual(reopened['work']['error'], 'The app closed.')
        self.assertEqual(reopened['status'], 'OPEN')
        retried = self.service._dogfood_dispatch({'action': 'retry_work', 'id': fix['id']})
        self.assertEqual(retried['work']['submission_id'], result['work']['submission_id'])
        self.assertEqual(retried['work']['state'], 'PLANNING')
        self.assertEqual(self.service.requests.submit.call_count, 2)
        with self.assertRaises(PolicyError):
            self.service._dogfood_dispatch({'action': 'retry_work', 'id': fix['id']})

    def test_failed_intake_leaves_capture_ready_to_send_again(self):
        fix = self.dogfood.save('The pane does not open.')
        with patch.object(self.service, 'submit', side_effect=PolicyError('The worker is unavailable.')):
            with self.assertRaises(PolicyError):
                send(self.service, self.dogfood, fix['id'])
        self.assertIsNone(progress(self.store, fix['id']))
        self.assertEqual(self.dogfood.get(fix['id'])['status'], 'OPEN')

    def test_dismissed_or_wordless_findings_do_not_dispatch(self):
        fix = self.dogfood.save('This is no longer needed.')
        self.dogfood.set_status(fix['id'], 'DISMISSED')
        with self.assertRaises(PolicyError):
            send(self.service, self.dogfood, fix['id'])
        wordless = self.dogfood.save('', element={'tag': 'button'})
        with self.assertRaises(PolicyError):
            send(self.service, self.dogfood, wordless['id'])
        self.service.requests.submit.assert_not_called()

    def test_wordless_capture_accepts_note_then_freezes_sent_evidence(self):
        fix = self.dogfood.save('', element={'tag': 'button'}, route='/dogfood')
        with self.assertRaises(PolicyError):
            self.dogfood.set_note(fix['id'], '')
        with self.assertRaises(PolicyError):
            self.dogfood.set_note(fix['id'], 'x' * 8001)
        updated = self.service._dogfood_dispatch({'action': 'set_note', 'id': fix['id'],
                                                  'transcript': 'The button does nothing.'})
        self.assertEqual(updated['transcript'], 'The button does nothing.')
        self.assertEqual(updated['element'], fix['element'])
        self.assertEqual(updated['route'], fix['route'])
        self.assertEqual(updated['created'], fix['created'])
        self.assertEqual(updated['diagnostics']['voice'], 'typed')
        send(self.service, self.dogfood, fix['id'])
        with self.assertRaises(PolicyError):
            self.dogfood.set_note(fix['id'], 'Change the evidence.')

    def test_kel_update_never_auto_applies_even_with_full_access(self):
        job = {'contract': {'context': {'kibble': {'fix_id': 'FIX-0001'}}}}
        with patch('kel.authority.is_full', return_value=True):
            self.assertIn('your review', why_wait(self.store, job))

    def test_worker_snapshot_preserves_original_source_and_progress_follows_job(self):
        from kel.coding import compile_coding, snapshot
        for args in (['init'], ['-c', 'user.name=Kel', '-c', 'user.email=kel@localhost',
                                'commit', '--allow-empty', '-m', 'fixture']):
            subprocess.run(['git', '-C', str(self.source), *args], check=True, capture_output=True)
        original = self.source / 'example.py'
        original.write_text('answer = 1\n', encoding='utf-8')
        fix = self.dogfood.save('The number is wrong.')
        result = send(self.service, self.dogfood, fix['id'])
        sid = result['work']['submission_id']
        with contextlib.closing(self.store.connect()) as db:
            packet = json.loads(db.execute('SELECT packet FROM submission_packets WHERE id=?', (sid,)).fetchone()[0])
        contract = self.service._compile_work(sid, result['work']['conversation'],
                                              'Fix the number.', packet, 'coding', False)
        self.assertEqual(contract['context']['kibble']['fix_id'], fix['id'])
        jid = self.store.create(contract, conversation=result['work']['conversation'])
        with self.store.transaction() as db:
            db.execute("UPDATE submissions SET state='DISPATCHED',job_id=? WHERE id=?", (jid, sid))
        work = progress(self.store, fix['id'])
        self.assertEqual(work['job_id'], jid)
        self.assertEqual(work['state'], 'READY')
        self.assertIn('job.created', [event['type'] for event in work['events']])
        copy = self.store.root / 'repositories' / jid
        copy.parent.mkdir()
        snapshot(self.source, copy)
        (copy / 'example.py').write_text('answer = 2\n', encoding='utf-8')
        self.assertEqual(original.read_text(encoding='utf-8'), 'answer = 1\n')
        with patch('kel.apply_changes.apply_checked') as apply:
            with self.assertRaises(PolicyError):
                apply_work(self.service, self.dogfood, fix['id'])
            apply.assert_not_called()
        self.assertEqual(self.dogfood.get(fix['id'])['status'], 'OPEN')

    def test_recorded_screenshot_is_staged_for_native_worker_without_original_access(self):
        from kel.core import digest
        cid = self.service.context.conversation()
        raw = b'\x89PNG\r\n\x1a\nfixture'
        aid = self.service.context.attach(cid, 'FIX-0001.png', raw, 'image/png')
        packet = self.service.context.handoff(cid, 'Fix the recorded target.', [aid])
        packet['kibble'] = {'fix_id': 'FIX-0001'}
        original = self.store.root / packet['files'][0]['image_path']
        paths = stage_images(self.store, {'context': packet}, 'fixture-run')
        self.assertEqual(len(paths), 1)
        self.assertTrue(Path(paths[0]).is_relative_to(self.store.root / 'sessions/fixture-run'))
        self.assertEqual(Path(paths[0]).read_bytes(), raw)
        self.assertEqual(original.read_bytes(), raw)
        with patch.object(Path, 'is_junction', return_value=True):
            with self.assertRaises(PolicyError):
                stage_images(self.store, {'context': packet}, 'fixture-run')
        original.write_bytes(b'changed')
        with self.assertRaises(PolicyError):
            stage_images(self.store, {'context': packet}, 'fixture-run')
        packet['files'][0].update(image_path='../outside.png', sha256=digest(raw))
        with self.assertRaises(PolicyError):
            stage_images(self.store, {'context': packet}, 'fixture-run')


if __name__ == '__main__':
    unittest.main()
