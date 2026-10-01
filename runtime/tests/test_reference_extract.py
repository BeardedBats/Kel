"""Actual bounded extraction and rejection checks; only generated fixtures."""
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from kel.reference_extract import extract_reference, _kind, _pdf, _slot, _bounded_worker


def pdf_bytes(text='Reference notes preserve decisions.'):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=200)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(f'BT /F1 16 Tf 10 100 Td ({text}) Tj ET'.encode('ascii'))
    page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class Extraction(unittest.TestCase):
    def test_worker_output_cannot_fill_parent_memory(self):
        import sys
        with self.assertRaisesRegex(ValueError, 'text limit'):
            _bounded_worker([sys.executable, '-c', 'import sys; sys.stdout.write("x"*300000)'], {})

    def test_actual_bounded_pdf_child(self):
        result = extract_reference('reference.pdf', pdf_bytes())
        self.assertEqual(result['text'], 'Reference notes preserve decisions.')
        self.assertEqual((result['kind'], result['extraction'], result['pages']), ('pdf', 'pdf-text', 1))

    def test_corrupt_pdf_safe_error(self):
        with self.assertRaisesRegex(ValueError, 'could not read this PDF'):
            extract_reference('bad.pdf', b'%PDF-1.7\nnot a pdf')

    def test_no_text_pdf_not_silently_accepted(self):
        from pypdf import PdfWriter
        writer = PdfWriter(); writer.add_blank_page(width=600, height=200)
        data = io.BytesIO(); writer.write(data)
        with self.assertRaisesRegex(ValueError, 'without readable text'):
            _pdf(data.getvalue())

    def test_encrypted_pdf_rejected(self):
        from pypdf import PdfWriter
        writer = PdfWriter(); writer.add_blank_page(width=600, height=200); writer.encrypt('synthetic-password')
        data = io.BytesIO(); writer.write(data)
        with self.assertRaisesRegex(ValueError, 'password protection'):
            _pdf(data.getvalue())

    def test_file_type_name_size_and_single_slot(self):
        for name, data in [('bad.pdf', b'not pdf'), ('../read.pdf', pdf_bytes()), ('large.pdf', b'%PDF-'+b'a'*5_000_000)]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                _kind(name, data)
        self.assertTrue(_slot.acquire(blocking=False))
        try:
            with self.assertRaisesRegex(ValueError, 'another reference'):
                extract_reference('reference.pdf', pdf_bytes())
        finally:
            _slot.release()

    def test_pdf_page_limit(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        for _ in range(21): writer.add_blank_page(width=10, height=10)
        data = io.BytesIO(); writer.write(data)
        with self.assertRaisesRegex(ValueError, '20 pages'):
            _pdf(data.getvalue())


if __name__ == '__main__': unittest.main()
