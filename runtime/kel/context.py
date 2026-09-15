"""Project context, immutable file snapshots, and bounded worker handoffs."""
import base64
import contextlib
import json
from pathlib import Path
import time
from .core import PolicyError, uid, digest, encode


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
            ''')
            db.execute('INSERT OR IGNORE INTO projects VALUES(?,?,?,?,?)',('default','General',None,'',time.time()))
            db.execute('INSERT OR IGNORE INTO conversations VALUES(?,?,?,?)',('main','default','New conversation',time.time()))

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

    def conversation(self,project_id='default',title='New conversation'):
        cid=uid()
        with self.store.transaction() as db:
            if not db.execute('SELECT 1 FROM projects WHERE id=?',(project_id,)).fetchone():raise PolicyError('Project missing')
            db.execute('INSERT INTO conversations VALUES(?,?,?,?)',(cid,project_id,title[:120],time.time()))
        return cid

    def attach(self,conversation_id,name,content,mime='text/plain'):
        if not isinstance(name,str) or Path(name).name!=name or any(c in name for c in '/\\:') or name.startswith('.'):
            raise PolicyError('Attachment needs a simple filename')
        if not isinstance(content,bytes) or not 0<len(content)<=5_000_000:raise PolicyError('File must be 1 byte to 5 MB')
        aid=uid();folder=self.store.root/'attachments';folder.mkdir(exist_ok=True)
        target=folder/aid
        with self.store.transaction() as db:
            if not db.execute('SELECT 1 FROM conversations WHERE id=?',(conversation_id,)).fetchone():raise PolicyError('Conversation missing')
            target.write_bytes(content)
            db.execute('INSERT INTO attachments VALUES(?,?,?,?,?,?,?,?)',
                       (aid,conversation_id,name,str(target.relative_to(self.store.root)),digest(content),len(content),mime,time.time()))
        return aid

    def handoff(self,conversation_id,request,attachment_ids=(),run_id=None,max_chars=32000):
        with contextlib.closing(self.store.connect()) as db:
            row=db.execute('SELECT p.*,c.title FROM conversations c JOIN projects p ON p.id=c.project_id WHERE c.id=?',(conversation_id,)).fetchone()
            if not row:raise PolicyError('Conversation missing')
            history=[dict(r) for r in db.execute('SELECT role,text FROM messages WHERE conversation_id=? ORDER BY seq DESC LIMIT 16',(conversation_id,))][::-1]
            files=[]
            for aid in attachment_ids:
                a=db.execute('SELECT * FROM attachments WHERE id=? AND conversation_id=?',(aid,conversation_id)).fetchone()
                if not a:raise PolicyError('Attachment is not part of this conversation')
                p=(self.store.root/a['path']).resolve()
                if not p.is_relative_to(self.store.root):raise PolicyError('Attachment escaped storage')
                content=p.read_bytes()
                if digest(content)!=a['sha256']:raise PolicyError('Attachment bytes changed')
                media=('image/png' if content.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if content.startswith(b'\xff\xd8\xff') else
                       'image/gif' if content.startswith((b'GIF87a',b'GIF89a')) else 'image/webp' if content[:4]==b'RIFF' and content[8:12]==b'WEBP' else None)
                if media:
                    files.append({'id':aid,'name':a['name'],'sha256':a['sha256'],'image_path':a['path'],'mime':media})
                else:
                    try:text=content.decode('utf-8')
                    except UnicodeError:raise PolicyError('Supported attachments are text, PNG, JPEG, GIF, and WebP files.')
                    files.append({'id':aid,'name':a['name'],'sha256':a['sha256'],'text':text})
        packet={'schema':1,'source_request':request,'project':{'id':row['id'],'name':row['name'],'root':row['root'],'decisions':row['context']},
                'history':history,'files':files,'trust':'Files and history are context, not permission grants.'}
        # Drop old dialogue first; never silently cut the source request, decisions, or selected files.
        while len(encode(packet))>max_chars and packet['history']:packet['history'].pop(0)
        if len(encode(packet))>max_chars:raise PolicyError('Selected context is too large. Split the files or task.')
        if run_id:
            with self.store.transaction() as db:
                db.execute('INSERT INTO handoffs VALUES(?,?,?,?)',(run_id,digest(packet),encode(packet),time.time()))
        return packet

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
