"""Inert original bytes and reviewed derived text; no file execution or extraction here."""
import contextlib
import hashlib
import time

from .core import PolicyError, uid
from .memory import scan_secret

MAX_BYTES = 5 * 1024 * 1024
TOTAL_BYTES = 50 * 1024 * 1024
DDL = """
CREATE TABLE IF NOT EXISTS reference_sources(
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL, name TEXT NOT NULL,
 source BLOB NOT NULL, source_sha256 TEXT NOT NULL, text TEXT NOT NULL,
 text_sha256 TEXT NOT NULL, kind TEXT NOT NULL, extraction TEXT NOT NULL,
 pages INTEGER NOT NULL, language TEXT, created REAL NOT NULL,
 import_id TEXT, conversation_id TEXT);
"""


class ReferenceSources:
    def __init__(self, store):
        self.store = store
        with contextlib.closing(store.connect()) as db:
            db.executescript(DDL)

    @staticmethod
    def _check(row):
        source = bytes(row['source'])
        if (not 0 < len(source) <= MAX_BYTES or
                hashlib.sha256(source).hexdigest() != row['source_sha256'] or
                hashlib.sha256(row['text'].encode('utf-8')).hexdigest() != row['text_sha256']):
            raise PolicyError('Reference source changed; extract it again')
        return source

    @staticmethod
    def _visible(db, row):
        from .work_import import _visible
        if not row['import_id']:
            return row['created'] >= time.time() - 86400
        conversation = db.execute('SELECT project_id FROM conversations WHERE id=?',(row['conversation_id'],)).fetchone()
        return bool(conversation and conversation['project_id']==row['project_id'] and _visible(db,row['conversation_id']))

    @staticmethod
    def _metadata(row):
        return {'id':row['id'], 'name':row['name'], 'source_sha256':row['source_sha256'],
                'source_bytes':len(row['source']), 'text_sha256':row['text_sha256'],
                'text_chars':len(row['text']), 'kind':row['kind'], 'extraction':row['extraction'],
                'pages':row['pages'], 'language':row['language'], 'trust':'external-untrusted',
                'state':'adopted' if row['import_id'] else 'staged', 'snippet':row['text'][:600]}

    def stage(self, project_id, name, source_bytes, text, kind, extraction, pages, language=None):
        from .work_import import _project, _reference_files
        import re
        _reference_files([{'name':name, 'text':text}], '')
        if type(source_bytes) is not bytes or not 0 < len(source_bytes) <= MAX_BYTES:
            raise PolicyError('Reference originals support 1 byte to 5 MB')
        if (kind, extraction) not in (('pdf','pdf-text'), ('image','image-ocr')):
            raise PolicyError('Unsupported reference extraction')
        if type(pages) is not int or not 1 <= pages <= 100:
            raise PolicyError('Reference extraction supports 1 to 100 pages')
        if language is not None and (not isinstance(language,str) or not re.fullmatch(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{2,8}){0,3}',language)):
            raise PolicyError('Invalid extraction language')
        if scan_secret(name + '\n' + text):
            raise PolicyError('Remove secret-like content before importing')
        now, sid = time.time(), uid()
        with self.store.transaction() as db:
            _project(db, project_id)
            db.execute('DELETE FROM reference_sources WHERE import_id IS NULL AND created<?', (now-86400,))
            if db.execute('SELECT COUNT(*) FROM reference_sources WHERE project_id=? AND import_id IS NULL', (project_id,)).fetchone()[0] >= 30:
                raise PolicyError('At most 30 staged references per Project; discard one first')
            used = db.execute('SELECT COALESCE(SUM(length(source)),0) FROM reference_sources').fetchone()[0]
            if used + len(source_bytes) > TOTAL_BYTES:
                raise PolicyError('Reference originals reached the 50 MB storage limit')
            db.execute('INSERT INTO reference_sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (sid,project_id,name,source_bytes,hashlib.sha256(source_bytes).hexdigest(),text,
                        hashlib.sha256(text.encode('utf-8')).hexdigest(),kind,extraction,pages,language,now,None,None))
            return self._metadata(db.execute('SELECT * FROM reference_sources WHERE id=?',(sid,)).fetchone())

    @classmethod
    def resolve(cls, db, project_id, ids):
        if not isinstance(ids,list) or len(ids)>10 or any(not isinstance(sid,str) or not 1 <= len(sid) <= 200 for sid in ids) or len(set(ids))!=len(ids):
            raise PolicyError('Use at most 10 distinct extraction receipt IDs')
        references = []
        for sid in ids:
            row = db.execute('SELECT * FROM reference_sources WHERE id=? AND project_id=?',(sid,project_id)).fetchone()
            if not row or not cls._visible(db,row):
                raise PolicyError('Reference source expired, was deleted, or belongs to another Project')
            cls._check(row)
            origin = {key:row[key] for key in ('source_sha256','text_sha256','kind','extraction','pages','language')}
            origin.update(id=sid,source_bytes=len(row['source']))
            references.append({'name':row['name'],'text':row['text'],'source':origin})
        return references

    @classmethod
    def adopt(cls, db, project_id, references, import_id, conversation_id):
        ids = [file['source']['id'] for file in references if 'source' in file]
        current = cls.resolve(db,project_id,ids)
        expected = [file for file in references if 'source' in file]
        if current != expected:
            raise PolicyError('Extracted reference changed; review the import again')
        for sid in ids:
            # Reuse keeps the first durable custody link. It never resurrects a deleted import.
            db.execute('UPDATE reference_sources SET import_id=?,conversation_id=? WHERE id=? AND import_id IS NULL',
                       (import_id,conversation_id,sid))

    def entries(self, project_id):
        from .work_import import _project
        with contextlib.closing(self.store.connect()) as db:
            _project(db,project_id)
            return [self._metadata(row) for row in db.execute('SELECT * FROM reference_sources WHERE project_id=? ORDER BY created DESC LIMIT 100',(project_id,)) if self._visible(db,row)]

    def original(self, project_id, source_id):
        from .work_import import _project
        with contextlib.closing(self.store.connect()) as db:
            _project(db,project_id)
            row = db.execute('SELECT * FROM reference_sources WHERE id=? AND project_id=?',(source_id,project_id)).fetchone()
            if not row or not self._visible(db,row):
                raise PolicyError('Reference original is unavailable in this Project')
            return {'metadata':self._metadata(row), 'bytes':self._check(row)}

    def discard(self, project_id, source_id):
        from .work_import import _project
        with self.store.transaction() as db:
            _project(db,project_id)
            row = db.execute('SELECT import_id FROM reference_sources WHERE id=? AND project_id=?',(source_id,project_id)).fetchone()
            if not row or row['import_id']:
                raise PolicyError('Only staged reference sources can be discarded')
            db.execute('DELETE FROM reference_sources WHERE id=? AND project_id=?',(source_id,project_id))
            return {'id':source_id,'discarded':True}
