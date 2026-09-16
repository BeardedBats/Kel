import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import subprocess
import sys
import os
import threading
import time
import unittest
from unittest.mock import patch

from kel.acp_host import ACPHost, ServiceClient, run


class ACPHostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.requests = []
        self.send_hook = None
        self.state = {'projects': [{'id': 'saved', 'root': str(self.root), 'test_command': ['pytest']}],
                      'conversations': [{'id': 'c1'}], 'messages': [], 'submissions': [], 'jobs': []}
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.reply(owner.state)
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path == '/api/vetting':
                    # No vetting session exists for this conversation: the ingestion probe answers
                    # 'none' and the prompt proceeds down the normal submission path.
                    self.reply({'kind': 'none'})
                    return
                owner.requests.append((self.path, body))
                if self.path == '/api/send':
                    # Keep one row per submission id; concurrent prompts share the engine.
                    subs = [s for s in owner.state['submissions'] if s['id'] != body['id']]
                    subs.append({'id': body['id'], 'state': 'DISPATCHED', 'job_id': None})
                    owner.state['submissions'] = subs
                    owner.state['messages'].append({'seq': len(owner.state['messages']) + 1, 'role': 'assistant', 'text': 'Real HTTP reply'})
                    if owner.send_hook:
                        owner.send_hook(owner.state)
                self.reply({'id': 'c1'})
            def reply(self, value):
                if self.headers.get('Authorization') != 'Bearer secret':
                    self.send_response(403)
                    self.end_headers()
                    return
                raw = json.dumps(value).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.descriptor = {'url': 'http://127.0.0.1:' + str(self.server.server_port) + '/', 'token': 'secret'}
        (self.root / 'desktop-session.json').write_text(json.dumps(self.descriptor))
        self.events = []
        self.host = ACPHost(ServiceClient(self.root), self.events.append, .01)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def test_new_conversation_does_not_adopt_donor_cwd(self):
        # B6: an ACP session/new cwd (the donor's temp/install working dir) must
        # not silently become an authorized project root. A new conversation
        # defaults to the unrooted project.
        result = self.host.dispatch('session/new', {'cwd': str(self.root)})
        self.assertEqual(result, {'sessionId': 'kel:c1'})
        self.assertEqual(self.requests, [('/api/conversation', {'project': 'default'})])

    def test_prompt_streams_real_http_response_and_stable_submission(self):
        result = self.host.dispatch('session/prompt', {'sessionId': 'kel:c1', 'prompt': [{'type': 'text', 'text': 'hello'}]})
        self.assertEqual(result['stopReason'], 'end_turn')
        self.assertTrue(self.requests[0][1]['id'].startswith('acp-'))
        self.assertIn('Real HTTP reply', self.events[0]['params']['update']['content']['text'])

    def test_auth_error_is_explicit_and_token_not_exposed(self):
        self.descriptor['token'] = 'incorrect'
        (self.root / 'desktop-session.json').write_text(json.dumps(self.descriptor))
        with self.assertRaisesRegex(RuntimeError, 'authentication failed'):
            self.host.dispatch('session/load', {'sessionId': 'kel:c1'})

    def test_image_is_attached_and_audio_is_rejected(self):
        text, attachments = self.host.content('c1', [{'type': 'text', 'text': 'describe'},
                                                  {'type': 'image', 'mimeType': 'image/png', 'data': 'YWJj'}])
        self.assertEqual(text, 'describe')
        self.assertEqual(attachments, ['c1'])
        self.assertEqual(self.requests[0][0], '/api/attach')
        with self.assertRaisesRegex(ValueError, 'Unsupported ACP content'):
            self.host.content('c1', [{'type': 'audio'}])

    def test_load_replays_roles(self):
        self.state['messages'] = [{'seq': 1, 'role': 'user', 'text': 'hello'}, {'seq': 2, 'role': 'assistant', 'text': 'hi'}]
        self.host.dispatch('session/load', {'sessionId': 'kel:c1'})
        self.assertEqual([e['params']['update']['sessionUpdate'] for e in self.events],
                         ['user_message_chunk', 'agent_message_chunk'])

    def test_json_protocol_has_only_json_output(self):
        output = io.StringIO()
        run(self.root, io.StringIO('bad\n' + json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'}) + '\n'), output)
        lines = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(lines[0]['error']['code'], -32700)
        self.assertEqual(lines[1]['result']['agentInfo']['name'], 'kel')

    def test_failed_planning_reports_failure(self):
        def fail(state):
            state['submissions'][0].update(state='FAILED', error='No model connected')
        self.send_hook = fail
        self.host.prompt({'sessionId': 'kel:c1', 'prompt': [{'type': 'text', 'text': 'hello'}]})
        self.assertIn('No model connected', self.events[-1]['params']['update']['content']['text'])

    def test_uncertain_work_is_pending_not_verified(self):
        def uncertain(state):
            state['submissions'][0]['job_id'] = 'j1'
            state['jobs'] = [{'id': 'j1', 'state': 'WAITING_RESOURCE', 'verdict': 'UNCERTAIN'}]
        self.send_hook = uncertain
        result = self.host.prompt({'sessionId': 'kel:c1', 'prompt': [{'type': 'text', 'text': 'hello'}]})
        self.assertEqual(result['stopReason'], 'end_turn')
        self.assertEqual(self.events[-2]['params']['update']['status'], 'pending')
        # B2: the wait is explained in plain language instead of echoing the verdict word.
        text = self.events[-1]['params']['update']['content']['text']
        self.assertIn('waiting for a worker', text)
        self.assertNotIn('VERIFIED', text)

    def test_cancel_controls_job_without_shutting_down_service(self):
        def cancelled(state):
            state['submissions'][0]['job_id'] = 'j1'
            state['jobs'] = [{'id': 'j1', 'state': 'CANCELLED'}]
            self.host.dispatch('session/cancel', {'sessionId': 'kel:c1'})
        self.send_hook = cancelled
        result = self.host.prompt({'sessionId': 'kel:c1', 'prompt': [{'type': 'text', 'text': 'hello'}]})
        self.assertEqual(result['stopReason'], 'cancelled')
        self.assertEqual(self.requests[-1], ('/api/control', {'job': 'j1', 'action': 'cancel'}))
        self.assertFalse(any('shutdown' in path for path, _ in self.requests))

    def test_transport_close_leaves_durable_job_alive(self):
        def disconnect(state):
            state['submissions'][0]['job_id'] = 'j1'
            state['jobs'] = [{'id': 'j1', 'state': 'RUNNING', 'verdict': 'UNCERTAIN'}]
            self.host.closed.set()
        self.send_hook = disconnect
        self.host.prompt({'sessionId': 'kel:c1', 'prompt': [{'type': 'text', 'text': 'hello'}]})
        self.assertEqual([path for path, _ in self.requests], ['/api/send'])
        self.assertEqual(self.state['jobs'][0]['state'], 'RUNNING')

    def test_explicit_local_resource_link_attaches_selected_file(self):
        selected = self.root / 'selected note.txt'
        selected.write_text('User selected content')
        self.host.content('c1', [{'type': 'text', 'text': 'summarize'},
                               {'type': 'resource_link', 'uri': selected.as_uri()}])
        self.assertEqual(self.requests[-1][1]['name'], 'selected note.txt')
        with self.assertRaisesRegex(ValueError, 'remote resource links'):
            self.host.content('c1', [{'type': 'resource_link', 'uri': 'https://example.com/private'}])

    def test_side_question_during_active_prompt_keeps_job_and_resumes_conversation(self):
        sent = {'count': 0}
        def start_job(state):
            sent['count'] += 1
            if sent['count'] == 1:
                state['submissions'][0]['job_id'] = 'j1'
                state['jobs'] = [{'id': 'j1', 'state': 'RUNNING', 'verdict': 'UNCERTAIN'}]
        self.send_hook = start_job
        first = {}
        thread = threading.Thread(target=lambda: first.setdefault(
            'result', self.host.prompt({'sessionId': 'kel:c1', 'prompt': [{'type': 'text', 'text': 'build it'}]})))
        thread.start()
        deadline = time.time() + 5
        while sent['count'] == 0 and time.time() < deadline:
            time.sleep(.01)
        time.sleep(.05)
        second = self.host.prompt({'sessionId': 'kel:c1', 'prompt': [{'type': 'text', 'text': 'what did you find?'}]})
        thread.join(timeout=5)
        self.assertEqual(second['stopReason'], 'end_turn')
        self.assertIn('result', first)
        self.assertEqual(first['result']['stopReason'], 'end_turn')
        # The side question must never cancel or pause the durable job.
        self.assertFalse(any(path == '/api/control' for path, _ in self.requests))
        running = [j for j in self.state['jobs'] if j['id'] == 'j1']
        self.assertTrue(running and running[0]['state'] == 'RUNNING')
        texts = [e['params']['update']['content']['text'] for e in self.events if e.get('params', {}).get('update', {}).get('sessionUpdate') == 'agent_message_chunk']
        self.assertTrue(any('still running in the background' in t for t in texts))

    def test_awaiting_user_emits_permission_guidance_with_action_summary(self):
        def awaiting(state):
            state['submissions'][0]['job_id'] = 'j1'
            state['jobs'] = [{'id': 'j1', 'state': 'AWAITING_USER', 'verdict': 'UNCERTAIN'}]
            state['approvals'] = [{'id': 'a1', 'job_id': 'j1', 'action': json.dumps({'kind': 'command', 'command': 'npm test'})}]
        self.send_hook = awaiting
        result = self.host.prompt({'sessionId': 'kel:c1', 'prompt': [{'type': 'text', 'text': 'fix the build'}]})
        self.assertEqual(result['stopReason'], 'end_turn')
        text = self.events[-1]['params']['update']['content']['text']
        self.assertIn('Kel needs your permission', text)
        self.assertIn('npm test', text)
        self.assertIn('Work context', text)
        update = self.events[-2]['params']['update']
        self.assertEqual(update['status'], 'pending')

    def test_mapped_donor_conversation_reuses_existing_id_and_history(self):
        self.state['conversations'][0]['project_id'] = 'saved'
        self.state['messages'] = [{'seq': 1, 'role': 'user', 'text': 'existing question'}]
        (self.root / 'aion-conversations.json').write_text(json.dumps({'donor1': 'c1'}))
        with patch.dict('os.environ', {'AIONUI_CONVERSATION_ID': 'donor1'}):
            result = self.host.dispatch('session/new', {'cwd': str(self.root)})
        self.assertEqual(result['sessionId'], 'kel:c1')
        self.assertEqual(self.requests, [])
        self.assertEqual(self.events[0]['params']['update']['content']['text'], 'existing question')

    def test_new_session_persists_independent_donor_mapping(self):
        self.state['conversations'][0]['project_id'] = 'saved'
        with patch.dict('os.environ', {'AIONUI_CONVERSATION_ID': 'donor-new'}):
            self.host.dispatch('session/new', {'cwd': str(self.root)})
            files = list((self.root / 'aion-session-map').glob('*.json'))
            self.assertEqual(len(files), 1)
            self.assertEqual(json.loads(files[0].read_text()), {'donor-new': 'c1'})
            self.host.dispatch('session/new', {'cwd': str(self.root)})
        self.assertEqual([path for path, _ in self.requests], ['/api/conversation'])

    def test_cli_uses_utf8_even_with_windows_legacy_encoding(self):
        self.state['messages'] = [{'seq': 1, 'role': 'assistant', 'text': 'Saved — café 日本語'}]
        request = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'session/load',
                              'params': {'sessionId': 'kel:c1'}}).encode() + b'\n'
        script = Path(__file__).parents[1] / 'kel' / 'acp_host.py'
        process = subprocess.run([sys.executable, str(script), '--data', str(self.root)], input=request,
                                 capture_output=True, timeout=15,
                                 env={**os.environ, 'PYTHONIOENCODING': 'cp1252'})
        self.assertEqual(process.returncode, 0, process.stderr.decode('utf-8'))
        events = [json.loads(line) for line in process.stdout.decode('utf-8').splitlines()]
        self.assertEqual(events[0]['params']['update']['content']['text'], 'Saved — café 日本語')


if __name__ == '__main__':
    unittest.main()
