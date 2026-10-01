"""Execution receipts and legacy correction, without contacting a provider."""
import base64
import contextlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from kel.core import Store, PolicyError, encode
from kel.image_jobs import ImageAdapter, action, compile_image, image_artifact, repair_legacy_claims
from tests.test_requested_image_output import png


class ImageJobTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='kel-image-execution-')
        self.addCleanup(self.temporary.cleanup)
        self.store = Store(Path(self.temporary.name))
        self.adapter = ImageAdapter(self.store)

    def claimed(self):
        job = self.store.create(compile_image('Create an infographic about Kel.'))
        return self.store.claim(job, 'image', provider='image-generation')

    def test_native_tool_event_is_required_not_agent_image_prose(self):
        class ProseConnection:
            def __init__(self, *args, **kwargs): pass
            def run(self, prompt, **kwargs):
                kwargs['on_event']({'method':'item/completed','params':{'item':{
                    'type':'agentMessage','text':'Done. Here is the image.','result':base64.b64encode(png()).decode()}}})
                return {'outcome':'SUCCESS'}
            def close(self): pass
        self.adapter.connection_factory = ProseConnection
        result = self.adapter._native('Create an infographic.', self.claimed()['id'], threading.Event())
        self.assertEqual(result['outcome'], 'FAILED')
        with contextlib.closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_receipts').fetchone()[0], 0)

    def test_desktop_receipt_cannot_land_after_cancellation(self):
        run = self.claimed()
        with self.store.transaction() as db:
            db.execute("INSERT INTO image_tasks VALUES(?,?,?,'QUEUED',NULL,NULL,NULL,NULL,0)",
                       (run['id'], run['epoch'], 'Create image.'))
        task = action(self.store, {'action':'poll','ready':True,'provider':'configured','model':'image-model'})['task']
        self.store.control(run['job_id'], 'cancel')
        with self.assertRaises(PolicyError):
            action(self.store, {'action':'result',**task,'base64':base64.b64encode(png()).decode()})
        with contextlib.closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_receipts').fetchone()[0], 0)

    def test_legacy_false_done_correction_preserves_text_files_and_does_not_replay(self):
        contract = {'request':'Make me an infographic showing how Kel works to my staff', 'project_id':'staff',
            'milestones':[{'id':'document','objective':'Make infographic','filename':'result.md',
                           'checks':[{'kind':'min_chars','value':1}]}]}
        job_id = self.store.create(contract)
        with self.store.transaction() as db:
            job = self.store._get(db, job_id)
            artifact = self.store._artifact(job_id, 'document', 'old-run', 'This was text, not an image.')
            job['milestones']['document'].update(state='ACCEPTED',artifact=artifact,checks=[],provider='codex')
            job.update(state='CLOSED',verdict='VERIFIED')
            self.store._save(db, job, 'fixture.false_image_done')
            db.execute('INSERT INTO messages(conversation_id,role,text,job_id,at,meta) VALUES(?,?,?,?,?,?)',
                ('main','assistant','Done. It passed its checks.',job_id,1,encode({'kind':'result','verdict':'VERIFIED','job':job_id})))
        old_bytes = (self.store.root / artifact['path']).read_bytes()
        self.assertEqual(repair_legacy_claims(self.store), [job_id])
        self.assertEqual(repair_legacy_claims(self.store), [])
        job = self.store.get(job_id)
        self.assertEqual(job['state'], 'WAITING_RESOURCE')
        self.assertEqual(job['contract']['kind'], 'image')
        self.assertEqual(job['contract']['project_id'], 'staff')
        self.assertEqual(job['milestones']['image']['attempts'], 0)
        self.assertEqual((self.store.root / artifact['path']).read_bytes(), old_bytes)
        with contextlib.closing(self.store.connect()) as db:
            rows = db.execute("SELECT text,meta FROM messages WHERE job_id=? AND role='assistant' ORDER BY seq", (job_id,)).fetchall()
            self.assertEqual(rows[0]['text'], 'Done. It passed its checks.')
            self.assertEqual(json.loads(rows[0]['meta'])['verdict'], 'FAILED')
            self.assertEqual(len(rows), 2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM runs').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM contracts WHERE job_id=?',(job_id,)).fetchone()[0], 2)

    def test_nonimage_legacy_work_is_unchanged(self):
        job_id = self.store.create({'request':'Write a prompt to generate an infographic.',
            'milestones':[{'id':'document','objective':'Write prompt','filename':'result.md',
                           'checks':[{'kind':'min_chars','value':1}]}]})
        with self.store.transaction() as db:
            job = self.store._get(db,job_id)
            job.update(state='CLOSED',verdict='VERIFIED')
            self.store._save(db,job,'fixture.prompt_done')
        before = self.store.get(job_id)
        self.assertEqual(repair_legacy_claims(self.store), [])
        self.assertEqual(self.store.get(job_id), before)
