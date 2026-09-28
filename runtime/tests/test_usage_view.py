"""What Kel's messages and each piece of work used: tokens, time, approximate cost, which model.

Each of Kel's own messages carries its usage in its metadata (the chips under the reply); a job's
totals ride on `/api/office/item`; `GET /api/usage` reads both. A subscription call is "included in
your plan", never $0.00; an unknown cost stays unknown. Fake models only.
"""
import contextlib
import json
import sys
import time
import unittest
from pathlib import Path

from kel import staff, usage
from kel.core import PolicyError

sys.path.insert(0, str(Path(__file__).parent))
from test_d72_defaults import ServiceCase, UsageTurn  # noqa: E402


class SummaryTests(unittest.TestCase):
    def test_plan_metered_and_mixed(self):
        plan = {'subscription': True, 'processed': 1000, 'wall_ms': 1200, 'cost_usd': 0.05,
                'cost_basis': 'reported', 'model': 'claude-opus-5-5'}
        metered = {'subscription': False, 'processed': 400, 'wall_ms': 800, 'cost_usd': 0.0004,
                   'cost_basis': 'estimated', 'model': 'deepseek-flash'}
        out = usage.summarize([plan])
        self.assertEqual((out['billing'], out['cost'], out['plan_cost_equivalent']), ('plan', None, 0.05))
        self.assertEqual((out['tokens'], out['ms'], out['model_label']), (1000, 1200, 'Claude Opus 5.5'))
        out = usage.summarize([metered])
        self.assertEqual((out['billing'], out['cost'], out['cost_basis']), ('metered', 0.0004, 'estimated'))
        out = usage.summarize([plan, metered])
        self.assertEqual((out['billing'], out['calls'], out['tokens'], out['models']),
                         ('mixed', 2, 1400, ['Claude Opus 5.5', 'DeepSeek Flash']))
        self.assertIsNone(usage.summarize([]))

    def test_an_unknown_metered_cost_is_never_free(self):
        out = usage.summarize([{'subscription': False, 'processed': 10, 'cost_usd': None}])
        self.assertIsNone(out['cost'])
        self.assertEqual(out['billing'], 'metered')


class MessageUsageTests(ServiceCase):
    def messages(self):
        with contextlib.closing(self.service.store.connect()) as db:
            return [dict(r) for r in db.execute("SELECT * FROM messages WHERE conversation_id=? AND role='assistant' "
                                                'ORDER BY seq', (self.cid,))]

    def test_a_reply_carries_its_usage(self):
        self.service.model = UsageTurn({'action': 'reply', 'text': 'Six to eight hours of sun.'})
        sid = self.service.submit({'text': 'How much sun do tomatoes need?', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        message = self.messages()[-1]
        used = json.loads(message['meta'])['usage']
        self.assertEqual((used['tokens'], used['billing'], used['model_label'], used['calls']),
                         (860, 'plan', 'ChatGPT Luna', 1))
        view = self.service.usage_view(self.cid)
        self.assertEqual(view['messages'][str(message['seq'])]['tokens'], 860)

    def test_a_handoff_acknowledgement_carries_the_turn_and_the_work_its_totals(self):
        self.service.model = UsageTurn({'action': 'start_background_work', 'title': 'Garden plan',
                                        'acknowledgement': "On it — I'll post it here once it's checked.",
                                        'related_topic': None})
        sid = self.service.submit({'text': 'Write me a spring garden plan for the back yard',
                                   'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        ack = next(m for m in self.messages() if 'On it' in m['text'])
        self.assertEqual(json.loads(ack['meta'])['usage']['tokens'], 860)
        with contextlib.closing(self.service.store.connect()) as db:
            job_id = db.execute('SELECT job_id FROM submissions WHERE id=?', (sid,)).fetchone()['job_id']
        usage.record(self.service.store, 'run-1', job_id=job_id, adapter='deepseek', model='deepseek-flash',
                     result={'usage': {'prompt_tokens': 100, 'completion_tokens': 20}, 'wall_ms': 900})
        totals = self.service.usage_view(job=job_id)['usage']
        self.assertEqual((totals['billing'], totals['tokens'], totals['ms']), ('metered', 120, 900))
        if staff.staffing_of(self.service.store.get(job_id)):
            self.assertEqual(self.service.office_item(job_id)['usage']['tokens'], 120)
        with self.assertRaisesRegex(PolicyError, 'Pick a conversation'):
            self.service.usage_view()


if __name__ == '__main__':
    unittest.main()
