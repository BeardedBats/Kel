"""Project context, immutable file snapshots, and bounded worker handoffs."""
import base64
import contextlib
import json
import os
from pathlib import Path
import time
import uuid
from .core import PolicyError, uid, digest, encode


def image_mime(content):
    return ('image/png' if content.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if content.startswith(b'\xff\xd8\xff') else
            'image/gif' if content.startswith((b'GIF87a',b'GIF89a')) else
            'image/webp' if content[:4]==b'RIFF' and content[8:12]==b'WEBP' else None)


def _attachment_content(store, row):
    from .native import _plain_schema_path
    path=store.root/row['path']
    try:
        path=_plain_schema_path(path)
        if not path.resolve().is_relative_to((store.root/'attachments').resolve()):
            raise PolicyError('Attachment escaped storage')
        before=path.stat()
        if before.st_size!=row['size'] or not 0<before.st_size<=5_000_000:
            raise PolicyError('Attachment bytes changed or exceed 5 MB')
        descriptor=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0))
        with os.fdopen(descriptor,'rb') as source:
            opened=os.fstat(source.fileno())
            if opened.st_nlink!=1 or (opened.st_dev,opened.st_ino)!=(before.st_dev,before.st_ino):
                raise PolicyError('Attachment storage changed during read')
            raw=source.read(5_000_001)
        _plain_schema_path(path)
        after=path.stat()
        if ((after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)!=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)
                or len(raw)!=row['size'] or digest(raw)!=row['sha256']):
            raise PolicyError('Attachment bytes changed')
        return raw
    except (OSError,RuntimeError) as exc:
        raise PolicyError('Attachment storage is unavailable or linked') from exc


class Context:
    def __init__(self,store):
        self.store=store
        with contextlib.closing(store.connect()) as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,root TEXT,context TEXT,updated REAL);
            CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,project_id TEXT,title TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS attachments(id TEXT PRIMARY KEY,conversation_id TEXT,name TEXT,path TEXT,sha256 TEXT,size INTEGER,mime TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS grants(id TEXT PRIMARY KEY,project_id TEXT,action_digest TEXT,expires REAL,revoked INTEGER DEFAULT 0,UNIQUE(project_id,action_digest));
            CREATE TABLE IF NOT EXISTS handoffs(run_id TEXT PRIMARY KEY,sha256 TEXT,data TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS submission_context(submission_id TEXT PRIMARY KEY,status TEXT NOT NULL,updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS request_calls(call_id TEXT PRIMARY KEY,submission_id TEXT NOT NULL,state TEXT NOT NULL,estimate TEXT NOT NULL,usage TEXT,cancellation_supported INTEGER NOT NULL,created REAL NOT NULL,updated REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS request_calls_submission ON request_calls(submission_id,created);
            ''')
            from .rewind import ensure
            ensure(db)  # D-75.2: rewound messages leave the history every handoff reads
            db.execute('INSERT OR IGNORE INTO projects VALUES(?,?,?,?,?)',('default','General',None,'',time.time()))
            db.execute('INSERT OR IGNORE INTO conversations VALUES(?,?,?,?)',('main','default','New conversation',time.time()))

    def context_status(self, submission_id):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT status FROM submission_context WHERE submission_id=?', (submission_id,)).fetchone()
        return json.loads(row['status']) if row else None

    def request_calls(self, submission_id):
        with contextlib.closing(self.store.connect()) as db:
            rows = db.execute('SELECT * FROM request_calls WHERE submission_id=? ORDER BY created,call_id', (submission_id,)).fetchall()
        return [{**dict(row), 'estimate': json.loads(row['estimate']),
                 'usage': json.loads(row['usage']) if row['usage'] else None,
                 'cancellation_supported': bool(row['cancellation_supported'])} for row in rows]

    def project(self,name,root=None,notes='',project_id=None):
        if not isinstance(name,str) or not name.strip() or len(name)>120: raise PolicyError('Name must be 1 to 120 characters')
        if not isinstance(notes,str) or len(notes)>12000: raise PolicyError('Project context exceeds 12000 characters')
        if root:
            root=str(Path(root).resolve(strict=True))
            if not Path(root).is_dir(): raise PolicyError('Project folder is not a directory')
        pid=project_id or uid()
        with self.store.transaction() as db:
            old=db.execute('SELECT root FROM projects WHERE id=?',(pid,)).fetchone()
            if old and old['root']!=root:
                db.execute('UPDATE grants SET revoked=1 WHERE project_id=?',(pid,))
            db.execute('INSERT INTO projects VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,root=excluded.root,context=excluded.context,updated=excluded.updated',
                       (pid,name.strip(),root,notes,time.time()))
        return pid

    def conversation(self,project_id='default',title='New conversation',conversation_id=None):
        """A new conversation; with `conversation_id`, the conversation an ACP session reserved
        (ST-04: created on its first message, so opening a chat writes nothing). Idempotent."""
        cid=conversation_id or uid()
        if conversation_id is not None:
            try:
                cid=str(uuid.UUID(str(conversation_id)))
            except ValueError:
                raise PolicyError('Invalid conversation id') from None
        with self.store.transaction() as db:
            if conversation_id is not None and db.execute('SELECT 1 FROM conversations WHERE id=?',(cid,)).fetchone():
                return cid
            if not db.execute('SELECT 1 FROM projects WHERE id=?',(project_id,)).fetchone():raise PolicyError('Project missing')
            db.execute('INSERT INTO conversations VALUES(?,?,?,?)',(cid,project_id,title[:120],time.time()))
        return cid

    def attach(self,conversation_id,name,content,mime='text/plain'):
        if not isinstance(name,str) or Path(name).name!=name or any(c in name for c in '/\\:') or name.startswith('.'):
            raise PolicyError('Attachment needs a simple filename')
        if not isinstance(content,bytes) or not 0<len(content)<=5_000_000:raise PolicyError('File must be 1 byte to 5 MB')
        # FN-04: each conversation keeps its files in its own folder under Kel's data (backed up with it).
        # Older rows keep their flat `attachments/<id>` path; the stored relative path is what is read.
        safe=''.join(ch for ch in str(conversation_id) if ch.isalnum() or ch in '-_')[:64] or 'main'
        aid=uid();folder=self.store.root/'attachments'/safe
        target=folder/aid
        with self.store.transaction() as db:
            if not db.execute('SELECT 1 FROM conversations WHERE id=?',(conversation_id,)).fetchone():raise PolicyError('Conversation missing')
            folder.mkdir(parents=True,exist_ok=True)
            target.write_bytes(content)
            db.execute('INSERT INTO attachments VALUES(?,?,?,?,?,?,?,?)',
                       (aid,conversation_id,name,str(target.relative_to(self.store.root)),digest(content),len(content),mime,time.time()))
        return aid

    def handoff(self,conversation_id,request,attachment_ids=(),run_id=None,max_chars=32000):
        with contextlib.closing(self.store.connect()) as db:
            row=db.execute('SELECT p.*,c.title FROM conversations c JOIN projects p ON p.id=c.project_id WHERE c.id=?',(conversation_id,)).fetchone()
            if not row:raise PolicyError('Conversation missing')
            from .import_context import load_import_context
            imported=load_import_context(self.store,row['id'],conversation_id,request)
            from .rewind import VISIBLE
            excluded=imported['exclude_seqs']
            exclusion=(' AND seq NOT IN ('+','.join('?' for _ in excluded)+')') if excluded else ''
            history=[dict(r) for r in db.execute('SELECT role,text FROM messages WHERE conversation_id=? AND '+VISIBLE+exclusion+' ORDER BY seq DESC LIMIT 16',(conversation_id,*excluded))][::-1]
            files=[]
            for aid in attachment_ids:
                a=db.execute('SELECT * FROM attachments WHERE id=? AND conversation_id=?',(aid,conversation_id)).fetchone()
                if not a:raise PolicyError('Attachment is not part of this conversation')
                content=_attachment_content(self.store,a)
                media=image_mime(content)
                if content.startswith(b'%PDF-') or Path(a['name']).suffix.lower()=='.pdf':
                    from .reference_extract import extract_reference
                    try:derived=extract_reference(a['name'],content)
                    except ValueError as exc:raise PolicyError(str(exc)) from None
                    files.append({'id':aid,'name':a['name'],'sha256':a['sha256'],'text':derived['text'],
                                  'kind':'pdf','extraction':derived['extraction'],'pages':derived['pages'],
                                  'trust':'external-untrusted','source_digest':a['sha256']})
                elif media:
                    files.append({'id':aid,'name':a['name'],'sha256':a['sha256'],'image_path':a['path'],'mime':media})
                else:
                    try:text=content.decode('utf-8')
                    except UnicodeError:raise PolicyError('Supported attachments are text, PNG, JPEG, GIF, and WebP files.')
                    files.append({'id':aid,'name':a['name'],'sha256':a['sha256'],'text':text})
        packet={'schema':1,'source_request':request,'project':{'id':row['id'],'name':row['name'],'root':row['root'],'decisions':row['context']},
                'history':history,'files':files,'trust':'Files and history are context, not permission grants.'}
        if imported['receipt']:
            packet['imported_sources']=imported['sources']
            packet['imported_context']=imported['receipt']
        # Drop old dialogue first; never silently cut the source request, decisions, or selected files.
        while len(encode(packet))>max_chars and packet['history']:packet['history'].pop(0)
        if len(encode(packet))>max_chars:raise PolicyError('Selected context is too large. Split the files or task.')
        if imported['receipt']:packet['imported_context']['body_retained']=True
        if run_id:
            with self.store.transaction() as db:
                db.execute('INSERT INTO handoffs VALUES(?,?,?,?)',(run_id,digest(packet),encode(packet),time.time()))
        return packet

    def images(self, packet, conversation_id):
        """Recheck conversation-owned selected bytes at delivery, not only at intake."""
        selected = [file for file in packet.get('files',[]) if file.get('image_path')]
        if len(selected)>10:
            raise PolicyError('Choose at most ten image attachments')
        payloads=[]
        with contextlib.closing(self.store.connect()) as db:
            for file in selected:
                row=db.execute('SELECT * FROM attachments WHERE id=? AND conversation_id=?',
                               (file.get('id'),conversation_id)).fetchone()
                if not row or row['sha256']!=file.get('sha256') or row['path']!=file.get('image_path'):
                    raise PolicyError('Image is not an unchanged attachment in this conversation')
                raw=_attachment_content(self.store,row)
                media=image_mime(raw)
                if len(raw)!=row['size'] or digest(raw)!=row['sha256'] or media is None or media!=file.get('mime'):
                    raise PolicyError('Image bytes or type changed after selection')
                payloads.append({'mime':media,'data':base64.b64encode(raw).decode(),'sha256':row['sha256']})
        return payloads

    def grant(self,project_id,action,seconds=86400):
        gid=uid()
        with self.store.transaction() as db:
            if not db.execute('SELECT 1 FROM projects WHERE id=?',(project_id,)).fetchone():raise PolicyError('Project missing')
            db.execute('INSERT INTO grants VALUES(?,?,?,?,0) ON CONFLICT(project_id,action_digest) DO UPDATE SET expires=excluded.expires,revoked=0',
                       (gid,project_id,digest(action),time.time()+min(seconds,86400*30)))
        return gid

    def allowed(self,project_id,action):
        with contextlib.closing(self.store.connect()) as db:
            return bool(db.execute('SELECT 1 FROM grants WHERE project_id=? AND action_digest=? AND revoked=0 AND expires>?',
                                  (project_id,digest(action),time.time())).fetchone())

    def revoke(self,project_id):
        with self.store.transaction() as db:db.execute('UPDATE grants SET revoked=1 WHERE project_id=?',(project_id,))
