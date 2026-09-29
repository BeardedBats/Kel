"""One search across the user's own content: chats, transcripts and vetting topics/specs.

Plain human queries and partial matches; snippets instead of raw rows. Work results, artifacts and
knowledge stay on their own surfaces for now — this is the highest-value core of a unified search
and the architecture the rest can extend.
"""
import contextlib
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

    def run(self, query, limit=6):
        needle = (query or '').strip()
        if len(needle) < 2 or len(needle) > 120 or not re.search(r'\w', needle):
            return {'query': needle, 'transcripts': [], 'vetting': [], 'conversations': []}
        pattern = _like(needle)
        results = {'query': needle, 'transcripts': [], 'vetting': [], 'conversations': []}
        with contextlib.closing(self.store.connect()) as db:
            try:
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
                for row in db.execute(
                        "SELECT id, topic, state, conversation_id FROM vetting_sessions WHERE topic LIKE ? ESCAPE '\\' "
                        'ORDER BY updated DESC LIMIT ?', (pattern, limit)):
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
                            "WHERE q.prompt LIKE ? ESCAPE '\\' LIMIT ?", (pattern, limit)):
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
                        "SELECT id, title FROM conversations WHERE title LIKE ? ESCAPE '\\' "
                        'ORDER BY created DESC LIMIT ?', (pattern, limit)):
                    results['conversations'].append({
                        'id': row['id'], 'title': row['title'] or 'Conversation', 'snippet': '',
                    })
                if len(results['conversations']) < limit:
                    # D-75.2: messages an edit or a regenerate rewound are no longer part of the chat.
                    rewound = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                                         "AND name='rewound_messages'").fetchone()
                    visible = 'AND seq NOT IN (SELECT seq FROM rewound_messages) ' if rewound else ''
                    for row in db.execute(
                            "SELECT conversation_id AS id, text FROM messages "
                            "WHERE text LIKE ? ESCAPE '\\' " + visible + 'ORDER BY seq DESC LIMIT ?', (pattern, limit)):
                        if all(item['id'] != row['id'] for item in results['conversations']):
                            results['conversations'].append({
                                'id': row['id'],
                                'title': _snippet(row['text'] or '', needle, 60) or 'Conversation',
                                'snippet': _snippet(row['text'] or '', needle),
                            })
            except Exception:
                pass
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
