"""Actual bounded PDF child extraction at the conversation handoff."""
import io
import tempfile
import unittest
from kel.context import Context
from kel.core import Store, PolicyError
from test_reference_extract import pdf_bytes


class PDFHandoff(unittest.TestCase):
    def test_readable_pdf_uses_derived_text_and_source_metadata(self):
        with tempfile.TemporaryDirectory() as root:
            context=Context(Store(root))
            aid=context.attach('main','notes.pdf',pdf_bytes())
            file=context.handoff('main','Summarize selected notes.',[aid])['files'][0]
            self.assertEqual(file['text'],'Reference notes preserve decisions.')
            self.assertNotIn('%PDF',file['text'])
            self.assertEqual((file['kind'],file['extraction'],file['pages'],file['trust']),('pdf','pdf-text',1,'external-untrusted'))
            self.assertEqual(file['source_digest'],file['sha256'])

    def test_no_text_pdf_fails_instead_of_sending_syntax(self):
        from pypdf import PdfWriter
        writer=PdfWriter();writer.add_blank_page(width=10,height=10)
        output=io.BytesIO();writer.write(output)
        with tempfile.TemporaryDirectory() as root:
            context=Context(Store(root));aid=context.attach('main','empty.pdf',output.getvalue())
            with self.assertRaisesRegex(PolicyError,'without readable text'):context.handoff('main','Summarize.',[aid])
