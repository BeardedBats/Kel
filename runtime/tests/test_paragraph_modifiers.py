"""Known direct prose modifiers retain the same narrow constraint boundaries."""
import unittest
from kel.word_limits import parse
from kel.prose_review import enabled


class ParagraphModifiers(unittest.TestCase):
    def test_explicit_known_modifiers_enable_existing_prose_gate(self):
        for modifier in ('short', 'brief', 'concise'):
            with self.subTest(modifier=modifier):
                limit = parse('Write two '+modifier+' paragraphs. Use only these facts: notes preserve decisions.')
                self.assertEqual(limit, {'paragraphs':2, 'prose_ending_basis':'sentence-punctuation'})
                self.assertTrue(enabled(limit))
        self.assertEqual(parse('Write exactly 50 words in two short paragraphs.')['paragraphs'], 2)

    def test_ambiguous_per_part_quoted_and_structured_modifiers_defer(self):
        for request in (
            'Write about two short paragraphs.',
            'Write between one and two brief paragraphs.',
            'Write one to two concise paragraphs.',
            'Write two short paragraphs and one brief paragraph.',
            'Write two short paragraphs with 10 words each.',
            'Write exactly 50 words per short paragraph.',
            'Write two short paragraphs each with a separate topic.',
            'Explain this: "Write two short paragraphs."',
            'Explain this:\n> Write two short paragraphs.',
            'Write two short paragraphs as a numbered list.',
        ):
            with self.subTest(request=request):
                self.assertIsNone(parse(request))
        self.assertEqual(parse('Write exactly 50 words in two brief paragraphs as a Markdown table.'),
                         {'minimum':50, 'maximum':50})
