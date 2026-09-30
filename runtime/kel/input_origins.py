"""One-shot transcript provenance across the desktop's existing ACP transport.

The queue stores identifiers and a digest, never transcript text or permissions.
Only the matching first-send text in the intended Project can consume it.
"""
import time
import uuid

from .core import PolicyError, digest


class InputOrigins:
    def __init__(self, store):
        self.store = store
        with store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS pending_input_origins('
                       'donor_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, transcript_id TEXT NOT NULL,'
                       'text_digest TEXT NOT NULL, created REAL NOT NULL)')

    def queue(self, donor_id, project_id, transcript_id, text):
        try:
            donor_id = str(uuid.UUID(str(donor_id)))
        except (ValueError, TypeError):
            raise PolicyError('Choose a Kel chat for this transcript.') from None
        if not isinstance(text, str) or not text.strip() or len(text) > 20000:
            raise PolicyError('Transcript input must contain 1 to 20000 characters.')
        from .transcription import Transcription
        saved = Transcription(self.store).transcript(transcript_id)
        with self.store.transaction() as db:
            db.execute('DELETE FROM pending_input_origins WHERE created<?', (time.time() - 3600,))
            db.execute('INSERT INTO pending_input_origins VALUES(?,?,?,?,?) ON CONFLICT(donor_id) DO UPDATE SET '
                       'project_id=excluded.project_id,transcript_id=excluded.transcript_id,'
                       'text_digest=excluded.text_digest,created=excluded.created',
                       (donor_id, project_id, saved['id'], digest(text.strip()), time.time()))
        return {'queued': True, 'transcript_id': saved['id']}

    def claim(self, donor_id, project_id, text):
        with self.store.transaction() as db:
            db.execute('DELETE FROM pending_input_origins WHERE created<?', (time.time() - 3600,))
            row = db.execute('SELECT * FROM pending_input_origins WHERE donor_id=?', (donor_id,)).fetchone()
            if not row or row['project_id'] != project_id or row['text_digest'] != digest(text.strip()):
                return None
            db.execute('DELETE FROM pending_input_origins WHERE donor_id=?', (donor_id,))
            return {'id': row['transcript_id']}
