"""Scoping answers typed in the chat (D-70 item 4): while a scoping card is open, answers typed in the
conversation go through the same `VettingAnswerIngestion` into that card's session, the card shows
them, and nothing new starts; "start" or "go" starts the work with them. Fake models only.
"""
import contextlib
import json
import sys
import unittest
from pathlib import Path

from kel import scoping

sys.path.insert(0, str(Path(__file__).parent))
from test_d70_cards import QUESTIONS, SMALL_WORK, ServiceBase  # noqa: E402

REQUEST = 'Write me a spring garden plan for the back yard'
Q = [{'id': 'Q1', 'prompt': 'Who is it for?', 'options': [{'code': 'A', 'label': 'Just me'}, {'code': 'B', 'label': 'My team'},
                                                          {'code': 'C', 'label': 'The public'}]},
     {'id': 'Q2', 'prompt': 'How long?', 'options': [{'code': 'A', 'label': 'One page'},
                                                      {'code': 'B', 'label': 'Two or three pages'}]}]


class NormalizeTests(unittest.TestCase):
    def test_the_forms_nick_types(self):
        self.assertEqual(scoping.normalize_typed('1A 2B', Q), '1: A\n2: B')
        self.assertEqual(scoping.normalize_typed('1c, 2a', Q), '1: C\n2: A')
        self.assertEqual(scoping.normalize_typed('1: my team\n2: a single index card', Q),
                         '1: B\n2: none of these: a single index card')
        self.assertEqual(scoping.normalize_typed('just me, one page', Q), '1: A\n2: A')
        self.assertEqual(scoping.normalize_typed('the public; a postcard', Q), '1: C\n2: none of these: a postcard')
        # Two parts that match nothing are not read as answers in order.
        self.assertEqual(scoping.normalize_typed('a website, with a blog', Q), 'a website, with a blog')

    def test_start_words(self):
        for text in ('start', 'Go', 'go ahead', 'ok, start', "let's go", 'Start now!'):
            self.assertTrue(scoping.START_WORDS.match(text), text)
        for text in ('start a new essay about bees', 'going to the shop'):
            self.assertFalse(scoping.START_WORDS.match(text), text)


class TypedAnswerTests(ServiceBase):
    def open_card(self):
        self.turn.answer = dict(SMALL_WORK, scoping=QUESTIONS)
        sid = self.service.submit({'text': REQUEST, 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        return self.scopings()[0]

    def jobs(self):
        return [j for j in self.service.store.list_jobs() if j['conversation'] == self.cid]

    def test_typed_answers_land_on_the_card_and_start_nothing(self):
        row = self.open_card()
        calls = len(self.turn.calls)
        sid = self.service.submit({'text': '1: the public\n2: a single index card', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        self.assertEqual(len(self.turn.calls), calls, 'the turn model never saw it')
        self.assertEqual(self.jobs(), [])
        view = scoping.view(self.service.store, row['id'], self.cid)
        self.assertEqual(view['state'], 'open')
        self.assertEqual(view['recorded'], {'Q1': {'option': 'C', 'text': None, 'label': 'The public'},
                                            'Q2': {'option': None, 'text': 'a single index card',
                                                   'label': 'a single index card'}})
        said = self.messages()[-1]['text']
        self.assertTrue(said.startswith('Got it: Who is it for? The public; How long? a single index card.'), said)
        self.assertIn('Say "start"', said)
        # The same ingestion path recorded them (source: chat).
        with contextlib.closing(self.service.store.connect()) as db:
            sources = {r['question_id']: r['source'] for r in db.execute(
                'SELECT question_id, source FROM vetting_answers WHERE session_id=?', (row['session_id'],))}
        self.assertEqual(sources, {'Q1': 'chat', 'Q2': 'chat'})

    def test_start_typed_in_the_chat_starts_with_the_recorded_answers(self):
        row = self.open_card()
        self.service.submit({'text': '1C', 'conversation': self.cid})
        sid = self.service.submit({'text': 'go', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        view = scoping.view(self.service.store, row['id'])
        self.assertEqual(view['state'], 'started')
        self.assertEqual(self.wait(view['started_submission']), 'DISPATCHED')
        jobs = self.jobs()
        self.assertEqual(len(jobs), 1)
        answers = jobs[0]['contract']['context']['scoping']['answers']
        self.assertEqual([(a['answer'], a['assumed']) for a in answers], [('The public', False), ('One page', True)])

    def test_other_messages_still_go_to_kel(self):
        self.open_card()
        calls = len(self.turn.calls)
        self.turn.answer = {'action': 'reply', 'text': 'Tomatoes like sun.'}
        sid = self.service.submit({'text': 'How much sun do tomatoes need?', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        self.assertEqual(len(self.turn.calls), calls + 1)
        self.assertEqual(self.messages()[-1]['text'], 'Tomatoes like sun.')
        self.assertEqual(scoping.view(self.service.store, self.scopings()[0]['id'])['recorded'], {})

    def test_no_open_card_means_start_is_an_ordinary_message(self):
        self.turn.answer = {'action': 'reply', 'text': 'Start what?'}
        sid = self.service.submit({'text': 'start', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        self.assertEqual(self.messages()[-1]['text'], 'Start what?')


if __name__ == '__main__':
    unittest.main()
