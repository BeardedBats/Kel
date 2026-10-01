import tempfile
import hashlib
import struct
import time
import unittest
import zlib
from pathlib import Path

from kel.core import PolicyError, Store
from kel.engine import Engine
from kel.output_contracts import ensure_image_schema, image_check, validate_png


def png():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 2, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress((b'\x00' + b'\xff\x80\x00\xff' * 2) * 2)) + chunk(b'IEND', b''))


class RequestedImageOutputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='kel-image-output-')
        self.store = Store(Path(self.temporary.name))

    def tearDown(self):
        self.temporary.cleanup()

    def candidate(self, request='Create an infographic about how Kel works.', **extra):
        contract = {'request': request, 'milestones': [{'id': 'result', 'objective': request,
                    'filename': 'result.md', 'checks': [{'kind': 'min_chars', 'value': 1}]}]}
        contract.update(extra)
        job_id = self.store.create(contract)
        run = self.store.claim(job_id, 'result')
        self.store.enqueue_result('result-' + run['id'], run['id'], run['epoch'],
            {'outcome': 'SUCCESS', 'text': 'Done. I generated and checked your infographic. Here is the image prompt.',
             'image_receipt': {'path': 'artifacts/claimed.png', 'tool': 'image_generation'}})
        self.store.consume()
        return job_id

    def test_prose_or_worker_receipt_cannot_satisfy_requested_image(self):
        job_id = self.candidate()
        job = self.store.get(job_id)
        self.assertEqual(job['milestones']['result']['state'], 'NEEDS_REPAIR')
        self.assertIsNone(job['milestones']['result']['artifact'])
        self.assertIn('No image file', job['milestones']['result']['error'])
        self.assertTrue(any(claim['id'] == 'requested.image' for claim in job['contract']['claims']))

    def test_explicit_image_output_cannot_be_downgraded_to_text_checks(self):
        job_id = self.candidate('Make this happen.', output_contract={'kind': 'image'})
        self.assertEqual(self.store.get(job_id)['milestones']['result']['state'], 'NEEDS_REPAIR')

    def test_reassessing_old_false_acceptance_blocks_done_publication(self):
        job_id = self.candidate()
        with self.store.transaction() as db:
            job = self.store._get(db, job_id)
            artifact = self.store._artifact(job_id, 'result', 'legacy-run', 'I generated and checked your infographic.')
            job['milestones']['result']['artifact'] = artifact
            job['milestones']['result'].update(state='ACCEPTED', checks=[])
            job.update(state='CLOSED', verdict='VERIFIED')
            self.store._save(db, job, 'fixture.old_false_acceptance')
        self.assertEqual(self.store.assess(job_id), 'FAILED')
        with self.assertRaises(PolicyError):
            self.store.publish(job_id)

    def test_prompt_only_request_keeps_its_text_output_contract(self):
        job_id = self.candidate('Write a prompt to generate an infographic about Kel.')
        self.assertEqual(self.store.verify(job_id, 'result'), 'VERIFIED')

    def image_contract(self):
        return {'request': 'Create an infographic about Kel.', 'kind': 'image',
                'output_contract': {'kind': 'image'}, 'milestones': [{'id': 'image',
                'objective': 'Create an infographic about Kel.', 'filename': 'image.png',
                'checks': [{'kind': 'generated_image'}]}]}

    def receipt(self, run_id, job_id, raw, path=None, write=True):
        relative = path or ('artifacts/' + run_id + '/image.png')
        if write:
            target = self.store.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        with self.store.transaction() as db:
            ensure_image_schema(db)
            db.execute('INSERT INTO image_receipts VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       (run_id, job_id, 'image', relative, hashlib.sha256(raw).hexdigest(), len(raw),
                        'image/png', 2, 2, 'fixture-image-tool', 'fixture', time.time()))

    def captured_image(self, raw=None, path=None, write=True):
        job_id = self.store.create(self.image_contract())
        run = self.store.claim(job_id, 'image', 'image-generation')
        self.receipt(run['id'], job_id, raw or png(), path, write)
        self.store.enqueue_result('capture-' + run['id'], run['id'], run['epoch'], {'outcome': 'SUCCESS'})
        self.store.consume()
        return job_id, run

    def test_valid_captured_fixture_delivers_image_and_names_visual_review_limit(self):
        job_id, _ = self.captured_image()
        self.assertEqual(self.store.verify(job_id, 'image'), 'VERIFIED')
        self.assertEqual(self.store.assess(job_id), 'VERIFIED')
        text, new = self.store.publish(job_id)
        self.assertTrue(new)
        self.assertIn('![Generated image](kel-image://' + job_id + '/image)', text)
        self.assertIn('visual details have not had a separate review', text)
        self.assertNotIn('It passed its checks.', text)
        self.assertEqual(self.store.lineage(job_id)[0]['media_type'], 'image/png')
        self.assertEqual(validate_png(png()), {'width': 2, 'height': 2})

    def test_missing_corrupt_and_outside_root_assets_cannot_be_captured(self):
        cases = [(None, None, False), (png()[:-2], None, True),
                 (None, '../outside.png', False), (b'not actually a PNG file' * 4, None, True)]
        for raw, path, write in cases:
            with self.subTest(path=path, write=write):
                job_id, _ = self.captured_image(raw, path, write)
                milestone = self.store.get(job_id)['milestones']['image']
                self.assertEqual(milestone['state'], 'NEEDS_REPAIR')
                self.assertIsNone(milestone['artifact'])

    def test_changed_asset_invalidates_a_prior_verified_image(self):
        job_id, _ = self.captured_image()
        self.store.verify(job_id, 'image')
        self.store.assess(job_id)
        artifact = self.store.get(job_id)['milestones']['image']['artifact']
        (self.store.root / artifact['path']).write_bytes(png() + b'trailing mutation')
        self.assertEqual(image_check(self.store, self.store.get(job_id), 'image')['verdict'], 'FAILED')
        self.assertNotEqual(self.store.assess(job_id), 'VERIFIED')
        with self.assertRaises(PolicyError):
            self.store.publish(job_id)

    def test_image_route_never_calls_a_text_adapter_when_generator_is_missing(self):
        class TextAdapter:
            calls = 0
            capabilities = {'text'}
            def execute(adapter, *args, **kwargs):
                adapter.calls += 1
                return {'outcome': 'SUCCESS', 'text': 'A text substitute'}
        adapter = TextAdapter()
        engine = Engine(self.store, {'fixture': adapter})
        try:
            job_id = engine.submit(self.image_contract())
            engine.tick()
            self.assertEqual(adapter.calls, 0)
            self.assertEqual(self.store.get(job_id)['state'], 'WAITING_RESOURCE')
            self.assertIn('No image generator', self.store.get(job_id)['route_block'])
        finally:
            engine.close()

    def test_failed_image_attempt_waits_instead_of_automatically_calling_tool_again(self):
        class ImageAdapter:
            calls = 0
            def ready(adapter): return True
            def execute(adapter, prompt, **kwargs):
                adapter.calls += 1
                return {'outcome': 'FAILED', 'error': 'Fixture image tool failed.'}
        adapter = ImageAdapter()
        engine = Engine(self.store, {'image-generation': adapter})
        try:
            job_id = engine.submit(self.image_contract())
            job = engine.wait(job_id, timeout=3)
            self.assertEqual(adapter.calls, 1)
            self.assertEqual(job['state'], 'WAITING_RESOURCE')
            for _ in range(3): engine.tick()
            self.assertEqual(adapter.calls, 1)
            self.store.give_more_tries(job_id)
            engine.wait(job_id, timeout=3)
            self.assertEqual(adapter.calls, 2)
            for expected in (3, 4):
                self.store.give_more_tries(job_id)
                engine.wait(job_id, timeout=3)
                for _ in range(3): engine.tick()
                self.assertEqual(adapter.calls, expected)
        finally:
            engine.close()

    def test_explicit_resume_rearms_one_orphaned_or_paused_image_attempt(self):
        class ImageAdapter:
            calls = 0
            def ready(adapter): return True
            def execute(adapter, prompt, **kwargs):
                adapter.calls += 1
                return {'outcome': 'FAILED', 'error': 'Fixture image tool failed.'}
        adapter = ImageAdapter()
        engine = Engine(self.store, {'image-generation': adapter})
        try:
            for mode in ('orphaned', 'paused'):
                with self.subTest(mode=mode):
                    job_id = engine.submit(self.image_contract())
                    run = self.store.claim(job_id, 'image', 'image-generation', timeout=-1)
                    if mode == 'orphaned':
                        self.store.recover_abandoned()
                        self.store.reopen(job_id)
                    else:
                        self.store.control(job_id, 'pause')
                        self.store.acknowledge_stop(run['id'], run['epoch'])
                        self.store.control(job_id, 'resume')
                    before = adapter.calls
                    job = engine.wait(job_id, timeout=3)
                    self.assertEqual(adapter.calls, before + 1)
                    self.assertEqual(job['state'], 'WAITING_RESOURCE')
                    for _ in range(3): engine.tick()
                    self.assertEqual(adapter.calls, before + 1)
        finally:
            engine.close()


if __name__ == '__main__':
    unittest.main()
