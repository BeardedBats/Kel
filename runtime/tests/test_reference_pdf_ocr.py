"""Generated PDF bytes only: real Windows OCR plus bounded fallback contracts."""
import io
import json
import hashlib
import os
import unittest
from unittest.mock import patch

from kel.reference_extract import _pdf, extract_reference, _bounded_worker
from test_reference_extract import pdf_bytes


def scanned_pdf(blank=False):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB', (1200, 500), 'white')
    if not blank:
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 48)
        ImageDraw.Draw(image).text((70, 170), 'Notes preserve decisions.', font=font, fill='black')
    output = io.BytesIO()
    image.save(output, format='PDF', resolution=144)
    return output.getvalue()


class PdfOcr(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Built-in PDF OCR requires Windows')
    def test_actual_scanned_and_mixed_pdf_local_workers(self):
        from pypdf import PdfReader, PdfWriter
        scan = scanned_pdf()
        result = extract_reference('scan.pdf', scan)
        self.assertEqual(result['extraction'], 'pdf-ocr')
        self.assertEqual(result['pages'], 1)
        self.assertIn('Notes preserve decisions.', result['text'])
        self.assertTrue(result['language'])
        print(json.dumps({'source_sha256': hashlib.sha256(scan).hexdigest(), 'case': 'scanned', 'result': result}))
        writer = PdfWriter()
        writer.append(PdfReader(io.BytesIO(pdf_bytes('Notes explain reasons.'))))
        writer.append(PdfReader(io.BytesIO(scan)))
        output = io.BytesIO(); writer.write(output)
        mixed = extract_reference('mixed.pdf', output.getvalue())
        self.assertEqual(mixed['pages'], 2)
        self.assertEqual(mixed['extraction'], 'pdf-ocr')
        self.assertTrue(mixed['text'].startswith('Notes explain reasons.\n\n'))
        self.assertIn('Notes preserve decisions.', mixed['text'])
        print(json.dumps({'source_sha256': hashlib.sha256(output.getvalue()).hexdigest(), 'case': 'mixed', 'result': mixed}))

    @unittest.skipUnless(os.name == 'nt', 'Built-in PDF OCR requires Windows')
    def test_actual_blank_scanned_page_rejected(self):
        with self.assertRaisesRegex(ValueError, 'without readable text'):
            extract_reference('blank.pdf', scanned_pdf(blank=True))

    def test_all_pages_validated_before_trusted_ocr_signal(self):
        from pypdf import PdfWriter
        from pypdf.generic import NameObject, DecodedStreamObject
        writer = PdfWriter(); writer.add_blank_page(width=100, height=100)
        page = writer.add_blank_page(width=100, height=100)
        stream = DecodedStreamObject(); stream.set_data(b' ' * 8_000_001)
        page[NameObject('/Contents')] = writer._add_object(stream)
        output = io.BytesIO(); writer.write(output)
        with self.assertRaisesRegex(ValueError, 'too large'):
            _pdf(output.getvalue(), allow_ocr=True)

    def test_fallback_shares_deadline_and_preserves_readable_page(self):
        control = {'needs_ocr': True, 'pages': 2, 'page_texts': ['Known text.', ''], 'missing_pages': [1]}
        final = {'text': 'Known text.\n\nScanned text.', 'pages': 2, 'language': 'en-US', 'extraction': 'pdf-ocr'}
        with patch('kel.reference_extract._bounded_worker', side_effect=[control, final]) as worker, patch('kel.reference_extract.time.monotonic', side_effect=[10, 12, 17]):
            answer = extract_reference('mixed.pdf', b'%PDF-synthetic')
        self.assertEqual(answer['text'], final['text'])
        self.assertEqual([call.kwargs['timeout'] for call in worker.call_args_list], [18, 13])
        self.assertEqual(worker.call_args_list[1].args[1]['page_texts'], ['Known text.', ''])
        self.assertEqual(worker.call_args_list[1].args[1]['missing_pages'], [1])

    def test_page_count_mismatch_fails_closed(self):
        control = {'needs_ocr': True, 'pages': 1, 'page_texts': [''], 'missing_pages': [0]}
        wrong = {'text': 'Text.', 'pages': 2, 'language': 'en-US', 'extraction': 'pdf-ocr'}
        with patch('kel.reference_extract._bounded_worker', side_effect=[control, wrong]), self.assertRaisesRegex(ValueError, 'validate'):
            extract_reference('scan.pdf', b'%PDF-synthetic')

    def test_worker_startup_consumes_remaining_deadline(self):
        class Process:
            stdin = io.BytesIO()
            stdout = io.BytesIO(b'{"text":"Text."}')
            returncode = 0
            waits = []
            def wait(self, timeout):
                self.waits.append(timeout)
            def poll(self):
                return 0
        child = Process()
        with patch('kel.reference_extract.subprocess.Popen', return_value=child), patch('kel.windows_job.bound_child_process', return_value=lambda: None), patch('kel.reference_extract.time.monotonic', side_effect=[10, 15]):
            result = _bounded_worker(['fixed-worker'], {}, timeout=8)
        self.assertEqual(child.waits, [3, 5])
        self.assertEqual(result['text'], 'Text.')

    def test_invalid_parser_control_never_starts_native_fallback(self):
        import sys
        invalid = {'needs_ocr': True, 'pages': 1, 'page_texts': ['Text.'], 'missing_pages': [0]}
        command = [sys.executable, '-c', 'import json; print(json.dumps(' + repr(invalid) + '))']
        with self.assertRaisesRegex(ValueError, 'validate the PDF'):
            _bounded_worker(command, {}, allow_ocr=True)


if __name__ == '__main__': unittest.main()


def test_ocr_custody_import_keeps_original_language_and_provenance(tmp_path):
    from kel.core import Store
    from kel.reference_sources import ReferenceSources
    from kel.work_import import WorkImports
    import contextlib
    store = Store(tmp_path / 'engine')
    with contextlib.closing(store.connect()) as db:
        db.executescript('CREATE TABLE projects(id TEXT PRIMARY KEY,name TEXT,root TEXT,context TEXT,updated REAL);'
                        'CREATE TABLE conversations(id TEXT PRIMARY KEY,project_id TEXT,title TEXT,created REAL);'
                        'CREATE TABLE chat_state(conversation_id TEXT PRIMARY KEY,deleted_at REAL);')
        db.execute("INSERT INTO projects VALUES('p','Project',NULL,'',1)")
    sources, imports = ReferenceSources(store), WorkImports(store)
    raw = b'%PDF-synthetic-inert'
    staged = sources.stage('p', 'scan.pdf', raw, 'Notes preserve decisions.', 'pdf', 'pdf-ocr', 1, 'en-US')
    preview = imports.preview('p', 'Reference transcript.', extraction_ids=[staged['id']])
    receipt = imports.confirm(preview['preview_id'], preview['digest'], 'p', confirm=True)
    original = sources.original('p', staged['id'])
    assert original['bytes'] == raw
    assert original['metadata']['extraction'] == 'pdf-ocr'
    assert original['metadata']['language'] == 'en-US'
    assert original['metadata']['trust'] == 'external-untrusted'
    assert original['metadata']['state'] == 'adopted'
    assert receipt['conversation_id']
