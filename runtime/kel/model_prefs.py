"""Default Kel model + per-conversation override.

The choice is a soft preference on top of Kel's routing: a preferred provider is tried first and
routing keeps every existing fallback; Auto keeps the original deterministic order. Provider
machinery stays out of the simple UI — the service layer only exposes plain labels, availability
and the stored choice.
"""
import contextlib
import time

from .core import PolicyError

MIGRATION_VERSION = 13
MIGRATION_NAME = 'v15-model-prefs'

DDL = """
CREATE TABLE IF NOT EXISTS model_prefs(
    scope TEXT PRIMARY KEY,
    provider TEXT,
    model TEXT,
    updated REAL NOT NULL);
"""

# Plain display names only. Raw provider/model ids never reach the simple UI.
PROVIDER_LABELS = {
    'claude-code': 'Claude',
    'codex': 'Codex',
    'internal': 'Anthropic',
    'deepseek': 'DeepSeek',
}
MODEL_LABELS = {
    'claude-native': 'Claude (built-in)',
    'codex-native': 'Codex (built-in)',
    'claude-sonnet-4-6': 'Claude Sonnet 4.6',
    'deepseek-chat': 'DeepSeek Chat',
    'deepseek-reasoner': 'DeepSeek Reasoner',
}


def ensure_schema(store):
    # Plain autocommit connection: executescript performs an implicit COMMIT and must not sit
    # inside store.transaction(). schema_migrations is created if an older store lacks it.
    with contextlib.closing(store.connect()) as db:
        db.executescript(
            'CREATE TABLE IF NOT EXISTS schema_migrations('
            'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT);'
            + DDL)
        if db.execute('SELECT 1 FROM schema_migrations WHERE version=?',
                      (MIGRATION_VERSION,)).fetchone():
            return False
        db.execute('INSERT INTO schema_migrations(version,name,applied,note) VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                    'Default Kel model and per-conversation overrides'))
    return True


class ModelPrefs:
    def __init__(self, store):
        self.store = store
        ensure_schema(store)

    def _row(self, scope):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT provider, model FROM model_prefs WHERE scope=?',
                             (scope,)).fetchone()
        return dict(row) if row else None

    def default(self):
        return self._row('default')

    def conversation(self, conversation_id):
        if not conversation_id:
            return None
        return self._row('conversation:' + conversation_id)

    def snapshot(self, conversation_id=None):
        return {'default': self.default(), 'conversation': self.conversation(conversation_id)}

    @staticmethod
    def _validate(provider, model):
        from .providers import DEFINITIONS
        if provider:
            item = next((entry for entry in DEFINITIONS if entry['id'] == provider), None)
            if item is None:
                raise PolicyError('That model choice is not available in this version of Kel.')
            ids = {entry['id'] for entry in item.get('models', ())}
            if model and model not in ids:
                raise PolicyError('That model choice is not available for %s.'
                                  % PROVIDER_LABELS.get(provider, provider))

    def set(self, scope, provider, model):
        if not provider:
            return self.clear(scope)
        self._validate(provider, model)
        with contextlib.closing(self.store.connect()) as db:
            db.execute('INSERT INTO model_prefs VALUES(?,?,?,?) ON CONFLICT(scope) DO UPDATE '
                       'SET provider=excluded.provider, model=excluded.model, updated=excluded.updated',
                       (scope, provider, model or None, time.time()))

    def clear(self, scope):
        with contextlib.closing(self.store.connect()) as db:
            db.execute('DELETE FROM model_prefs WHERE scope=?', (scope,))

    def set_default(self, provider, model):
        self.set('default', provider, model)

    def set_conversation(self, conversation_id, provider, model):
        if not conversation_id:
            raise PolicyError('Open a conversation before choosing its model.')
        self.set('conversation:' + conversation_id, provider, model)

    def clear_conversation(self, conversation_id):
        if conversation_id:
            self.clear('conversation:' + conversation_id)

    # -- execution-side resolution -------------------------------------------------------------
    @staticmethod
    def resolve_for_job(store, job_id):
        """(provider, model) the execution should favour for this job, or None for Auto."""
        cid = None
        try:
            import contextlib as _contextlib
            with _contextlib.closing(store.connect()) as db:
                row = db.execute('SELECT conversation_id FROM submissions WHERE job_id=?',
                                 (job_id,)).fetchone()
                cid = row['conversation_id'] if row else None
        except Exception:
            cid = None
        prefs = ModelPrefs(store)
        snap = prefs.snapshot(cid)
        return snap['conversation'] or snap['default']


def provider_label(provider_id):
    return PROVIDER_LABELS.get(provider_id, provider_id)


def model_label(model_id):
    if not model_id:
        return None
    return MODEL_LABELS.get(model_id, model_id)
