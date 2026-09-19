"""V1.5 G4: credential hygiene — the key reaches only the intended request, never durable data.

Leak vectors checked here: transport/provider error messages, request bodies, native CLI child
environments, test-command environments, and every durable byte of a store after a completed
worker run. (Renderer exposure and export paths are covered by the custody tests and
`packaging/verify-credentials.cjs`.)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kel.core import Store
from kel.host_runtime import test_command_env as host_test_command_env
from kel.internal import InternalAdapter, redact
from kel.native import child_env

SECRET = 'sk-test-secret-abcdef1234567890'


class RedactionTests(unittest.TestCase):
    def test_redact_strips_secret_shaped_tokens_and_live_values(self):
        with mock.patch.dict(os.environ, {'ANTHROPIC_API_KEY': SECRET}):
            cleaned = redact('401 from key ' + SECRET + ' and sk-other-token-123456789')
        self.assertNotIn(SECRET, cleaned)
        self.assertNotIn('sk-other-token', cleaned)
        self.assertIn('[redacted]', cleaned)

    def test_transport_errors_never_echo_the_key(self):
        def transport(body, timeout):
            raise RuntimeError('boom with ' + SECRET)

        with mock.patch.dict(os.environ, {'ANTHROPIC_API_KEY': SECRET}):
            result = InternalAdapter(transport=transport, timeout=5).execute('Do it.')
        self.assertEqual(result['outcome'], 'FAILED')
        self.assertNotIn(SECRET, json.dumps(result))
        self.assertIn('[redacted]', result['error'])


class RequestScopeTests(unittest.TestCase):
    def test_the_key_travels_only_in_the_request_header(self):
        captured = {}

        class FakeResponse:
            def read(self, n=-1):
                return json.dumps({'content': [{'type': 'text', 'text': 'ok'}]}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        def fake_urlopen(request, timeout=None):
            captured['url'] = request.full_url
            captured['headers'] = json.dumps(request.header_items())
            captured['data'] = request.data
            return FakeResponse()

        with mock.patch.dict(os.environ, {'ANTHROPIC_API_KEY': SECRET}), \
                mock.patch('urllib.request.urlopen', fake_urlopen):
            body = InternalAdapter()._request({'model': 'm', 'messages': []}, 5)
        self.assertIn(SECRET, captured['headers'])            # the key travels in the header
        self.assertNotIn(SECRET.encode(), captured['data'])   # never in the request body
        self.assertEqual(body.get('content', [{}])[0].get('text'), 'ok')


class ChildEnvironmentTests(unittest.TestCase):
    def test_native_children_receive_no_cross_provider_key(self):
        base = {'ANTHROPIC_API_KEY': 'a-key-value', 'OPENAI_API_KEY': 'o-key-value',
                'DEEPSEEK_API_KEY': 'd-key-value', 'CLAUDECODE': '1'}
        codex = child_env('codex', base)
        claude = child_env('claude', base)
        self.assertNotIn('ANTHROPIC_API_KEY', codex)
        self.assertIn('OPENAI_API_KEY', codex)
        self.assertNotIn('OPENAI_API_KEY', claude)
        self.assertIn('ANTHROPIC_API_KEY', claude)
        self.assertNotIn('CLAUDECODE', codex)
        self.assertNotIn('CLAUDECODE', claude)

    def test_native_children_strip_third_provider_keys(self):
        # AUD-MINOR-003: the child keeps at most its own provider's credential; every other
        # Kel-managed key (third providers included) is removed, not just the counterpart.
        base = {'ANTHROPIC_API_KEY': 'a-key-value', 'OPENAI_API_KEY': 'o-key-value',
                'DEEPSEEK_API_KEY': 'd-key-value', 'CLAUDECODE': '1'}
        codex = child_env('codex', base)
        claude = child_env('claude', base)
        self.assertIn('OPENAI_API_KEY', codex)
        self.assertNotIn('ANTHROPIC_API_KEY', codex)
        self.assertNotIn('DEEPSEEK_API_KEY', codex)
        self.assertIn('ANTHROPIC_API_KEY', claude)
        self.assertNotIn('OPENAI_API_KEY', claude)
        self.assertNotIn('DEEPSEEK_API_KEY', claude)

    def test_unknown_native_provider_strips_every_provider_key(self):
        base = {'ANTHROPIC_API_KEY': 'a', 'OPENAI_API_KEY': 'o', 'DEEPSEEK_API_KEY': 'd'}
        env = child_env('fixture', base)
        for key in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY'):
            self.assertNotIn(key, env)

    def test_a_spawned_native_child_process_sees_only_its_own_key(self):
        # Boundary check: the environment a real child process observes, not just the dict.
        base = dict(os.environ)
        base.update({'ANTHROPIC_API_KEY': 'a-key-value', 'OPENAI_API_KEY': 'o-key-value',
                     'DEEPSEEK_API_KEY': 'd-key-value'})
        probe = ('import json, os; print(json.dumps({k: os.environ.get(k) for k in '
                 '("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY")}))')
        result = subprocess.run([sys.executable, '-c', probe], env=child_env('claude', base),
                                capture_output=True, text=True, timeout=30)
        seen = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(seen, {'ANTHROPIC_API_KEY': 'a-key-value', 'OPENAI_API_KEY': None,
                                'DEEPSEEK_API_KEY': None})

    def test_test_commands_receive_no_provider_keys(self):
        with mock.patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'a-key-value',
                                          'OPENAI_API_KEY': 'o-key-value',
                                          'DEEPSEEK_API_KEY': 'd-key-value'}):
            env = host_test_command_env()
        self.assertNotIn('ANTHROPIC_API_KEY', env)
        self.assertNotIn('OPENAI_API_KEY', env)
        self.assertNotIn('DEEPSEEK_API_KEY', env)
        self.assertEqual(env.get('PYTHONDONTWRITEBYTECODE'), '1')


class DurableLeakTests(unittest.TestCase):
    def test_a_completed_run_never_persists_the_key(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        store = Store(base / 'data')
        payload = {'content': [{'type': 'tool_use', 'id': 't1', 'name': 'submit_result',
                                'input': {'text': '# Result\n' + 'durable work item ' * 6}}],
                   'usage': {'output_tokens': 5}}
        with mock.patch.dict(os.environ, {'ANTHROPIC_API_KEY': SECRET}):
            result = InternalAdapter(transport=lambda body, timeout: payload,
                                     timeout=10).execute('Do it.')
            self.assertEqual(result['outcome'], 'SUCCESS')
            job = store.create({'request': 'Do the work', 'milestones': [
                {'id': 'm1', 'objective': 'Draft the thing', 'filename': 'out.md',
                 'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 4}]}]})
            run = store.claim(job, 'm1', provider='internal')
            store.enqueue_result('r1', run['id'], run['epoch'], result)
            store.consume()
            store.verify(job, 'm1')
            store.assess(job)
        for path in (base / 'data').rglob('*'):
            if path.is_file():
                self.assertNotIn(SECRET.encode(), path.read_bytes(), str(path))


if __name__ == '__main__':
    unittest.main()
