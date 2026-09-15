import contextlib
import json
from pathlib import Path
import tempfile
import unittest
from kel.core import Store,PolicyError
from kel.context import Context
from kel.engine import compile_document
from kel.runner import process_identity
from kel.coding import CodingAdapter,check_evidence,file_manifest


class V1Tests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.store=Store(self.tmp.name);self.context=Context(self.store)
    def tearDown(self):self.tmp.cleanup()
    def test_context_survives_reopen(self):
        p=self.context.project('Project',notes='Use Cedar, not Maple.');c=self.context.conversation(p)
        self.store.add_message('The deadline is Friday.',conversation=c)
        a=self.context.attach(c,'notes.md',b'## Facts\nThe number is 47.')
        packet=Context(Store(self.tmp.name)).handoff(c,'Write the plan',[a])
        self.assertEqual(packet['project']['decisions'],'Use Cedar, not Maple.')
        self.assertIn('47',packet['files'][0]['text']);self.assertIn('Friday',packet['history'][0]['text'])
    def test_foreign_attachment_is_rejected(self):
        c=self.context.conversation();a=self.context.attach('main','a.txt',b'private')
        with self.assertRaises(PolicyError):self.context.handoff(c,'read',[a])
    def test_changed_attachment_is_rejected(self):
        a=self.context.attach('main','a.txt',b'original');(self.store.root/'attachments'/a).write_bytes(b'changed')
        with self.assertRaises(PolicyError):self.context.handoff('main','read',[a])
    def test_context_overflow_never_truncates_request(self):
        with self.assertRaises(PolicyError):self.context.handoff('main','x'*33000)
    def test_exact_permission_reuse_and_revoke(self):
        action={'command':['python','test.py'],'root':'A'}
        self.context.grant('default',action);self.assertTrue(self.context.allowed('default',action))
        self.assertFalse(self.context.allowed('default',dict(action,root='B')))
        self.context.revoke('default');self.assertFalse(self.context.allowed('default',action))
    def test_folder_change_revokes_grants(self):
        action={'edit':True};self.context.grant('default',action)
        self.context.project('General',self.tmp.name,project_id='default')
        self.assertFalse(self.context.allowed('default',action))
    def test_duplicate_intake_creates_one_job(self):
        contract=dict(compile_document('Write a note',['note']),submission_id='request-47')
        a=self.store.create(contract);b=self.store.create(contract)
        self.assertEqual(a,b);self.assertEqual(len(self.store.list_jobs()),1)
    def test_live_process_identity_is_stable(self):
        import os
        self.assertIsNotNone(process_identity(os.getpid()));self.assertEqual(process_identity(os.getpid()),process_identity(os.getpid()))
        self.assertIsNone(process_identity(999999999))
    def test_code_claim_without_trusted_evidence_is_uncertain(self):
        CodingAdapter(self.store);self.assertEqual(check_evidence(self.store,'fake'),'UNCERTAIN')
    def test_binary_context_fails_explicitly(self):
        a=self.context.attach('main','image.bin',b'\xff\xfe\x00')
        with self.assertRaises(PolicyError):self.context.handoff('main','inspect',[a])


if __name__=='__main__':unittest.main()
