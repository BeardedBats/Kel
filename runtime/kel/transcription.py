"""Transcription: Kel's first-class audio input source (V1.5.1, migration v12).

Ported from the donor desktop app (`Transcriptions-Source.zip`): the Muse provider protocol
(realtime websocket + multipart file transcription), the library model (folders + transcripts
with the donor's status/source semantics), the contextual-title algorithm, and the append /
combine / export behaviours. Deliberate replacements are documented in docs/transcription/:

- Tauri/Rust IPC and Windows Credential Manager custody become the engine HTTP action family
  `/api/transcription` with engine-side key resolution (env `META_API_KEY` or a stored key,
  presence-only, mirroring `kel/providers.py`).
- The FFmpeg sidecar becomes renderer-side WebAudio decoding to 24 kHz mono PCM16 WAV; the
  engine validates/converts timelines with the stdlib `wave` module and can concatenate WAVs
  losslessly (append recording / combine transcripts) without any external binary.
- The donor's spacebar recording shortcut is intentionally NOT ported (program hard rule).

Transcription is an input source, never a conversational system: it produces text, and the
existing VettingAnswerIngestion pipeline understands that text (typed, pasted, or spoken).
"""
import base64
import contextlib
import hashlib
import io
import json
import os
import queue
import re
import threading
import time
import uuid
import wave

from .core import PolicyError, uid

# Live stream sessions are process-wide: the service builds a fresh Transcription per
# action, so the registry must not live on the instance.
_STREAMS = {}

MIGRATION_VERSION = 12
MIGRATION_NAME = 'v15-transcription'

STATUSES = ('processing', 'recording', 'complete', 'failed', 'cancelled')
SOURCE_TYPES = ('recording', 'upload')

DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations(
    version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS transcription_folders(
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS transcripts(
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    text TEXT NOT NULL DEFAULT '',
    created REAL NOT NULL,
    updated REAL NOT NULL,
    folder_id TEXT REFERENCES transcription_folders(id) ON DELETE SET NULL,
    audio_path TEXT,
    audio_ext TEXT,
    source_type TEXT NOT NULL DEFAULT 'recording',
    source_filename TEXT,
    duration_ms INTEGER,
    status TEXT NOT NULL DEFAULT 'complete',
    error TEXT);
CREATE INDEX IF NOT EXISTS transcripts_by_created ON transcripts(created DESC);
CREATE INDEX IF NOT EXISTS transcripts_by_folder ON transcripts(folder_id);
CREATE TABLE IF NOT EXISTS transcription_settings(
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL);
"""

TARGET_RATE = 24000
MAX_UPLOAD_BYTES = 32 * 1024 * 1024          # Muse's documented limit
MAX_DURATION_MS = 10 * 60 * 1000             # Muse accepts up to 10 minutes
ACCEPTED_EXTENSIONS = ('mp3', 'mp4', 'wav', 'm4a', 'aac', 'ogg', 'flac', 'webm')

FIXTURE_SENTENCES = (
    'This is a local practice transcript so the recording and saving flow can be used '
    'before a transcription key is connected.',
    'The audio was captured clearly and the transcript was produced without a network '
    'transcription service.',
    'Everything you record stays on this computer and can be renamed, filed, or copied '
    'into a message.',
)


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def ensure_schema(store):
    with store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                   'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT)')
        if db.execute('SELECT 1 FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,)).fetchone():
            return False
        fresh = not _table(db, 'jobs')
        for statement in filter(None, (part.strip() for part in DDL.split(';'))):
            db.execute(statement)
        db.execute('INSERT OR IGNORE INTO schema_migrations(version, name, applied, note) VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                    'fresh database' if fresh else 'pre-existing database'))
        return True


# ---- titles (port of the donor's src-tauri/src/title.rs) ---------------------------------------

LEADING_FILLER = {
    'a', 'about', 'an', 'brief', 'discuss', 'discussing', 'going', 'gonna', 'hello', 'hey', 'i',
    "i'm", 'im', 'is', 'just', 'make', 'making', 'need', 'needed', 'note', 'ok', 'okay', 'on',
    'record', 'recording', 'regarding', 'so', 'talk', 'talking', 'the', 'this', 'to', 'today',
    'uh', 'um', 'update', 'want', 'wanted', 'we', "we're", 'well', 'were',
}
TRAILING_FILLER = {'a', 'an', 'and', 'for', 'in', 'of', 'on', 'or', 'the', 'to', 'with'}
LOWERCASE_WORDS = {'a', 'an', 'and', 'as', 'at', 'for', 'in', 'of', 'on', 'or', 'the', 'to', 'vs', 'with'}


def _strip_speaker(value):
    if ':' not in value:
        return value
    label, _, rest = value.partition(':')
    label = label.strip()
    if label and len(label) <= 30 and all(ch.isalnum() or ch.isspace() or ch == '-' for ch in label):
        return rest.strip()
    return value


def _clean_word(value):
    return value.strip("".join(ch for ch in value if not (ch.isalnum() or ch in "'-&")) or ' ').strip("""'\"()[]{}<>,.;:!?""")


def _format_word(value, index):
    lower = value.lower()
    letters = ''.join(ch for ch in value if ch.isalpha())
    if any(ch.isdigit() for ch in value):
        return value
    if letters and letters == letters.upper() and len(letters) > 1:
        return value  # keep acronyms
    if index > 0 and lower in LOWERCASE_WORDS:
        return lower
    if not value:
        return value
    return value[0].upper() + value[1:]


def contextual_title(text):
    """First usable sentence turned into a short title, filler stripped (donor behaviour)."""
    for chunk in re.split(r'[.!?\n]', text or ''):
        value = _strip_speaker((chunk or '').strip())
        words = [_clean_word(word) for word in value.split()]
        words = [word for word in words if word and not word.startswith('http')]
        while words and words[0].lower() in LEADING_FILLER:
            words.pop(0)
        while words and words[-1].lower() in TRAILING_FILLER:
            words.pop()
        if not words:
            continue
        title_words, length = [], 0
        for word in words[:9]:
            formatted = _format_word(word, len(title_words))
            next_length = length + len(formatted) + (1 if title_words else 0)
            if next_length > 64:
                break
            length = next_length
            title_words.append(formatted)
        while title_words and title_words[-1].lower() in TRAILING_FILLER:
            title_words.pop()
        title = ' '.join(title_words)
        if title:
            return title
    return None


# ---- audio helpers (stdlib wave; lossless, no external binary) ---------------------------------

def wav_duration_ms(data):
    try:
        with wave.open(io.BytesIO(data), 'rb') as handle:
            frames, rate = handle.getnframes(), handle.getframerate()
            if not rate:
                return None
            return int(round(frames * 1000.0 / rate))
    except (wave.Error, EOFError, ValueError):
        return None


def wav_concatenate(first, second):
    """Join two PCM WAV files when their formats match; None when they cannot be joined."""
    try:
        with wave.open(io.BytesIO(first), 'rb') as a, wave.open(io.BytesIO(second), 'rb') as b:
            if (a.getnchannels(), a.getsampwidth(), a.getframerate()) != \
               (b.getnchannels(), b.getsampwidth(), b.getframerate()):
                return None
            out = io.BytesIO()
            with wave.open(out, 'wb') as writer:
                writer.setnchannels(a.getnchannels())
                writer.setsampwidth(a.getsampwidth())
                writer.setframerate(a.getframerate())
                writer.writeframes(a.readframes(a.getnframes()))
                writer.writeframes(b.readframes(b.getnframes()))
            return out.getvalue()
    except (wave.Error, EOFError, ValueError):
        return None


def pcm_duration_ms(pcm_bytes, rate=TARGET_RATE, width=2):
    return int(round(len(pcm_bytes) / float(rate * width) * 1000.0))


# ---- providers ---------------------------------------------------------------------------------

class TranscriptionProvider:
    """UI never sees provider internals; transcripts are provider-independent text."""
    name = 'provider'
    label = 'Transcription'

    def transcribe_file(self, audio, filename, duration_ms=None):
        raise NotImplementedError

    def supports_stream(self):
        return False

    def open_stream(self):
        raise PolicyError('Live transcription is not available in this mode.')


class FixtureProvider(TranscriptionProvider):
    """Deterministic local provider: the credential-free path used for tests and demos.

    The transcript is derived from the file name (stable across runs), so automation and a
    person without a Meta key can exercise the entire flow end to end.
    """
    name = 'fixture'
    label = 'Local practice mode'

    def transcribe_file(self, audio, filename, duration_ms=None):
        digest = hashlib.sha256((filename or 'audio').encode('utf-8', 'replace')).hexdigest()
        start = int(digest[:2], 16) % len(FIXTURE_SENTENCES)
        count = 1 + int(digest[2:4], 16) % 3
        sentences = [FIXTURE_SENTENCES[(start + index) % len(FIXTURE_SENTENCES)] for index in range(count)]
        if duration_ms:
            sentences.append('(Practice transcript for %s of audio.)'
                             % _human_duration(duration_ms))
        return {'text': ' '.join(sentences), 'turns': []}

    def supports_stream(self):
        return True

    def open_stream(self):
        return _FixtureStream()


class _FixtureStream:
    """Deterministic live stream: emits one sentence every ~4 seconds of audio."""
    def __init__(self):
        self.sentences = []
        self.audio_ms = 0
        self._next_at = 3800

    def feed(self, pcm_bytes):
        self.audio_ms += pcm_duration_ms(pcm_bytes)
        while self.audio_ms >= self._next_at and len(self.sentences) < 6:
            self.sentences.append(FIXTURE_SENTENCES[len(self.sentences) % len(FIXTURE_SENTENCES)])
            self._next_at += 3800

    def status(self):
        return {'text': ' '.join(self.sentences), 'final': False}

    def finish(self):
        if not self.sentences:
            self.sentences.append(FIXTURE_SENTENCES[0])
        return {'text': ' '.join(self.sentences), 'final': True}


class MuseProvider(TranscriptionProvider):
    """Meta Muse Voice Transcribe (donor protocol).

    File transcription: multipart POST to /v1/asr/transcribe with {model, audioEncoding: WAV,
    mode: DIARIZATION}; realtime: websocket handshake (Bearer, PCM_24KHZ, ENDPOINTING,
    CUMULATIVE) with binary PCM frames and an endStream message. Error copy is ported verbatim
    from the donor so users never see raw HTTP vocabulary.
    """
    name = 'muse'
    label = 'Muse (Meta)'
    TRANSCRIBE_URL = 'https://api.meta.ai/v1/asr/transcribe'
    REALTIME_URL = 'wss://api.meta.ai/v1/asr/realtime'
    MODEL = 'muse-voice-transcribe-1.0'

    def __init__(self, api_key):
        self.api_key = api_key

    def transcribe_file(self, audio, filename, duration_ms=None):
        if len(audio) > MAX_UPLOAD_BYTES:
            raise PolicyError("The prepared audio exceeds Muse's 32 MB limit.")
        if duration_ms and duration_ms > MAX_DURATION_MS:
            raise PolicyError('Muse accepts audio up to 10 minutes. Split this file, then try again.')
        request = json.dumps({'model': self.MODEL, 'audioEncoding': 'WAV', 'mode': 'DIARIZATION'})
        boundary = 'kel' + uid().replace('-', '')
        body = _multipart(boundary, [('request', 'request.json', 'application/json', request.encode()),
                                     ('audio', 'audio.wav', 'audio/wav', audio)])
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen
        http = Request('%s?sessionId=%s' % (self.TRANSCRIBE_URL, 'upload-' + uid()),
                       data=body, method='POST',
                       headers={'Authorization': 'Bearer ' + self.api_key,
                                'Content-Type': 'multipart/form-data; boundary=' + boundary,
                                'Accept': 'application/json'})
        try:
            with urlopen(http, timeout=600) as response:
                payload = json.loads(response.read().decode('utf-8', 'replace'))
        except HTTPError as error:
            detail = ''
            try:
                detail = error.read().decode('utf-8', 'replace').lower()
            except Exception:
                detail = ''
            status = error.code
            if status in (401, 403):
                raise PolicyError('The Meta API key was not accepted. Replace it in Settings.') from None
            if status == 413:
                raise PolicyError("The prepared audio exceeds Muse's 32 MB limit.") from None
            if status == 429:
                raise PolicyError('Muse is busy for this account. Wait briefly, then try again.') from None
            if status == 400 and '10 minute' in detail:
                raise PolicyError('Muse accepts audio up to 10 minutes. Split this file, then try again.')
            if status == 400:
                raise PolicyError('Muse could not read the prepared audio.') from None
            raise PolicyError('Muse could not complete the transcription. Try again in a moment.') from None
        except PolicyError:
            raise
        except Exception:
            raise PolicyError('Muse could not connect. Check your network, then try again.') from None
        turns = payload.get('turns') or []
        if any(turn.get('speaker') for turn in turns):
            text = '\n\n'.join(('%s: %s' % (turn.get('speaker'), (turn.get('transcript') or '').strip()))
                               if turn.get('speaker') else (turn.get('transcript') or '').strip()
                               for turn in turns)
        else:
            text = (payload.get('transcript') or '').strip()
        return {'text': text, 'turns': turns, 'duration_ms': payload.get('audioDurationMs')}

    def supports_stream(self):
        try:
            import websocket  # websocket-client
        except ImportError:
            return False
        return True

    def open_stream(self):
        try:
            import websocket  # noqa: F401  (websocket-client)
        except ImportError:
            raise PolicyError('Live transcription is not available in this build; Kel will '
                              'transcribe when you stop.')
        return _MuseStream(self)


def _multipart(boundary, parts):
    lines = []
    for name, filename, content_type, data in parts:
        lines.append(('--%s\r\n' % boundary).encode())
        lines.append(('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (name, filename)).encode())
        lines.append(('Content-Type: %s\r\n\r\n' % content_type).encode())
        lines.append(data)
        lines.append(b'\r\n')
    lines.append(('--%s--\r\n' % boundary).encode())
    return b''.join(lines)


def _human_duration(ms):
    total = int(round(ms / 1000.0))
    minutes, seconds = divmod(max(0, total), 60)
    if minutes and seconds:
        return '%dm %ds' % (minutes, seconds)
    if minutes:
        return '%dm' % minutes
    return '%ds' % seconds


# ---- Muse realtime client ----------------------------------------------------------------------

MUSE_REALTIME_URL = 'wss://api.meta.ai/v1/asr/realtime'
MUSE_MODEL = 'muse-voice-transcribe-1.0'


def _muse_handshake(api_key):
    return {'authorization': {'accessToken': 'Bearer %s' % api_key},
            'audioEncoding': 'PCM_24KHZ', 'model': MUSE_MODEL, 'mode': 'ENDPOINTING',
            'partialMode': 'CUMULATIVE', 'emitAudioProgress': True}


class _MuseStream:
    """Realtime Muse socket (websocket-client) with the donor's protocol and plain-language errors."""

    def __init__(self, provider):
        self.provider = provider
        self.session_id = 'live-' + uuid.uuid4().hex
        self._queue = queue.Queue()
        self.finals = []
        self.partial = ''
        self.state = 'connecting'
        self.error = ''
        self.audio_ms = 0
        self._turns = set()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        deadline = time.time() + 12
        while self.state == 'connecting' and time.time() < deadline:
            time.sleep(0.05)

    # -- protocol ---------------------------------------------------------------------------------

    def _run(self):
        try:
            import websocket  # websocket-client
            url = '%s?sessionId=%s' % (MUSE_REALTIME_URL, self.session_id)
            socket = websocket.create_connection(url, timeout=12)
            socket.send(json.dumps(_muse_handshake(self.provider.api_key)))
            ack = socket.recv()
            data = json.loads(ack) if isinstance(ack, str) else {}
            if data.get('type') == 'error':
                self.error = str(data.get('message') or 'The Meta API key was not accepted.')
                self.state = 'failed'
                return
            if not data.get('sessionId'):
                self.error = 'Kel could not confirm the live transcription session.'
                self.state = 'failed'
                return
            self.state = 'live'
            while True:
                item = self._queue.get()
                if item is None:
                    socket.send(json.dumps({'type': 'endStream'}))
                    break
                socket.send_binary(item)
                self._read_some(socket)
                if self.state != 'live':
                    return
            deadline = time.time() + 20
            while time.time() < deadline and self.state == 'live':
                self._read_some(socket, budget=0.3)
            if self.state == 'live':
                self.state = 'closed'
            try:
                socket.close()
            except Exception:
                pass
        except Exception as exc:
            text = str(exc)
            if '401' in text or '403' in text or 'Handshake status' in text:
                self.error = 'The Meta API key was not accepted.'
            elif not self.error:
                self.error = 'Kel lost the live transcription connection.'
            self.state = 'failed'

    def _read_some(self, socket, budget=0.05):
        try:
            socket.settimeout(budget)
        except Exception:
            pass
        while True:
            try:
                frame = socket.recv()
            except Exception:
                return
            if not frame:
                self.state = 'closed'
                return
            self._apply(frame)

    def _apply(self, frame):
        if isinstance(frame, bytes):
            return
        try:
            data = json.loads(frame)
        except Exception:
            return
        if data.get('type') == 'error':
            self.error = str(data.get('message') or self.error or 'Muse reported a problem.')
            self.state = 'failed'
            return
        text = (data.get('transcript') or '').strip()
        if data.get('audioProcessedMs'):
            try:
                self.audio_ms = max(self.audio_ms, int(data['audioProcessedMs']))
            except Exception:
                pass
        if not text:
            return
        if data.get('final'):
            turn = data.get('turnId')
            if turn not in self._turns:
                self._turns.add(turn)
                self.finals.append(text)
                self.partial = ''
        else:
            self.partial = text

    # -- provider-stream face ---------------------------------------------------------------------

    def feed(self, pcm_bytes):
        self._queue.put(bytes(pcm_bytes))

    def _full(self):
        if self.finals:
            return ' '.join(self.finals).strip()
        return self.partial.strip()

    def status(self):
        return {'text': self._full(), 'final': False, 'state': self.state, 'error': self.error}

    def finish(self):
        self._queue.put(None)
        deadline = time.time() + 25
        while self.state in ('connecting', 'live') and time.time() < deadline:
            time.sleep(0.05)
        return {'text': self._full(), 'final': True, 'state': self.state, 'error': self.error}


# ---- the library service ------------------------------------------------------------------------

class Transcription:
    """Folders + transcripts (donor model) with provider-independent text and Kel persistence."""

    def __init__(self, store):
        self.store = store
        ensure_schema(store)
        self._streams = _STREAMS

    # -- provider + key ---------------------------------------------------------------------------

    def _setting(self, name):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT value FROM transcription_settings WHERE name=?', (name,)).fetchone()
        return row['value'] if row else ''

    def _set_setting(self, name, value):
        with self.store.transaction() as db:
            db.execute('INSERT OR REPLACE INTO transcription_settings(name,value) VALUES(?,?)',
                       (name, value))

    def api_key(self):
        key = os.environ.get('META_API_KEY') or os.environ.get('MUSE_API_KEY') or ''
        return key.strip() or self._setting('meta_api_key')

    def set_key(self, key):
        key = (key or '').strip()
        if not key:
            raise PolicyError('Paste the Meta API key first.')
        self._set_setting('meta_api_key', key)
        return {'has_key': True}

    def clear_key(self):
        self._set_setting('meta_api_key', '')
        return {'has_key': False}

    def provider(self):
        override = (os.environ.get('KEL_TRANSCRIPTION_PROVIDER') or '').strip().lower()
        if override == 'fixture':
            return FixtureProvider()
        if override == 'muse':
            key = self.api_key()
            if not key:
                raise PolicyError('Add a Meta API key first, then try again.')
            return MuseProvider(key)
        if self.api_key():
            return MuseProvider(self.api_key())
        return FixtureProvider()

    def status(self):
        mode = 'fixture'
        has_key = bool(self.api_key())
        if (os.environ.get('KEL_TRANSCRIPTION_PROVIDER') or '').strip().lower() == 'muse' or has_key:
            mode = 'muse'
        try:
            live = MuseProvider('x').supports_stream() if mode == 'muse' else True
        except Exception:
            live = False
        return {'mode': mode, 'has_key': has_key, 'live_capable': live,
                'label': 'Muse' if mode == 'muse' else 'Practice mode',
                'detail': ('Muse transcribes your audio.' if mode == 'muse'
                           else 'Practice mode transcribes locally with clear, repeatable text — '
                                'add a Meta API key in Settings to use Muse.')}

    # -- library ----------------------------------------------------------------------------------

    def library(self):
        with contextlib.closing(self.store.connect()) as db:
            folders = [dict(row) for row in db.execute(
                'SELECT * FROM transcription_folders ORDER BY name COLLATE NOCASE')]
            transcripts = [self._transcript_row(row, db) for row in db.execute(
                'SELECT * FROM transcripts ORDER BY created DESC')]
        return {'folders': folders, 'transcripts': transcripts}

    def _transcript_row(self, row, db=None):
        item = dict(row)
        item['has_audio'] = bool(item.get('audio_path')) and os.path.isfile(item.get('audio_path') or '')
        item['audio_url'] = None
        item.pop('audio_path', None)
        return item

    def _public(self, row):
        return self._transcript_row(dict(row))

    def transcript(self, transcript_id):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM transcripts WHERE id=?', (transcript_id,)).fetchone()
            if not row:
                raise PolicyError('That transcript no longer exists.')
            return dict(row)

    def transcript_rename(self, transcript_id, name):
        name = (name or '').strip()
        if not name:
            raise PolicyError('Give the transcript a name first.')
        with self.store.transaction() as db:
            db.execute('UPDATE transcripts SET name=?, updated=? WHERE id=?',
                       (name[:120], time.time(), transcript_id))
        return self._public(self.transcript(transcript_id))

    def transcript_delete(self, transcript_id):
        with self.store.transaction() as db:
            row = db.execute('SELECT audio_path FROM transcripts WHERE id=?', (transcript_id,)).fetchone()
            db.execute('DELETE FROM transcripts WHERE id=?', (transcript_id,))
        if row and row['audio_path']:
            try:
                os.remove(row['audio_path'])
            except OSError:
                pass
        return {'id': transcript_id, 'deleted': True}

    def assign(self, transcript_id, folder_id):
        with self.store.transaction() as db:
            if folder_id:
                exists = db.execute('SELECT 1 FROM transcription_folders WHERE id=?', (folder_id,)).fetchone()
                if not exists:
                    raise PolicyError('That folder no longer exists.')
            db.execute('UPDATE transcripts SET folder_id=?, updated=? WHERE id=?',
                       (folder_id or None, time.time(), transcript_id))
        return self._public(self.transcript(transcript_id))

    def folder_create(self, name):
        name = (name or '').strip()
        if not name:
            raise PolicyError('Give the folder a name first.')
        folder_id = uid()
        with self.store.transaction() as db:
            db.execute('INSERT INTO transcription_folders(id,name,created) VALUES(?,?,?)',
                       (folder_id, name[:80], time.time()))
        return {'id': folder_id, 'name': name[:80]}

    def folder_rename(self, folder_id, name):
        name = (name or '').strip()
        if not name:
            raise PolicyError('Give the folder a name first.')
        with self.store.transaction() as db:
            db.execute('UPDATE transcription_folders SET name=? WHERE id=?', (name[:80], folder_id))
        return {'id': folder_id, 'name': name[:80]}

    def folder_delete(self, folder_id):
        with self.store.transaction() as db:
            db.execute('UPDATE transcripts SET folder_id=NULL WHERE folder_id=?', (folder_id,))
            db.execute('DELETE FROM transcription_folders WHERE id=?', (folder_id,))
        return {'id': folder_id, 'deleted': True}

    # -- audio files ------------------------------------------------------------------------------

    def _audio_dir(self):
        path = os.path.join(str(self.store.root), 'transcription', 'audio')
        os.makedirs(path, exist_ok=True)
        return path

    def _write_audio(self, transcript_id, extension, data):
        extension = re.sub(r'[^a-z0-9]', '', (extension or 'wav').lower()) or 'wav'
        path = os.path.join(self._audio_dir(), '%s.%s' % (transcript_id, extension))
        with open(path, 'wb') as handle:
            handle.write(data)
        return path

    def export_text(self, transcript_id):
        row = self.transcript(transcript_id)
        return {'name': (row['name'] or 'transcript') + '.txt', 'text': row['text'] or ''}

    def export_audio(self, transcript_id):
        row = self.transcript(transcript_id)
        path = row.get('audio_path') or ''
        if not path or not os.path.isfile(path):
            raise PolicyError('This transcript has no saved audio.')
        with open(path, 'rb') as handle:
            data = handle.read()
        extension = os.path.splitext(path)[1].lstrip('.') or 'wav'
        mime = {'wav': 'audio/wav', 'mp3': 'audio/mpeg', 'mp4': 'audio/mp4',
                'm4a': 'audio/mp4', 'ogg': 'audio/ogg', 'webm': 'audio/webm'}.get(extension, 'audio/wav')
        return {'name': (row['name'] or 'audio') + '.' + extension,
                'mime': mime, 'data': base64.b64encode(data).decode('ascii')}

    # -- recordings -------------------------------------------------------------------------------

    def save_recording(self, text, duration_ms, audio, extension='wav', append_to=None,
                       name_hint=''):
        data = base64.b64decode(audio or '', validate=True)
        if not data:
            raise PolicyError('The recording contained no audio.')
        text = (text or '').strip()
        duration_ms = max(0, int(duration_ms or 0))
        if append_to:
            target = self.transcript(append_to)
            combined_audio = None
            if (target.get('audio_path') and os.path.isfile(target['audio_path'])
                    and target['audio_path'].lower().endswith('.wav') and extension == 'wav'):
                try:
                    with open(target['audio_path'], 'rb') as handle:
                        combined_audio = wav_concatenate(handle.read(), data)
                except Exception:
                    combined_audio = None
            with self.store.transaction() as db:
                db.execute('UPDATE transcripts SET text=?, duration_ms=?, updated=?, status=? WHERE id=?',
                           ('\n\n'.join(part for part in (target.get('text') or '', text) if part).strip(),
                            (target.get('duration_ms') or 0) + duration_ms, time.time(), 'complete',
                            append_to))
            if combined_audio is not None:
                with open(target['audio_path'], 'wb') as handle:
                    handle.write(combined_audio)
            else:
                self._write_audio(append_to + '-append-' + uid()[:8], extension, data)
            return self._public(self.transcript(append_to))
        transcript_id = uid()
        path = self._write_audio(transcript_id, extension, data)
        now = time.time()
        name = contextual_title(text) or (name_hint.strip() or 'Recording %s' % time.strftime('%b %d, %H:%M'))
        with self.store.transaction() as db:
            db.execute('INSERT INTO transcripts(id,name,text,created,updated,folder_id,audio_path,'
                       'source_type,source_filename,duration_ms,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (transcript_id, name, text, now, now, None, path, 'recording', None,
                        duration_ms, 'complete'))
        return self._public(self.transcript(transcript_id))

    def combine(self, target_id, source_id):
        if target_id == source_id:
            raise PolicyError('Choose a different transcript to combine.')
        target = self.transcript(target_id)
        source = self.transcript(source_id)
        text = '\n\n'.join(part for part in ((target.get('text') or '').strip(),
                                             (source.get('text') or '').strip()) if part)
        duration = (target.get('duration_ms') or 0) + (source.get('duration_ms') or 0)
        combined_audio = None
        target_audio = target.get('audio_path') or ''
        source_audio = source.get('audio_path') or ''
        if (target_audio and source_audio and os.path.isfile(target_audio)
                and os.path.isfile(source_audio) and target_audio.lower().endswith('.wav')
                and source_audio.lower().endswith('.wav')):
            try:
                with open(target_audio, 'rb') as handle:
                    first = handle.read()
                with open(source_audio, 'rb') as handle:
                    second = handle.read()
                combined_audio = wav_concatenate(first, second)
            except Exception:
                combined_audio = None
        with self.store.transaction() as db:
            db.execute('UPDATE transcripts SET text=?, duration_ms=?, updated=? WHERE id=?',
                       (text, duration, time.time(), target_id))
            db.execute('DELETE FROM transcripts WHERE id=?', (source_id,))
        if combined_audio is not None:
            with open(target_audio, 'wb') as handle:
                handle.write(combined_audio)
        elif source_audio:
            try:
                os.remove(source_audio)
            except OSError:
                pass
        return self._public(self.transcript(target_id))

    # -- transcription ----------------------------------------------------------------------------

    def _validate_upload(self, filename, data):
        if not data:
            raise PolicyError('That audio file is empty.')
        if len(data) > MAX_UPLOAD_BYTES:
            raise PolicyError('This audio is larger than 32 MB. Split it, then try again.')
        extension = filename.rsplit('.', 1)[-1].lower() if '.' in (filename or '') else ''
        if extension and extension not in ACCEPTED_EXTENSIONS:
            raise PolicyError('That file type is not supported. Choose a common audio file (MP3, MP4, or M4A).')
        duration = wav_duration_ms(data)
        if duration is None and (extension in ('', 'wav') or self.provider().name == 'muse'):
            raise PolicyError('This audio file could not be read. It may be damaged or in an '
                              'unsupported format.')
        if duration and duration > MAX_DURATION_MS:
            raise PolicyError('Muse accepts audio up to 10 minutes. Split this file, then try again.')
        return duration

    def transcribe_upload(self, filename, audio, title_hint=''):
        data = base64.b64decode(audio or '', validate=True)
        duration = self._validate_upload(filename, data)
        transcript_id = uid()
        extension = (filename.rsplit('.', 1)[-1].lower() if '.' in (filename or '') else 'wav')
        path = self._write_audio(transcript_id, extension, data)
        now = time.time()
        stem = os.path.splitext(os.path.basename(filename or 'Audio'))[0] or 'Audio'
        with self.store.transaction() as db:
            db.execute('INSERT INTO transcripts(id,name,text,created,updated,folder_id,audio_path,'
                       'source_type,source_filename,duration_ms,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (transcript_id, stem, '', now, now, None, path, 'upload',
                        os.path.basename(filename or 'audio'), duration, 'processing'))
        provider = self.provider()
        try:
            result = provider.transcribe_file(data, filename, duration)
        except PolicyError as exc:
            with self.store.transaction() as db:
                db.execute('UPDATE transcripts SET status=?, updated=? WHERE id=?',
                           ('failed', time.time(), transcript_id))
            raise PolicyError(str(exc))
        text = (result.get('text') or '').strip()
        turns = result.get('turns') or []
        if turns and any(turn.get('speaker') for turn in turns):
            text = '\n\n'.join(
                ('%s: %s' % (turn['speaker'], turn['transcript'].strip())
                 if turn.get('speaker') else turn['transcript'].strip()) for turn in turns)
        name = (title_hint or '').strip() or contextual_title(text) or stem
        final_duration = result.get('duration_ms') or duration
        with self.store.transaction() as db:
            db.execute('UPDATE transcripts SET name=?, text=?, duration_ms=?, status=?, updated=? WHERE id=?',
                       (name[:120], text, final_duration, 'complete' if text else 'failed', time.time(),
                        transcript_id))
        return self._public(self.transcript(transcript_id))

    def quick_transcribe(self, filename, audio, duration_hint=None):
        """Composer path: produce editable text, keep nothing in the library."""
        data = base64.b64decode(audio or '', validate=True)
        duration = self._validate_upload(filename, data) or (int(duration_hint) if duration_hint else None)
        provider = self.provider()
        result = provider.transcribe_file(data, filename, duration)
        return {'text': (result.get('text') or '').strip(), 'turns': result.get('turns') or [],
                'duration_ms': result.get('duration_ms') or duration,
                'mode': provider.name}

    # -- live streaming ---------------------------------------------------------------------------

    def stream_start(self, conversation=None):
        provider = self.provider()
        if not provider.supports_stream():
            return {'session_id': None, 'mode': provider.name, 'live': False,
                    'label': 'Kel will transcribe when you stop recording.'}
        handle = provider.open_stream()
        session_id = 'ts-' + uuid.uuid4().hex
        self._streams[session_id] = {'handle': handle, 'provider': provider.name,
                                     'started': time.time(), 'conversation': conversation or ''}
        self._gc_streams()
        return {'session_id': session_id, 'mode': provider.name, 'live': True,
                'label': ('Live transcription is on.' if provider.name == 'muse'
                          else 'Practice transcript is on — check any answers before applying.')}

    def _stream(self, session_id):
        entry = self._streams.get(session_id)
        if not entry:
            raise PolicyError('That recording session has ended.')
        return entry

    def _gc_streams(self):
        cutoff = time.time() - 2 * 60 * 60
        for key in [key for key, entry in self._streams.items() if entry['started'] < cutoff]:
            self._streams.pop(key, None)

    def stream_chunk(self, session_id, pcm):
        entry = self._stream(session_id)
        data = base64.b64decode(pcm or '', validate=True)
        if data:
            entry['handle'].feed(data)
        state = entry['handle'].status()
        return {'session_id': session_id, 'text': state.get('text') or '',
                'state': state.get('state') or ('live' if entry['provider'] == 'fixture' else 'live'),
                'error': state.get('error') or ''}

    def stream_status(self, session_id):
        entry = self._stream(session_id)
        state = entry['handle'].status()
        return {'session_id': session_id, 'text': state.get('text') or '',
                'state': state.get('state') or 'live', 'error': state.get('error') or ''}

    def stream_finish(self, session_id):
        entry = self._stream(session_id)
        result = entry['handle'].finish()
        duration = getattr(entry['handle'], 'audio_ms', 0) or 0
        self._streams.pop(session_id, None)
        return {'text': (result.get('text') or '').strip(), 'duration_ms': duration,
                'mode': entry['provider'], 'error': result.get('error') or ''}
