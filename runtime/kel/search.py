"""Scoped search over durable records, with exact output-version references."""
import contextlib
import json
import re

from .core import PolicyError


def _like(needle):
    return '%' + needle.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'


def _snippet(text, needle, width=90):
    if not text:
        return ''
    lowered = text.lower()
    at = lowered.find(needle.lower())
    if at < 0:
        return text[:width].strip()
    start = max(0, at - width // 2)
    end = min(len(text), at + len(needle) + width // 2)
    chunk = text[start:end].replace('\n', ' ').strip()
    return ('…' if start > 0 else '') + chunk + ('…' if end < len(text) else '')


class Search:
    def __init__(self, store):
        self.store = store

    def run(self, query, limit=6, project_id=None):
        needle = (query or '').strip()
        limit = max(1, min(30, int(limit or 6)))
        results = {key: [] for key in ('transcripts', 'vetting', 'conversations', 'work', 'artifacts', 'knowledge', 'imports')}
        results.update(query=needle, project_id=project_id, omissions=[])
        if len(needle) < 2 or len(needle) > 120 or not re.search(r'\w', needle):
            return results
        pattern = _like(needle)
        with contextlib.closing(self.store.connect()) as db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            conv_map = {r['id']: r['project_id'] for r in db.execute('SELECT id,project_id FROM conversations')} if 'conversations' in tables else {}
            excluded = set()
            if 'project_meta' in tables:
                excluded = {r[0] for r in db.execute("SELECT project_id FROM project_meta WHERE archived IS NOT NULL OR kind='system'")}
            gone = set()
            if 'chat_state' in tables:
                gone = {r[0] for r in db.execute('SELECT conversation_id FROM chat_state WHERE deleted_at IS NOT NULL')}
            if project_id and (project_id in excluded or ('projects' in tables and not db.execute('SELECT 1 FROM projects WHERE id=?', (project_id,)).fetchone())):
                return results
            allowed = [cid for cid, pid in conv_map.items() if pid not in excluded and cid not in gone and (project_id is None or pid == project_id)]
            def conv_filter(column):
                # IDs are values, never interpolated SQL. Missing tables retain old isolated fixtures.
                if project_id is None:
                    denied = sorted(gone | {cid for cid, pid in conv_map.items() if pid in excluded})
                    if not denied:
                        return '', []
                    return ' AND ' + column + ' NOT IN (' + ','.join('?' for _ in denied) + ') ', denied
                return ' AND ' + column + ' IN (' + ','.join('?' for _ in allowed) + ') ', allowed
            scope, scope_args = conv_filter('id')
            try:
                if project_id is not None:
                    results['omissions'].append({'kind': 'transcripts', 'reason': 'Transcripts without a Project association are excluded'})
                    raise LookupError('Unscoped transcripts cannot be attributed to this Project')
                for row in db.execute(
                        "SELECT id, name, text FROM transcripts "
                        "WHERE name LIKE ? ESCAPE '\\' OR text LIKE ? ESCAPE '\\' "
                        'ORDER BY updated DESC LIMIT ?', (pattern, pattern, limit)):
                    results['transcripts'].append({
                        'id': row['id'],
                        'title': row['name'] or 'Transcript',
                        'snippet': _snippet(row['text'] or '', needle),
                    })
            except Exception:
                pass
            try:
                vscope, vargs = conv_filter('conversation_id')
                for row in db.execute(
                        "SELECT id, topic, state, conversation_id FROM vetting_sessions WHERE topic LIKE ? ESCAPE '\\' " + vscope +
                        'ORDER BY updated DESC LIMIT ?', (pattern, *vargs, limit)):
                    results['vetting'].append({
                        'id': row['id'],
                        'title': row['topic'],
                        'snippet': 'Design vetting session · ' + str(row['state'] or '').lower(),
                        'conversation_id': row['conversation_id'],  # the chat it belongs to (palette)
                    })
                if len(results['vetting']) < limit:
                    for row in db.execute(
                            "SELECT distinct s.id, s.topic, s.conversation_id FROM vetting_sessions s "
                            'JOIN vetting_questions q ON q.session_id = s.id '
                            "WHERE q.prompt LIKE ? ESCAPE '\\' " + vscope.replace('conversation_id', 's.conversation_id') + ' LIMIT ?', (pattern, *vargs, limit)):
                        if all(item['id'] != row['id'] for item in results['vetting']):
                            results['vetting'].append({
                                'id': row['id'], 'title': row['topic'],
                                'snippet': 'Matches a question in this session',
                                'conversation_id': row['conversation_id'],
                            })
            except Exception:
                pass
            try:
                for row in db.execute(
                        "SELECT id, title FROM conversations WHERE title LIKE ? ESCAPE '\\' " + scope +
                        'ORDER BY created DESC LIMIT ?', (pattern, *scope_args, limit)):
                    results['conversations'].append({
                        'id': row['id'], 'title': row['title'] or 'Conversation', 'snippet': '',
                    })
                if len(results['conversations']) < limit:
                    # D-75.2: messages an edit or a regenerate rewound are no longer part of the chat.
                    rewound = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                                         "AND name='rewound_messages'").fetchone()
                    visible = 'AND seq NOT IN (SELECT seq FROM rewound_messages) ' if rewound else ''
                    mscope, margs = conv_filter('conversation_id')
                    for row in db.execute(
                            "SELECT conversation_id AS id, text FROM messages "
                            "WHERE text LIKE ? ESCAPE '\\' " + visible + mscope + 'ORDER BY seq DESC LIMIT ?', (pattern, *margs, limit)):
                        if all(item['id'] != row['id'] for item in results['conversations']):
                            results['conversations'].append({
                                'id': row['id'],
                                'title': _snippet(row['text'] or '', needle, 60) or 'Conversation',
                                'snippet': _snippet(row['text'] or '', needle),
                            })
            except Exception:
                pass
            # Durable outputs are searched without reading arbitrary paths or importing file text.
            # Artifact contents use Store's containment and integrity checks below.
            def permitted(pid, cid=None):
                return pid not in excluded and (project_id is None or pid == project_id) and (not cid or cid not in gone)
            if 'jobs' in tables:
                for row in db.execute('SELECT id,data FROM jobs ORDER BY rowid DESC'):
                    job = json.loads(row['data'])
                    cid = job.get('conversation')
                    contract = job.get('contract') or {}
                    pid = conv_map.get(cid) or contract.get('project_id')
                    if not permitted(pid, cid):
                        continue
                    text = str(contract.get('request') or '')
                    if needle.lower() in text.lower():
                        results['work'].append({'id': row['id'], 'project_id': pid, 'conversation_id': cid,
                                                'title': _snippet(text, needle, 60), 'snippet': _snippet(text, needle),
                                                'state': job.get('state'), 'link': {'kind': 'work', 'id': row['id'], 'conversation_id': cid}})
                    if len(results['work']) >= limit:
                        break
            if 'artifact_lineage' in tables:
                count = 0
                for row in db.execute('SELECT * FROM artifact_lineage ORDER BY created DESC'):
                    if not permitted(row['project_id'], row['conversation_id']):
                        continue
                    count += 1
                    if count > 300:
                        results['omissions'].append({'kind': 'artifacts', 'reason': 'Only the latest 300 eligible output versions were scanned'})
                        break
                    if row['bytes'] is not None and row['bytes'] > 1000000:
                        continue
                    try:
                        path = (self.store.root / row['relpath']).resolve()
                        if not path.is_relative_to((self.store.root / 'artifacts').resolve()) or path.stat().st_size > 1000000:
                            continue
                        text = self.store.artifact_text({'path': row['relpath'], 'sha256': row['sha256']})
                    except (OSError, PolicyError, UnicodeError):
                        continue
                    if needle.lower() not in (row['filename'] + '\n' + text).lower():
                        continue
                    results['artifacts'].append({'id': row['id'], 'project_id': row['project_id'],
                        'conversation_id': row['conversation_id'], 'job_id': row['job_id'],
                        'title': row['filename'], 'snippet': _snippet(text, needle), 'sha256': row['sha256'],
                        'superseded_by': row['superseded_by'], 'link': {'kind': 'artifact', 'id': row['id'], 'job_id': row['job_id']}})
                    if len(results['artifacts']) >= limit:
                        break
            if 'memories' in tables:
                for row in db.execute("SELECT id,project_id,topic,summary,value,trust FROM memories WHERE status='active' "
                                      "AND (topic LIKE ? ESCAPE '\\' OR summary LIKE ? ESCAPE '\\' OR value LIKE ? ESCAPE '\\') ORDER BY updated DESC",
                                      (pattern, pattern, pattern)):
                    if not permitted(row['project_id']):
                        continue
                    results['knowledge'].append({'id': row['id'], 'project_id': row['project_id'], 'title': row['topic'],
                        'snippet': _snippet(row['summary'] or row['value'], needle), 'trust': row['trust'],
                        'link': {'kind': 'knowledge', 'id': row['id'], 'project_id': row['project_id']}})
                    if len(results['knowledge']) >= limit:
                        break
            if 'work_imports' in tables:
                for row in db.execute('SELECT * FROM work_imports ORDER BY created DESC'):
                    if not permitted(row['project_id'], row['conversation_id']):
                        continue
                    data = json.loads(row['data'])
                    text = '\n'.join(m['text'] for m in data['messages'])
                    if needle.lower() in (data['title'] + '\n' + text).lower():
                        results['imports'].append({'id': row['id'], 'title': data['title'], 'project_id': row['project_id'],
                            'conversation_id': row['conversation_id'], 'source': row['source'], 'snippet': _snippet(text, needle),
                            'link': {'kind': 'conversation', 'id': row['conversation_id']}})
                    if len(results['imports']) >= limit:
                        break
            try:
                # CP-10a stage 3 (D-77, B-10): a chat the person deleted is not found any more.
                from .chat_state import read_states
                gone = {s['conversation_id'] for s in read_states(db).values()
                        if s.get('deleted_at') and s.get('conversation_id')}
                if gone:
                    results['conversations'] = [c for c in results['conversations'] if c['id'] not in gone]
            except Exception:
                pass
        return results
