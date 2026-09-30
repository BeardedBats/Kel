import os
import json
import tempfile
import unittest
import uuid
import time
from pathlib import Path
from unittest.mock import patch

from kel.core import PolicyError
from kel.service import Service
from kel.work_hub import WorkHub


class WorkHubApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'KEL_TURN_MODEL':'none', 'KEL_GENERAL_ROOT':'none',
                              'KEL_CLI_WEB':'0', 'KEL_MEMORY_MIRROR':'0', 'KEL_TASTE':'0',
                              'KEL_REVIEWER':'none', 'KEL_SKIP_TELEMETRY':'1'})
        self.env.start()
        self.service = Service(Path(self.temporary.name) / 'engine')
        self.hub = WorkHub(self.service)

    def tearDown(self):
        self.service.shutdown()
        self.env.stop()
        self.temporary.cleanup()

    def test_preview_confirm_find_and_reopen_share_engine_identity(self):
        preview = self.service.action('/api/work-hub/imports', {'action':'preview',
            'project_id':'default', 'content':'Existing planning record for the work hub.', 'title':'Work hub record'})
        self.assertEqual(self.hub.get('/api/work-hub/imports', {'project_id':'default'})['entries'], [])
        receipt = self.service.action('/api/work-hub/imports', {'action':'confirm',
            'project_id':'default', 'preview_id':preview['preview_id'], 'digest':preview['digest'], 'confirm':True})
        state = self.service.state(receipt['conversation_id'])
        self.assertEqual(state['jobs'], [])
        self.assertEqual(len(state['messages']), 1)
        self.assertIn('external-untrusted', state['messages'][0]['text'])
        search = self.hub.get('/api/work-hub/search', {'project_id':'default', 'query':'planning'})
        self.assertTrue(any(entry['id'] == receipt['conversation_id'] for entry in search['conversations']))
        same = self.service.action('/api/work-hub/imports', {'action':'confirm',
            'project_id':'default', 'preview_id':preview['preview_id'], 'digest':preview['digest'], 'confirm':True})
        self.assertTrue(same['duplicate'])
        self.assertEqual(same['conversation_id'], receipt['conversation_id'])

    def test_project_and_confirmation_boundaries(self):
        for project in ('*', 'missing'):
            with self.assertRaises(PolicyError):
                self.service.action('/api/work-hub/imports', {'action':'preview', 'project_id':project, 'content':'Existing work'})
        preview = self.service.action('/api/work-hub/imports', {'action':'preview', 'project_id':'default', 'content':'Existing work'})
        with self.assertRaises(PolicyError):
            self.service.action('/api/work-hub/imports', {'action':'confirm', 'project_id':'default',
                'preview_id':preview['preview_id'], 'digest':preview['digest'], 'confirm':'yes'})
        with self.assertRaises(PolicyError):
            self.hub.get('/api/work-hub/execute', {'project_id':'default'})

    def test_existing_semver_recipe_metadata_is_inspectable(self):
        result = self.hub.get('/api/work-hub/procedures',
                              {'project_id':'default', 'recipe_id':'fix-bug', 'version':'1.0.0'})
        self.assertEqual(result['version'], '1.0.0')
        self.assertEqual(result['state'], 'draft')
        self.assertEqual(self.hub.get('/api/work-hub/outcomes', {'project_id':'default'})['selection_changed'], False)

    def test_transcript_origin_crosses_transport_once_without_inventing_source_identity(self):
        from kel.input_origins import InputOrigins
        from kel.transcription import Transcription
        Transcription(self.service.store)
        with self.service.store.transaction() as db:
            db.execute('INSERT INTO transcripts(id,name,text,created,updated) VALUES(?,?,?,?,?)',
                       ('saved', 'Recorded input', 'Original source words', time.time(), time.time()))
        donor = str(uuid.uuid4())
        self.service.action('/api/work-hub/origin', {'project_id':'default', 'donor_id':donor,
            'transcript_id':'saved', 'text':'Reviewed edited input'})
        origins = InputOrigins(self.service.store)
        self.assertIsNone(origins.claim(donor, 'other', 'Reviewed edited input'))
        self.assertIsNone(origins.claim(donor, 'default', 'Different input'))
        with patch.object(self.service.requests, 'submit'):
            sid = self.service.submit({'conversation':'main', 'text':'Reviewed edited input', 'donor_id':donor})
        with self.service.store.transaction() as db:
            stored = json.loads(db.execute('SELECT packet FROM submission_packets WHERE id=?', (sid,)).fetchone()['packet'])
        self.assertEqual(stored['transcript_origin']['id'], 'saved')
        self.assertEqual(stored['transcript_origin']['name'], 'Recorded input')
        self.assertTrue(stored['transcript_origin']['edited'])
        self.assertIsNone(origins.claim(donor, 'default', 'Reviewed edited input'))
