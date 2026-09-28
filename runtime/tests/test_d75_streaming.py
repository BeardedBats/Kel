"""D-75.1: Kel's direct replies stream word by word where the runtime can stream.

The turn model's JSON answer is read as it arrives and only a reply's text is shown (never an
acknowledgement or hand-off); Claude Code streams through stream-json, OpenAI-compatible APIs
through server-sent events, and Codex exec (whole messages only) falls back to a whole reply. The
ACP host shows new words while the reply is written and never repeats them when it is posted.
No real model is called here.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse

from kel.acp_host import ACPHost
from kel.api_models import OpenAICompatAdapter
from kel.native import NativeAdapter
from kel.service import Service
from kel.turn import NO_CHANGE, ReplyStream, reply_so_far


class ReplySoFarTests(unittest.TestCase):
    def test_a_reply_streams_once_it_says_it_is_a_reply(self):
        self.assertIsNone(reply_so_far('{"act'))
        self.assertIsNone(reply_so_far('{"action":"reply"'))
        self.assertEqual(reply_so_far('{"action":"reply","text":"Tomatoes like'), 'Tomatoes like')
        self.assertEqual(reply_so_far('```json\n{"action": "reply", "text": "Line one\\nLine \\"two\\"'),
                         'Line one\nLine "two"')
        # An escape that has not fully arrived is held back.
        self.assertEqual(reply_so_far('{"action":"reply","text":"caf\\u00'), 'caf')
        self.assertEqual(reply_so_far('{"action":"reply","text":"done."}'), 'done.')

    def test_work_and_amendments_never_stream(self):
        self.assertIsNone(reply_so_far('{"action":"start_background_work","title":"Plan","acknowledgement":"On it'))
        self.assertIsNone(reply_so_far('{"action":"amend_background_work","text":"x'))

    def test_prose_streams_until_json_appears(self):
        self.assertEqual(reply_so_far('Sure, happy to'), 'Sure, happy to')
        self.assertIsNone(reply_so_far('Sure {"action":"start_background_work"'))
        self.assertEqual(reply_so_far('Answer as prose {x}', prose=True), 'Answer as prose {x}')

    def test_the_stream_stops_at_a_change_claim(self):
        shown = []
        stream = ReplyStream(shown.append)
        for raw in ('{"action":"reply","text":"Sure', '{"action":"reply","text":"Sure — I\'ve added',
                    '{"action":"reply","text":"Sure — I\'ve added that to the plan."}'):
            stream(raw)
        self.assertEqual(shown, ['Sure'])
        self.assertTrue(stream.stopped)


class ClaudeStreamJsonTests(unittest.TestCase):
    def test_words_are_read_from_stream_json_and_the_result_record_still_parses(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = NativeAdapter('claude', Path(tmp) / 'ws', Path(tmp) / 'logs')
            self.assertIn('stream-json', adapter.argv(stream=True))
            self.assertIn('--include-partial-messages', adapter.argv(stream=True))
            # Every Claude call uses stream-json (the only format with rate_limit_event, kel.quota);
            # only a streamed reply asks for the partial words.
            self.assertIn('stream-json', adapter.argv())
            self.assertNotIn('--include-partial-messages', adapter.argv())
            path = Path(tmp) / 'out.stdout'
            delta = lambda text: json.dumps({'type': 'stream_event', 'event': {
                'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': text}}})
            result = json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False,
                                 'result': 'Hello there.', 'session_id': 's1', 'usage': {'output_tokens': 3}})
            path.write_text(json.dumps({'type': 'system', 'subtype': 'init'}) + '\n' + delta('Hel'), encoding='utf-8')
            seen, streamed = [], {'offset': 0, 'text': '', 'rest': b''}
            adapter._stream_words(path, streamed, seen.append)
            self.assertEqual(seen, [])  # the delta line is not complete yet
            with path.open('a', encoding='utf-8') as handle:
                handle.write('\n' + delta('lo there.') + '\n' + result + '\n')
            adapter._stream_words(path, streamed, seen.append)
            self.assertEqual(seen, ['Hello there.'])
            parsed = adapter.parse(path.read_text(encoding='utf-8'))
            self.assertEqual((parsed['outcome'], parsed['text'], parsed['session_id']), ('SUCCESS', 'Hello there.', 's1'))

    def test_codex_never_asks_for_a_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = NativeAdapter('codex', Path(tmp) / 'ws', Path(tmp) / 'logs')
            self.assertEqual(adapter.argv(stream=True), adapter.argv())


class ServerSentEventsTests(unittest.TestCase):
    def test_a_streamed_completion_calls_back_with_the_answer_so_far(self):
        lines = [b'data: ' + json.dumps({'model': 'deepseek-flash', 'choices': [{'delta': {'content': piece}}]}).encode() + b'\n'
                 for piece in ('Six ', 'to eight ', 'hours.')]
        lines += [b'data: ' + json.dumps({'choices': [], 'usage': {'total_tokens': 9}}).encode() + b'\n', b'data: [DONE]\n']

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False
        seen = []
        with mock.patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'k'}), \
                mock.patch('urllib.request.urlopen', return_value=Response(b''.join(lines))) as opened:
            result = OpenAICompatAdapter('deepseek').execute('How much sun?', on_text=seen.append)
        body = json.loads(opened.call_args[0][0].data)
        self.assertTrue(body['stream'])
        self.assertEqual(seen, ['Six ', 'Six to eight ', 'Six to eight hours.'])
        self.assertEqual((result['outcome'], result['text'], result['usage']), ('SUCCESS', 'Six to eight hours.', {'total_tokens': 9}))

    def test_a_test_transport_without_streaming_answers_whole(self):
        adapter = OpenAICompatAdapter('deepseek', transport=lambda body, timeout: {
            'choices': [{'message': {'content': 'Whole.'}}]})
        seen = []
        self.assertEqual(adapter.execute('q', on_text=seen.append)['text'], 'Whole.')
        self.assertEqual(seen, [])


class StreamingTurn:
    """A turn model that writes its JSON answer in pieces, pausing between them."""

    def __init__(self, answer, pause=.25):
        self.answer, self.pause = answer, pause
        self.release = threading.Event()

    def execute(self, prompt, system=None, images=None, cancel=None, on_text=None):
        raw = json.dumps(self.answer)
        if on_text is not None:
            for end in range(12, len(raw), 9):
                on_text(raw[:end])
                time.sleep(self.pause / 10)
        return {'outcome': 'SUCCESS', 'text': raw}


class LocalClient:
    def __init__(self, service):
        self.service = service
        self.data = Path(service.store.root)
        self.drafts = []

    def call(self, route, payload=None):
        parsed = urlparse(route)
        query = parse_qs(parsed.query)
        if payload is None and parsed.path == '/api/draft':
            out = self.service.draft(query['id'][0])
            self.drafts.append(out['text'])
            return out
        if payload is None:
            return self.service.state(query.get('conversation', ['main'])[0])
        if route in ('/api/vetting', '/api/capabilities'):
            return {'kind': 'none'}
        return self.service.action(route, payload)

    def state(self, conversation='main'):
        return self.service.state(conversation)


class StreamedChatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        for name in ('ANTHROPIC_API_KEY', 'KEL_INTERNAL_MODEL'):
            os.environ.pop(name, None)
        os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none')
        self.service = Service(str(Path(self.tmp.name) / 'engine'))
        self.service.turn_mode = ''
        self.service.engine.adapters = {}
        self.service.stop.set()
        self.cid = self.service.context.conversation('default')
        self.events = []
        self.client = LocalClient(self.service)
        self.host = ACPHost(self.client, self.events.append, .05)

    def tearDown(self):
        with contextlib.suppress(Exception):
            self.service.shutdown()
        self.tmp.cleanup()

    def chunks(self):
        return [e['params']['update']['content']['text'] for e in self.events
                if e['params']['update'].get('sessionUpdate') == 'agent_message_chunk']

    def send(self, text):
        return self.host.prompt({'sessionId': 'kel:' + self.cid, 'prompt': [{'type': 'text', 'text': text}]})

    def test_a_reply_arrives_in_pieces_and_is_never_repeated(self):
        reply = 'Tomatoes want six to eight hours of direct sun a day, more in cooler places.'
        self.service.model = StreamingTurn({'action': 'reply', 'text': reply})
        self.send('How much sun do tomatoes need?')
        chunks = self.chunks()
        self.assertGreater(len(chunks), 2, chunks)          # several pieces, not one whole reply
        self.assertEqual(''.join(chunks), reply + '\n\n')     # and nothing said twice
        self.assertTrue(any(0 < len(d) < len(reply) for d in self.client.drafts))
        self.assertEqual(self.service.state(self.cid)['messages'][-1]['text'], reply)
        self.assertEqual(self.service.drafts, {})

    def test_a_handoff_acknowledgement_is_not_streamed(self):
        self.service.model = StreamingTurn({'action': 'start_background_work', 'title': 'Garden plan',
                                            'acknowledgement': "I'm starting on that now in the background; "
                                                               "I'll post it here once it's been checked.",
                                            'related_topic': None})
        gate = threading.Event()
        self.service._compile_work = lambda *args, **kwargs: gate.wait(5) or {}
        self.addCleanup(gate.set)
        self.send('Write me a spring garden plan')
        chunks = self.chunks()
        self.assertEqual(len(chunks), 1, chunks)
        self.assertIn('starting on that now', chunks[0])
        self.assertTrue(all(d == '' for d in self.client.drafts))

    def test_a_reply_the_guard_replaces_shows_the_real_reply_after_what_was_shown(self):
        self.service.model = StreamingTurn({'action': 'reply', 'text': "Sure thing — I've added that to the plan."})
        self.send('Also add basil')
        said = ''.join(self.chunks())
        self.assertTrue(said.startswith('Sure thing'))
        self.assertTrue(said.rstrip().endswith(NO_CHANGE))
        self.assertNotIn("I've added", said)

    def test_a_runtime_that_cannot_stream_still_answers_whole(self):
        class Whole:
            def execute(self, prompt, system=None, images=None, cancel=None):
                return {'outcome': 'SUCCESS', 'text': json.dumps({'action': 'reply', 'text': 'Whole answer.'})}
        self.service.model = Whole()
        self.send('Hello?')
        self.assertEqual(self.chunks(), ['Whole answer.\n\n'])


if __name__ == '__main__':
    unittest.main()
