"""Transcription engine tests (docs/transcription/08_TEST_MATRIX.md).

Provider-independent: everything runs against the deterministic fixture provider, so the
credential-free path is fully verifiable. The architecture contract test proves that a transcript
fed through the composer/vetting route and the same transcript fed directly into the existing
VettingAnswerIngestion pipeline produce equivalent Vetting state.
"""
import base64
import io
import sys
import tempfile
import unittest
import wave
from pathlib import Path

from kel.core import PolicyError, Store
from kel.transcription import Transcription, contextual_title, think_out_loud_buckets
from kel.service import Service
from kel.vetting_session import Vetting, snapshot


def wav_bytes(seconds=2.0, rate=24000, fill=b'\x00\x00'):
    buffer = io.BytesIO()
    handle = wave.open(buffer, 'wb')
    handle.setnchannels(1)
    handle.setsampwidth(2)
    handle.setframerate(rate)
    handle.writeframes(fill * int(rate * seconds))
    handle.close()
    return buffer.getvalue()


def b64(data):
    return base64.b64encode(data).decode('ascii')


class TranscriptionBase(unittest.TestCase):
    def setUp(self):
        sys.stdout.reconfigure(errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        self.t = Transcription(self.store)

    def tearDown(self):
        self.tmp.cleanup()


class RecordingAndLibraryTests(TranscriptionBase):
    def test_record_save_gives_title_audio_and_duration(self):
        row = self.t.save_recording('uh, so the matchup table should win by default', 2400, b64(wav_bytes(2.4)))
        self.assertEqual(row['status'], 'complete')
        self.assertEqual(row['source_type'], 'recording')
        self.assertTrue(row['has_audio'])
        self.assertEqual(row['duration_ms'], 2400)
        self.assertIn('Matchup', row['name'])

    def test_empty_recording_is_refused_with_plain_copy(self):
        with self.assertRaises(PolicyError) as raised:
            self.t.save_recording('text only', 0, '')
        self.assertIn('no audio', str(raised.exception))

    def test_library_survives_restart_and_audio_stays(self):
        row = self.t.save_recording('keep me around', 1000, b64(wav_bytes(1.0)))
        fresh = Transcription(self.store)
        library = fresh.library()
        self.assertEqual(len(library['transcripts']), 1)
        self.assertEqual(library['transcripts'][0]['id'], row['id'])
        self.assertTrue(library['transcripts'][0]['has_audio'])
        audio = fresh.export_audio(row['id'])
        self.assertEqual(audio['mime'], 'audio/wav')
        self.assertGreater(len(audio['data']), 100)

    def test_rename_delete_folder_and_move_back(self):
        row = self.t.save_recording('folder candidate', 800, b64(wav_bytes(0.8)))
        folder = self.t.folder_create('Interviews')
        moved = self.t.assign(row['id'], folder['id'])
        self.assertEqual(moved['folder_id'], folder['id'])
        back = self.t.assign(row['id'], None)
        self.assertIsNone(back['folder_id'])
        renamed = self.t.transcript_rename(row['id'], 'Renamed note')
        self.assertEqual(renamed['name'], 'Renamed note')
        self.t.assign(row['id'], folder['id'])
        self.t.folder_delete(folder['id'])
        self.assertEqual(self.t.library()['transcripts'][0]['folder_id'], None)
        self.t.transcript_delete(row['id'])
        self.assertEqual(self.t.library()['transcripts'], [])

    def test_append_recording_extends_text_duration_and_audio(self):
        first = self.t.save_recording('first part', 1000, b64(wav_bytes(1.0)))
        second = self.t.save_recording('second part', 1000, b64(wav_bytes(1.0)), append_to=first['id'])
        self.assertIn('first part', second['text'])
        self.assertIn('second part', second['text'])
        self.assertEqual(second['duration_ms'], 2000)
        self.assertEqual(len(self.t.library()['transcripts']), 1)

    def test_combine_appends_and_removes_source(self):
        target = self.t.save_recording('opening remarks', 1000, b64(wav_bytes(1.0)))
        source = self.t.save_recording('closing remarks', 1500, b64(wav_bytes(1.5)))
        combined = self.t.combine(target['id'], source['id'])
        self.assertIn('closing remarks', combined['text'])
        self.assertEqual(combined['duration_ms'], 2500)
        self.assertEqual(len(self.t.library()['transcripts']), 1)
        with self.assertRaises(PolicyError):
            self.t.transcript(source['id'])


class UploadTests(TranscriptionBase):
    def test_upload_is_deterministic_and_saved(self):
        audio = b64(wav_bytes(2.0))
        first = self.t.transcribe_upload('meeting-notes.wav', audio)
        self.assertEqual(first['status'], 'complete')
        self.assertTrue(first['has_audio'])
        self.assertGreater(len(first['text']), 20)
        again = self.t.quick_transcribe('meeting-notes.wav', audio)
        self.assertEqual(again['text'], first['text'])

    def test_upload_rejects_unreadable_audio_with_plain_copy(self):
        with self.assertRaises(PolicyError) as raised:
            self.t.transcribe_upload('notes.wav', b64(b'nope'))
        self.assertIn('could not be read', str(raised.exception))

    def test_upload_rejects_unsupported_extension(self):
        with self.assertRaises(PolicyError) as raised:
            self.t.transcribe_upload('notes.xyz', b64(wav_bytes(1.0)))
        self.assertIn('MP3, MP4, or WAV', str(raised.exception))

    def test_upload_rejects_long_audio(self):
        with self.assertRaises(PolicyError) as raised:
            self.t.transcribe_upload('long.wav', b64(wav_bytes(601.0)))
        self.assertIn('10 minutes', str(raised.exception))

    def test_quick_transcribe_keeps_nothing_in_the_library(self):
        result = self.t.quick_transcribe('draft.wav', b64(wav_bytes(1.0)))
        self.assertGreater(len(result['text']), 10)
        self.assertEqual(self.t.library()['transcripts'], [])
        self.assertEqual(result['mode'], 'fixture')

    def test_export_text_returns_txt_named_payload(self):
        row = self.t.save_recording('exportable words', 500, b64(wav_bytes(0.5)))
        export = self.t.export_text(row['id'])
        self.assertTrue(export['name'].endswith('.txt'))
        self.assertIn('exportable words', export['text'])


class StreamTests(TranscriptionBase):
    def test_stream_lifecycle_produces_text_and_duration(self):
        start = self.t.stream_start('main')
        self.assertTrue(start['live'])
        text = ''
        for _ in range(60):
            current = self.t.stream_chunk(start['session_id'], b64(b'\x00\x00' * 4096))
            text = current['text']
        self.assertGreater(len(text), 10)
        final = self.t.stream_finish(start['session_id'])
        self.assertGreaterEqual(len(final['text']), len(text))
        self.assertGreater(final['duration_ms'], 8000)
        with self.assertRaises(PolicyError):
            self.t.stream_status(start['session_id'])

    def test_stream_unknown_session_has_plain_error(self):
        with self.assertRaises(PolicyError) as raised:
            self.t.stream_chunk('ts-missing', b64(b'\x00\x00'))
        self.assertIn('ended', str(raised.exception))


class ProviderModeTests(TranscriptionBase):
    def test_mode_is_fixture_without_a_key_and_switches_when_set(self):
        status = self.t.status()
        self.assertEqual(status['mode'], 'fixture')
        self.assertFalse(status['has_key'])
        self.assertIn('Practice', status['label'])
        self.t.set_key('test-key-not-used')
        switched = self.t.status()
        self.assertEqual(switched['mode'], 'muse')
        self.assertTrue(switched['has_key'])
        self.t.clear_key()
        self.assertEqual(self.t.status()['mode'], 'fixture')

    def test_title_and_buckets_helpers(self):
        # Donor-faithful: only leading filler words are stripped, then title-casing is applied.
        self.assertEqual(contextual_title('uh, so I think the matchup table should win.'),
                         'Think the Matchup Table Should Win')
        self.assertEqual(contextual_title('hey, can you record a note about the dashboard layout'),
                         'Can You Record a Note About the Dashboard Layout')
        buckets = think_out_loud_buckets(
            'We must keep the rows compact. I am worried about the noisy banners. '
            'Not sure about the accent color yet.')
        self.assertTrue(buckets['requirements'])
        self.assertTrue(buckets['concerns'])
        self.assertTrue(buckets['unresolved'])


class TranscriptVettingTests(unittest.TestCase):
    """The architectural contract: any input method reaches the SAME ingestion service."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        self.vetting = Vetting(self.store)
        self.sid = self.vetting.start('default', 'main', 'Voice dashboard')['session_id']

    def tearDown(self):
        self.tmp.cleanup()

    def test_preview_writes_nothing_and_lists_answers(self):
        before = snapshot(self.store, self.sid)
        text = '1: C, and 2 none of these, keep it small'
        payload = self.vetting.preview_transcript('main', text)
        self.assertTrue(payload['preview'])
        ids = [item['question_id'] for item in payload['preview']]
        self.assertIn('Q1', ids)
        self.assertEqual(snapshot(self.store, self.sid), before)

    def test_transcript_route_matches_direct_ingestion(self):
        text = '1: C\n2: A\n3: B'
        # Path A: the route every transcript surface calls (preview then apply).
        payload = self.vetting.preview_transcript('main', text)
        self.assertTrue(payload['preview'])
        self.vetting.apply_transcript('main', text)
        snap_a = snapshot(self.store, self.sid)
        # Path B: direct ingestion of the same transcript with the same recorded source.
        store_b = Store(Path(self.tmp.name) / 'b.sqlite3')
        vetting_b = Vetting(store_b)
        sid_b = vetting_b.start('default', 'main', 'Voice dashboard')['session_id']
        vetting_b.ingest(sid_b, text, 'transcript')
        snap_b = snapshot(store_b, sid_b)
        self.assertEqual(snap_a, snap_b)
        self.assertEqual(snap_a['answers']['Q1']['selected'], ['C'])
        self.assertEqual([r[3] for r in snap_a['revisions']], [])

    def test_low_confidence_transcript_is_proposed_not_applied(self):
        text = 'the sidebar keeps me oriented'
        payload = self.vetting.preview_transcript('main', text)
        self.assertTrue(payload['proposals'])
        proposal = payload['proposals'][0]
        self.assertEqual(proposal['question_id'], 'Q6')
        self.vetting.apply_transcript('main', text)
        state = snapshot(self.store, self.sid)
        self.assertIsNone(state['answers'].get('Q6'))
        self.vetting.apply_transcript('main', text, accept_all=True)
        state = snapshot(self.store, self.sid)
        self.assertEqual(state['answers']['Q6']['selected'], [proposal['option']])

    def test_freethink_buckets_and_conflict_preview(self):
        self.vetting.ingest(self.sid, '7: A', 'chat')
        self.vetting.process(self.sid)  # batch 2 carries Q19, the opposite pole of Q7
        payload = self.vetting.preview_transcript(
            'main', 'We must keep rows compact. I am worried about noise. Not sure about colors yet.',
            mode='freethink')
        buckets = payload['buckets']
        self.assertTrue(buckets['requirements'] and buckets['concerns'] and buckets['unresolved'])
        conflict = self.vetting.preview_transcript('main', '19: B')
        self.assertTrue(conflict['potential_conflicts'])
        self.assertIn('leans', conflict['potential_conflicts'][0]['statement'])
        # Preview never changed the recorded answers.
        self.assertEqual(snapshot(self.store, self.sid)['answers']['Q7']['selected'], ['A'])

    def test_no_session_anywhere_is_a_plain_error(self):
        other = Store(Path(self.tmp.name) / 'empty.sqlite3')
        with self.assertRaises(PolicyError):
            Vetting(other).preview_transcript('', '1: C')

    def test_transcript_without_a_conversation_uses_the_latest_active_session(self):
        payload = self.vetting.preview_transcript('', '1: C')
        self.assertEqual(payload['session_id'], self.sid)


class TranscriptionServiceRouteTests(unittest.TestCase):
    """The action family the renderer calls; same object graph as production."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = Service(self.tmp.name)
        self.conversation = self.service.action('/api/conversation', {'project': 'default'})['id']
        self.audio = b64(wav_bytes(2.5))

    def tearDown(self):
        self.service.shutdown()
        self.tmp.cleanup()

    def test_status_quick_transcribe_and_stream_routes(self):
        status = self.service.action('/api/transcription', {'action': 'status'})
        self.assertEqual(status['mode'], 'fixture')
        quick = self.service.action('/api/transcription', {
            'action': 'quick_transcribe', 'filename': 'draft.wav', 'audio': self.audio})
        self.assertTrue(quick['text'])
        self.assertEqual(quick['duration_ms'], 2500)
        started = self.service.action('/api/transcription', {'action': 'stream_start', 'conversation': self.conversation})
        self.assertTrue(started['live'])
        chunk = base64.b64encode(b'\x00\x00' * 4096).decode()
        seen = ''
        for _ in range(40):
            state = self.service.action('/api/transcription', {
                'action': 'stream_chunk', 'session': started['session_id'], 'pcm': chunk})
            seen = state['text'] or seen
        finished = self.service.action('/api/transcription', {
            'action': 'stream_finish', 'session': started['session_id']})
        self.assertTrue(finished['text'])
        self.assertGreater(finished['duration_ms'], 3000)

    def test_library_actions_roundtrip(self):
        saved = self.service.action('/api/transcription', {
            'action': 'save_recording', 'text': 'notes about the layout', 'duration_ms': 2500,
            'audio': self.audio})
        folder = self.service.action('/api/transcription', {'action': 'folder_create', 'name': 'Interviews'})
        moved = self.service.action('/api/transcription', {
            'action': 'assign', 'id': saved['id'], 'folder': folder['id']})
        self.assertEqual(moved['folder_id'], folder['id'])
        renamed = self.service.action('/api/transcription', {
            'action': 'rename', 'id': saved['id'], 'name': 'Layout notes'})
        self.assertEqual(renamed['name'], 'Layout notes')
        exported = self.service.action('/api/transcription', {'action': 'export_text', 'id': saved['id']})
        self.assertIn('Layout', exported['name'])
        audio = self.service.action('/api/transcription', {'action': 'export_audio', 'id': saved['id']})
        self.assertEqual(audio['mime'], 'audio/wav')
        library = self.service.action('/api/transcription', {'action': 'library'})
        self.assertEqual(len(library['transcripts']), 1)
        deleted = self.service.action('/api/transcription', {'action': 'delete', 'id': saved['id']})
        self.assertTrue(deleted['deleted'])

    def test_vetting_transcript_routes(self):
        self.service.action('/api/vetting', {'action': 'start', 'conversation': self.conversation,
                                             'topic': 'Voice routing'})
        text = '1: C\n2: A'
        preview = self.service.action('/api/vetting', {'action': 'transcript_preview',
                                                       'conversation': self.conversation, 'text': text})
        self.assertEqual(len(preview['preview']), 2)
        applied = self.service.action('/api/vetting', {'action': 'transcript_apply',
                                                       'conversation': self.conversation, 'text': text})
        self.assertEqual(sorted(applied['applied']['applied']), ['Q1', 'Q2'])
        panel = self.service.action('/api/vetting', {'action': 'panel', 'conversation': self.conversation})
        self.assertEqual(panel['session']['topic'], 'Voice routing')

    def test_unknown_action_is_a_plain_error(self):
        with self.assertRaises(PolicyError):
            self.service.action('/api/transcription', {'action': 'nonsense'})
