"""FN-04: files attached in the composer reach Kel.

The desktop shell sends attached files as a trailing ``[[AION_FILES]]`` block of local paths. The
ACP host copies each one into Kel's own attachment store (per conversation, under Kel's data, so a
backup that says it includes attachments does) and strips the block from the request. The turn
model, a direct reply and a hand-off's packet all see the file. No real model is called here.
"""
import contextlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from urllib.parse import parse_qs, urlparse

from kel.acp_host import ACPHost, split_file_marker
from kel.service import Service


class FakeTurn:
    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def execute(self, prompt, system=None, images=None, **kwargs):
        self.calls.append(prompt)
        return {'outcome': 'SUCCESS', 'text': json.dumps(self.answer(prompt))}


class LocalClient:
    """The ACP host's service client, calling the real engine in-process."""

    def __init__(self, service):
        self.service = service
        self.data = Path(service.store.root)

    def call(self, route, payload=None):
        if payload is None:
            query = parse_qs(urlparse(route).query)
            return self.service.state(query.get('conversation', ['main'])[0])
        if route in ('/api/vetting', '/api/capabilities'):
            return {'kind': 'none'}
        return self.service.action(route, payload)

    def state(self, conversation='main'):
        return self.service.state(conversation)


class MarkerParsingTests(unittest.TestCase):
    def test_the_block_is_split_from_the_text(self):
        text, paths = split_file_marker('What is the code word?\n\n[[AION_FILES]]\nC:\\tmp\\note.txt\n/home/n/a.md')
        self.assertEqual(text, 'What is the code word?')
        self.assertEqual(paths, ['C:\\tmp\\note.txt', '/home/n/a.md'])

    def test_a_message_that_only_mentions_the_marker_is_untouched(self):
        for text in ('The [[AION_FILES]] marker is odd', 'x\n[[AION_FILES]]\nnot a path at all',
                     'x\n[[AION_FILES]]\nhttps://example.com/a.txt', 'x\n[[AION_FILES]]\n\\\\server\\share\\a.txt'):
            self.assertEqual(split_file_marker(text), (text, []))

    def test_the_block_stops_at_the_next_marker(self):
        text, paths = split_file_marker('Hi\n[[AION_FILES]]\n/a/b.txt\n[[AION_SESSIONS]]\nsession-1')
        self.assertEqual(paths, ['/a/b.txt'])
        self.assertEqual(text, 'Hi\n[[AION_SESSIONS]]\nsession-1')


class AttachmentsReachKelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        for name in ('ANTHROPIC_API_KEY', 'KEL_INTERNAL_MODEL'):
            os.environ.pop(name, None)
        os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none')
        self.service = Service(str(Path(self.tmp.name) / 'engine'))
        self.turn = FakeTurn(lambda prompt: (
            {'action': 'reply', 'text': 'The code word is ' + ('PERIWINKLE' if 'PERIWINKLE' in prompt else 'unknown') + '.'}
            if 'code word' in prompt.split('latest message:')[-1] else
            {'action': 'start_background_work', 'title': 'Summary of the note',
             'acknowledgement': "I'm on it and will post it here once it's been checked.", 'related_topic': None}))
        self.service.turn_mode = ''
        self.service.model = self.turn
        self.service.engine.adapters = {}
        self.service.stop.set()
        self.cid = self.service.context.conversation('default')
        self.events = []
        self.host = ACPHost(LocalClient(self.service), self.events.append, .02)
        # The shell's upload staging copy (outside Kel's data).
        self.upload = Path(self.tmp.name) / 'staging' / 'audit-note.txt'
        self.upload.parent.mkdir()
        self.upload.write_text('Notes for Kel.\nThe code word at the end is PERIWINKLE.\n', encoding='utf-8')

    def tearDown(self):
        with contextlib.suppress(Exception):
            self.service.shutdown()
        self.tmp.cleanup()

    def prompt(self, text):
        return self.host.prompt({'sessionId': 'kel:' + self.cid, 'prompt': [
            {'type': 'text', 'text': text + '\n\n[[AION_FILES]]\n' + str(self.upload)}]})

    def packet_of_last_submission(self):
        with contextlib.closing(self.service.store.connect()) as db:
            row = db.execute('SELECT p.packet FROM submissions s JOIN submission_packets p ON p.id=s.id '
                             'WHERE s.conversation_id=? ORDER BY s.created DESC LIMIT 1', (self.cid,)).fetchone()
        return json.loads(row['packet'])

    def test_kel_quotes_the_attached_file_and_keeps_it_in_its_own_data(self):
        self.assertEqual(self.prompt('Which code word appears at the end of the attached file?'),
                         {'stopReason': 'end_turn'})
        said = ''.join(e['params']['update']['content']['text'] for e in self.events
                       if e['params']['update'].get('sessionUpdate') == 'agent_message_chunk')
        self.assertIn('PERIWINKLE', said)
        self.assertIn('PERIWINKLE', self.turn.calls[-1])            # the turn model read the file
        packet = self.packet_of_last_submission()
        self.assertEqual([f['name'] for f in packet['files']], ['audit-note.txt'])
        self.assertIn('PERIWINKLE', packet['files'][0]['text'])
        # The request Kel stores is the person's words, not the shell's marker block.
        messages = self.service.state(self.cid)['messages']
        self.assertEqual(messages[0]['text'], 'Which code word appears at the end of the attached file?')
        # The copy lives in this conversation's folder under Kel's data, not in the staging folder.
        with contextlib.closing(self.service.store.connect()) as db:
            stored = db.execute('SELECT path FROM attachments WHERE conversation_id=?', (self.cid,)).fetchone()['path']
        copy = Path(self.service.store.root) / stored
        self.assertEqual(copy.parent.name, self.cid)
        self.assertTrue(copy.resolve().is_relative_to(Path(self.service.store.root).resolve()))
        self.assertEqual(copy.read_bytes(), self.upload.read_bytes())

    def test_a_handoff_packet_carries_the_file_to_the_work(self):
        gate = []
        original = self.service._compile_work

        def record(sid, cid, text, packet, kind, greenfield):
            gate.append(packet)
            return original(sid, cid, text, packet, kind, greenfield)
        self.service._compile_work = record
        self.prompt('Write a short summary document of the attached note')
        deadline = time.time() + 20
        while not gate and time.time() < deadline:
            time.sleep(.02)
        self.assertTrue(gate, 'the hand-off never started planning')
        self.assertIn('PERIWINKLE', gate[0]['files'][0]['text'])
        cards = [e for e in self.events if e['params']['update'].get('toolCallId', '').startswith('kel-work:')]
        self.assertTrue(cards)

    def test_a_missing_upload_is_said_plainly(self):
        self.upload.unlink()
        with self.assertRaisesRegex(ValueError, "couldn't find the attached file audit-note.txt"):
            self.prompt('Which code word?')


if __name__ == '__main__':
    unittest.main()
