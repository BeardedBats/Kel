"""D-75.2: edit a sent message and regenerate Kel's last reply.

Rewinding hides the edited message and the direct replies after it from everything Kel reads; work
already handed off (its acknowledgement, card and result) stays and is never re-run; editing a
message that started work makes the next message an amendment of that work (D-55). No real model.
"""
import contextlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

from kel.core import PolicyError
from kel.service import Service


class FakeTurn:
    def __init__(self):
        self.prompts = []
        self.count = 0

    def execute(self, prompt, system=None, images=None, cancel=None, **kwargs):
        self.prompts.append(prompt)
        latest = prompt.split('latest message:')[-1].lower()
        if 'garden plan' in latest:
            answer = {'action': 'start_background_work', 'title': 'Garden plan',
                      'acknowledgement': "I'm starting on that now in the background; I'll post it here once it's been checked.",
                      'related_topic': None}
        else:
            self.count += 1
            answer = {'action': 'reply', 'text': 'Answer %d to %s' % (self.count, latest.strip())}
        return {'outcome': 'SUCCESS', 'text': json.dumps(answer)}


class RewindTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        for name in ('ANTHROPIC_API_KEY', 'KEL_INTERNAL_MODEL'):
            os.environ.pop(name, None)
        os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none')
        self.service = Service(str(Path(self.tmp.name) / 'engine'))
        self.turn = FakeTurn()
        self.service.turn_mode = ''
        self.service.model = self.turn
        self.service.engine.adapters = {}
        self.service.stop.set()
        self.cid = self.service.context.conversation('default')

    def tearDown(self):
        with contextlib.suppress(Exception):
            self.service.shutdown()
        self.tmp.cleanup()

    def send(self, text, states=('SETTLED', 'DISPATCHED', 'FAILED')):
        sid = self.service.submit({'text': text, 'conversation': self.cid})
        deadline = time.time() + 20
        while time.time() < deadline:
            row = next(s for s in self.service.state(self.cid)['submissions'] if s['id'] == sid)
            if row['state'] in states or row.get('ack_seq'):
                return sid
            time.sleep(.02)
        raise TimeoutError(sid)

    def texts(self):
        return [(m['role'], m['text']) for m in self.service.state(self.cid)['messages']]

    def rewind(self, **data):
        return self.service.action('/api/rewind', dict(data, conversation=self.cid))

    def test_regenerate_rewinds_the_last_reply_and_its_question(self):
        self.send('what is basil')
        self.send('what is thyme')
        out = self.rewind(action='regenerate')
        self.assertEqual(out['text'], 'what is thyme')
        self.assertEqual([m['role'] for m in out['rewound']], ['user', 'assistant'])
        self.assertEqual(self.texts(), [('user', 'what is basil'), ('assistant', 'Answer 1 to what is basil')])
        self.send(out['text'])  # the desktop sends it again
        self.assertEqual(self.texts()[-1], ('assistant', 'Answer 3 to what is thyme'))
        # The rewound answer is not in what Kel read for the new one.
        self.assertNotIn('Answer 2', self.turn.prompts[-1])

    def test_edit_rewinds_from_the_edited_message(self):
        self.send('what is basil')
        self.send('what is thyme')
        out = self.rewind(action='edit', text='what is basil')
        self.assertEqual(out['mode'], 'rewind')
        self.assertEqual(len(out['rewound']), 4)
        self.assertEqual(self.texts(), [])
        self.send('what is sage')
        self.assertEqual(self.texts(), [('user', 'what is sage'), ('assistant', 'Answer 3 to what is sage')])
        self.assertNotIn('thyme', self.turn.prompts[-1])

    def test_the_occurrence_picks_which_identical_message(self):
        self.send('hello')
        self.send('hello')
        out = self.rewind(action='edit', text='hello', occurrence=1)  # the first one
        self.assertEqual(len(out['rewound']), 4)
        with self.assertRaises(PolicyError):
            self.rewind(action='edit', text='not said')

    def test_handed_off_work_is_never_rewound_or_regenerated(self):
        gate = []
        self.service._compile_work = lambda *args, **kwargs: gate.append(1) or time.sleep(30)
        self.send('what is basil')
        self.send('write me a garden plan')
        with self.assertRaisesRegex(PolicyError, "doesn't run work again"):
            self.rewind(action='regenerate')
        # Editing the first message keeps the hand-off and its acknowledgement.
        out = self.rewind(action='edit', text='what is basil')
        self.assertEqual([m['role'] for m in out['rewound']], ['user', 'assistant'])
        self.assertEqual([m['text'] for m in out['kept']][0], 'write me a garden plan')
        self.assertEqual(self.texts()[0], ('user', 'write me a garden plan'))

    def test_editing_a_message_that_started_work_amends_that_work(self):
        self.service._compile_work = lambda *args, **kwargs: time.sleep(30)
        sid = self.send('write me a garden plan')
        out = self.rewind(action='edit', text='write me a garden plan')
        self.assertEqual((out['mode'], out['submission'], out['rewound']), ('amend', sid, []))
        self.send('write me a garden plan for a shady yard')
        said = [t for r, t in self.texts() if r == 'assistant']
        self.assertTrue(any(t.startswith('Restarting') for t in said), said)
        # Still one hand-off: the edited request replaced the original's text.
        row = next(s for s in self.service.state(self.cid)['submissions'] if s['id'] == sid)
        self.assertEqual(row['text'], 'write me a garden plan for a shady yard')

    def test_hidden_rows_are_remembered(self):
        self.assertEqual(self.rewind(action='hidden')['rows'], [])
        self.rewind(action='hide', rows=['a1', 'b2'])
        self.assertEqual(self.rewind(action='hidden')['rows'], ['a1', 'b2'])


if __name__ == '__main__':
    unittest.main()
