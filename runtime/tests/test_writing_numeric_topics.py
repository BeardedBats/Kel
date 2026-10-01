"""Numeric subject facts do not erase an explicit trusted word limit."""
import unittest
from kel.word_limits import parse


class NumericTopicTests(unittest.TestCase):
    def test_topic_years_times_and_quantities_keep_word_limit(self):
        requests=['Write exactly 50 words about 2020.',
                  'Write exactly 50 words about roughly 100 years of local history.',
                  'Write under 50 words about a meeting around 10 AM.',
                  'Write a 50-word paragraph about 3 useful project notes.']
        for request in requests:
            with self.subTest(request=request):
                limit=parse(request)
                self.assertIsNotNone(limit)
                self.assertEqual(limit['maximum'],49 if 'under' in request else 50)

    def test_actual_approximate_or_range_word_counts_remain_deferred(self):
        for request in ('Write about 50 words.','Write roughly 50 words.','Write approximately 50-word paragraph.',
                        'Write around 50 words.','Write at least 50 words.','Write between 50 and 100 words.'):
            with self.subTest(request=request):self.assertIsNone(parse(request))

    def test_quoted_numeric_length_never_creates_a_limit(self):
        self.assertIsNone(parse('Explain "Write exactly 50 words about 2020."'))
        self.assertEqual(parse('Write exactly 50 words about "around 100 words".'),{'minimum':50,'maximum':50})
