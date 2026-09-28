"""Routing 2 §5.6 — DeepSeek (and OpenRouter as a second route) as bounded text workers.

The key reaches only the engine's environment (the desktop injects it from its OS-backed custody);
without it the worker is not registered and Settings says the key is needed. No network call is made:
every transport here is a fake that records the request.
"""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from kel import role_models, staff
from kel.api_models import OpenAICompatAdapter, has_key
from kel.core import Store


class Transport:
    def __init__(self, answer=None, error=None):
        self.answer, self.error, self.sent = answer, error, []

    def __call__(self, body, timeout):
        self.sent.append(body)
        if self.error:
            raise self.error
        return self.answer


DEEPSEEK_ANSWER = {'model': 'deepseek-flash', 'choices': [{'message': {'role': 'assistant', 'content': '- a\n- b'}}],
                   'usage': {'prompt_tokens': 120, 'completion_tokens': 8, 'prompt_cache_hit_tokens': 100}}


class AdapterTests(unittest.TestCase):
    def test_a_bounded_text_call_reports_the_model_and_usage(self):
        transport = Transport(DEEPSEEK_ANSWER)
        result = OpenAICompatAdapter('deepseek', 'deepseek-flash', transport=transport).execute('Tidy: b, a')
        self.assertEqual((result['outcome'], result['text'], result['model_used']), ('SUCCESS', '- a\n- b', 'deepseek-flash'))
        self.assertEqual(result['usage']['prompt_cache_hit_tokens'], 100)
        body = transport.sent[0]
        self.assertEqual((body['model'], body['stream'], body['messages'][1]['content']), ('deepseek-flash', False, 'Tidy: b, a'))
        self.assertNotIn('tools', body, 'text in, text out: no tools')
        self.assertNotIn('usage', body)

    def test_openrouter_asks_for_its_cost_and_uses_its_model_id(self):
        transport = Transport(dict(DEEPSEEK_ANSWER, model='deepseek/deepseek-v4.1-flash',
                                   usage={'prompt_tokens': 10, 'completion_tokens': 2, 'cost': 0.00001}))
        adapter = OpenAICompatAdapter('openrouter', role_models.model_arg('deepseek-flash', 'openrouter'),
                                      transport=transport)
        result = adapter.execute('x')
        self.assertEqual(transport.sent[0]['model'], 'deepseek/deepseek-v4.1-flash')
        self.assertEqual(transport.sent[0]['usage'], {'include': True})
        from kel.usage import normalize
        self.assertEqual(normalize(result, model='deepseek-flash')['cost_basis'], 'reported')

    def test_failures_keep_the_services_words_and_never_the_key(self):
        saved = os.environ.get('DEEPSEEK_API_KEY')
        os.environ['DEEPSEEK_API_KEY'] = 'sk-secret-value-123456'
        try:
            transport = Transport(error=RuntimeError('HTTP 400: Model Not Exist (key sk-secret-value-123456)'))
            seen = []
            adapter = OpenAICompatAdapter('deepseek', transport=transport)
            adapter.on_refusal = lambda error, version: seen.append(error)
            result = adapter.execute('x')
        finally:
            if saved is None:
                os.environ.pop('DEEPSEEK_API_KEY', None)
            else:
                os.environ['DEEPSEEK_API_KEY'] = saved
        self.assertEqual(result['outcome'], 'FAILED')
        self.assertIn('Model Not Exist', result['error'])
        self.assertNotIn('sk-secret', result['error'])
        self.assertEqual(role_models.classify_refusal(seen[0], 'deepseek-flash')[0], 'not_found')

    def test_without_a_key_it_says_so(self):
        saved = os.environ.pop('DEEPSEEK_API_KEY', None)
        try:
            self.assertFalse(has_key('deepseek'))
            result = OpenAICompatAdapter('deepseek').execute('x')
        finally:
            if saved is not None:
                os.environ['DEEPSEEK_API_KEY'] = saved
        self.assertIn('DEEPSEEK_API_KEY is needed', result['error'])

    def test_images_and_oversized_input_are_refused_plainly(self):
        adapter = OpenAICompatAdapter('deepseek', transport=Transport(DEEPSEEK_ANSWER))
        self.assertIn('text only', adapter.execute('x', images=[{'mime': 'image/png', 'data': ''}])['error'])
        self.assertIn('input budget', adapter.execute('x' * 70000)['error'])


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ['CODEX_HOME'] = str(Path(self.tmp.name) / 'codex-home')
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)

    def test_utility_runs_on_deepseek_flash_when_its_key_is_set_up(self):
        out = role_models.resolve(self.store, 'utility', adapters={'codex', 'deepseek'}, task_class='utility')
        self.assertEqual((out['adapter'], out['model'], out['model_arg']), ('deepseek', 'deepseek-flash', 'deepseek-flash'))
        self.assertIsNone(out['why'])

    def test_openrouter_is_the_second_route(self):
        out = role_models.resolve(self.store, 'utility', adapters={'codex', 'openrouter'}, task_class='utility')
        self.assertEqual((out['adapter'], out['model_arg']), ('openrouter', 'deepseek/deepseek-v4.1-flash'))

    def test_without_a_key_settings_say_it_is_needed(self):
        rows = {row['role']: row for row in role_models.listing(self.store, {'codex', 'claude'})['roles']}
        self.assertFalse(rows['utility']['available'])
        self.assertIn('needs a DeepSeek API key', rows['utility']['note'])

    def test_the_engine_hands_a_staffed_utility_step_to_deepseek(self):
        from kel.engine import Engine
        text = 'Rename these list items to title case'
        contract = {'request': text, 'milestones': [{'id': 'd', 'objective': text, 'filename': 'd.md',
                                                     'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 3}]}],
                    'classification': {'task_class': 'utility', 'tier': 'fast'}}
        record = staff.plan_job(self.store, contract)
        record['steps']['d'].update(role='utility', task_class='utility', dispatch='fast')
        contract['staffing'] = record
        job = self.store.create(contract)

        class Fake:
            capabilities = {'text'}

            def __init__(self):
                self.calls = []

            def execute(self, prompt, run_id=None, session_id=None, cancel=None):
                self.calls.append(run_id)
                return {'outcome': 'SUCCESS', 'text': '- Apples\n- Bread', 'model_used': 'deepseek-flash',
                        'usage': {'prompt_tokens': 50, 'completion_tokens': 5}}

        deepseek, codex = Fake(), Fake()
        engine = Engine(self.store, {'deepseek': deepseek, 'codex': codex})
        try:
            deadline = time.time() + 20
            while time.time() < deadline and not (deepseek.calls or codex.calls):
                engine.tick()
                time.sleep(.02)
        finally:
            engine.close()
        self.assertEqual((len(deepseek.calls), len(codex.calls)), (1, 0))
        call = staff.calls(self.store, job)[0]
        self.assertEqual((call['asked']['model'], call['ran']['adapter']), ('deepseek-flash', 'deepseek'))


class ServiceTests(unittest.TestCase):
    def test_the_service_registers_the_workers_its_keys_allow(self):
        from kel.service import Service
        from kel.api_models import OpenAICompatAdapter as Adapter
        with tempfile.TemporaryDirectory() as tmp:
            saved = dict(os.environ)
            try:
                os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none',
                                  CODEX_HOME=str(Path(tmp) / 'codex-home'), DEEPSEEK_API_KEY='sk-test-not-real')
                os.environ.pop('ANTHROPIC_API_KEY', None)
                os.environ.pop('OPENROUTER_API_KEY', None)
                service = Service(Path(tmp) / 'data')
                try:
                    self.assertIn('deepseek', service.engine.adapters)
                    self.assertNotIn('openrouter', service.engine.adapters)
                    self.assertIn('deepseek', service.staff_adapters())
                    binding = role_models.resolve(service.store, 'utility', adapters=service.staff_adapters(),
                                                  task_class='utility')
                    worker = service.staff_model(binding)
                    self.assertIsInstance(worker, Adapter)
                    self.assertEqual((worker.provider, worker.model), ('deepseek', 'deepseek-flash'))
                    listing = {row['role']: row for row in service.action('/api/model', {'action': 'roles'})['roles']}
                    self.assertTrue(listing['utility']['available'])
                finally:
                    service.shutdown()
            finally:
                os.environ.clear()
                os.environ.update(saved)


if __name__ == '__main__':
    unittest.main()
