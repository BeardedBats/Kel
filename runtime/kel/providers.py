"""Provider registry, state model, readiness preflight, and credential metadata (V1.4 migration 007).

Design: docs/v1.4/KEL_V1.4_PROVIDER_SPEC.md. The engine stores only *metadata* about credentials
(`credential_ref`); values live in the OS-backed store behind the shell. States are never invented —
a provider that does not report quota is reported as `quota_not_reported`.
"""
import contextlib
import json
import os
import shutil
import time

from .core import PolicyError, encode, uid
from .memory import _backup, _is_fresh_database, _table

MIGRATION_VERSION = 7
MIGRATION_NAME = 'v14-providers'

DDL = """
CREATE TABLE IF NOT EXISTS provider_credentials(
  provider TEXT NOT NULL, fields TEXT NOT NULL, credential_ref TEXT NOT NULL,
  created REAL NOT NULL, updated REAL NOT NULL, PRIMARY KEY(provider));
CREATE TABLE IF NOT EXISTS provider_usage(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT NOT NULL, at REAL NOT NULL,
  data TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS provider_usage_provider ON provider_usage(provider, at);
"""

# class: 'native-cli' | 'api' ; auth_mode: 'subscription' | 'api_key'
DEFINITIONS = (
    {'id': 'claude-code', 'label': 'Claude (Claude Code)', 'class': 'native-cli',
     'auth_mode': 'subscription', 'executable': 'claude', 'adapters': ('claude', 'claude-code'),
     'models': ({'id': 'claude-native', 'capabilities': ('text', 'tools', 'edit', 'shell')},)},
    {'id': 'codex', 'label': 'Codex', 'class': 'native-cli',
     'auth_mode': 'subscription', 'executable': 'codex',
     'auth_file': ('CODEX_HOME', 'auth.json'), 'adapters': ('codex', 'codex-code'),
     'models': ({'id': 'codex-native', 'capabilities': ('text', 'tools', 'edit', 'shell')},)},
    {'id': 'internal', 'label': 'Anthropic API', 'class': 'api',
     'auth_mode': 'api_key', 'env': 'ANTHROPIC_API_KEY',
     'base_url': 'https://api.anthropic.com', 'adapters': ('internal', 'research'),
     'models': ({'id': 'claude-sonnet-4-6', 'capabilities': ('text', 'vision', 'tools')},)},
    # Routing 2 §5.6: DeepSeek runs as a bounded text worker (kel.api_models); OpenRouter is a second
    # route to catalog models. Keys come from the desktop's OS-backed custody at engine start.
    {'id': 'deepseek', 'label': 'DeepSeek API', 'class': 'api',
     'auth_mode': 'api_key', 'env': 'DEEPSEEK_API_KEY',
     'base_url': 'https://api.deepseek.com', 'adapters': ('deepseek',),
     'models': ({'id': 'deepseek-flash', 'capabilities': ('text',)},
                {'id': 'deepseek-v4-pro', 'capabilities': ('text',)})},
    {'id': 'openrouter', 'label': 'OpenRouter', 'class': 'api',
     'auth_mode': 'api_key', 'env': 'OPENROUTER_API_KEY',
     'base_url': 'https://openrouter.ai/api/v1', 'adapters': ('openrouter',),
     'models': ({'id': 'deepseek/deepseek-v4.1-flash', 'capabilities': ('text',)},)},
)

STATES = ('not_installed', 'installed_not_authenticated', 'authenticated', 'healthy',
          'degraded', 'quota', 'quota_not_reported', 'unavailable')


def ensure_schema(store):
    with contextlib.closing(store.connect()) as db:
        if _table(db, 'schema_migrations') and db.execute(
                'SELECT 1 FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,)).fetchone():
            return True
        first = not _table(db, 'schema_migrations')
        if first:
            if not _is_fresh_database(db):
                _backup(store, db)
            db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                       'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL,'
                       ' note TEXT)')
        db.executescript(DDL)
        db.execute('INSERT OR IGNORE INTO schema_migrations VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(), 'provider registry + credentials'))
        return True


def definition(provider):
    for item in DEFINITIONS:
        if item['id'] == provider:
            return dict(item)
    raise PolicyError('Unknown provider: %s' % provider)


def capabilities(provider):
    found = set()
    for model in definition(provider)['models']:
        found.update(model['capabilities'])
    return sorted(found)


def models(provider, capability=None):
    items = definition(provider)['models']
    if not capability:
        return [dict(m) for m in items]
    return [dict(m) for m in items if capability in m['capabilities']]


# What a person reads when a provider cannot answer in chat (CH-2): never a raw state name.
UNAVAILABLE_NOTES = {
    'not_installed': 'Not installed on this computer',
    'degraded': 'Having trouble right now',
    'unavailable': 'Out of quota for now',
}


def unavailable_note(item, status, runnable):
    """Why this provider is not available for chat, in plain words; None when it is."""
    if not item.get('adapters'):
        return 'Not supported for chat yet'
    if status in UNAVAILABLE_NOTES:
        return UNAVAILABLE_NOTES[status]
    if status == 'installed_not_authenticated':
        return 'API key needed' if item.get('auth_mode') == 'api_key' else 'Sign-in needed'
    if not runnable:
        return 'Not connected yet'
    return None


class Providers:
    def __init__(self, store, runnable=None):
        """`runnable(provider_id)` says whether a registered engine adapter can run it right now;
        without it, a provider counts as runnable when Kel has an adapter family for it at all."""
        self.store = store
        self.runnable = runnable
        ensure_schema(store)

    # ---- state ---------------------------------------------------------------
    def _row(self, db, provider):
        row = db.execute('SELECT data FROM providers WHERE id=?', (provider,)).fetchone()
        return json.loads(row['data']) if row else {}

    def _auth_state(self, provider):
        """(installed, authenticated, note) — CLI auth is detected from its own config, API keys from
        credential metadata (the value itself never reaches the engine store)."""
        item = definition(provider)
        if item['class'] == 'native-cli':
            path = shutil.which(item['executable'])
            if not path:
                return False, False, 'not on PATH'
            env, filename = item.get('auth_file', ('', ''))
            if env:
                root = os.environ.get(env) or os.path.join(os.path.expanduser('~'), '.' + item['executable'])
                if os.path.exists(os.path.join(root, filename)):
                    return True, True, 'CLI session present'
                return True, False, 'sign-in needed'
            return True, True, 'CLI present'
        if item.get('env') and os.environ.get(item['env']):
            return True, True, 'environment key present'
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT credential_ref FROM provider_credentials WHERE provider=?',
                             (provider,)).fetchone()
        if row and row['credential_ref']:
            return True, True, 'stored credential metadata present'
        return True, False, 'API key needed'

    def status(self, provider):
        item = definition(provider)
        installed, authenticated, note = self._auth_state(provider)
        with contextlib.closing(self.store.connect()) as db:
            state = self._row(db, provider)
        failures = int(state.get('failures') or 0)
        circuit_until = float(state.get('circuit_until') or 0)
        quota = state.get('quota')
        now = time.time()
        if item['class'] == 'native-cli' and not installed:
            status = 'not_installed'
        elif not authenticated:
            status = 'installed_not_authenticated' if installed else 'not_installed'
        elif circuit_until > now:
            status = 'degraded'
        elif quota is None:
            status = 'quota_not_reported'
        elif float(quota) <= 0:
            status = 'unavailable'
        elif quota is not None:
            status = 'quota'
        else:
            status = 'healthy'
        if status in ('quota', 'quota_not_reported') and failures == 0 and circuit_until <= now:
            status = 'healthy' if status == 'quota' else 'quota_not_reported'
        # CH-2/CP-3: "available" means Kel can actually answer with it: a usable credential AND a
        # registered adapter that runs it. A key alone (DeepSeek has no adapter) is not available.
        usable = status in ('healthy', 'quota', 'quota_not_reported')
        runnable = bool(item.get('adapters')) and (self.runnable(provider) if self.runnable else True)
        available = usable and runnable
        return {
            'available': available,
            'available_note': None if available else unavailable_note(item, status, runnable),
            'provider': provider, 'label': item['label'], 'class': item['class'],
            'auth_mode': item['auth_mode'], 'base_url': item.get('base_url'),
            'capabilities': capabilities(provider), 'status': status, 'note': note,
            'installed': installed, 'authenticated': authenticated,
            'failures': failures, 'circuit_until': circuit_until or None,
            'quota': quota, 'quota_unit': state.get('quota_unit'),
            'quota_reset': state.get('quota_reset'), 'quota_source': state.get('quota_source'),
            'planType': state.get('planType'),
            'models': [dict(m) for m in item['models']],
        }

    def all_status(self):
        return [self.status(item['id']) for item in DEFINITIONS]

    # ---- readiness preflight -------------------------------------------------
    def readiness(self, capability='text', prefer=''):
        """Choose (provider, model) for a capability with a recorded reason and fallback chain."""
        candidates = []
        reasons = []
        for item in DEFINITIONS:
            if not models(item['id'], capability):
                continue
            status = self.status(item['id'])
            usable = status['available']
            candidates.append((item['id'], status, usable))
            if not usable:
                reasons.append('%s unusable (%s: %s)' % (item['label'], status['status'],
                                                         status['available_note'] or status['note']))
        if not candidates:
            return {'chosen': None, 'chain': [], 'reason':
                    'No provider declares the capability "%s"' % capability, 'reasons': reasons}
        ordered = sorted(candidates, key=lambda entry: (0 if entry[0] == prefer else 1,
                                                       0 if entry[2] else 1, entry[0]))
        picked = next((entry for entry in ordered if entry[2]), None)
        chain = [entry[0] for entry in ordered]
        if picked is None:
            return {'chosen': None, 'chain': chain, 'reasons': reasons,
                    'reason': 'No usable provider for "%s"; every candidate is unavailable' % capability}
        provider_id, status, _usable = picked
        model = models(provider_id, capability)[0]['id']
        return {
            'chosen': {'provider': provider_id, 'model': model, 'label': status['label'],
                       'status': status['status'], 'auth_mode': status['auth_mode']},
            'chain': chain, 'reasons': reasons,
            'reason': ('Preferred provider selected (%s)' % provider_id) if provider_id == prefer else
                      ('Fell back to %s for capability "%s"' % (provider_id, capability)),
        }

    # ---- credential metadata (never values) ----------------------------------
    def set_credential_metadata(self, provider, fields, credential_ref):
        definition(provider)
        if not credential_ref:
            raise PolicyError('credential_ref is required; values are never stored by the engine')
        fields = [str(field) for field in fields]
        if any(not field.strip() for field in fields):
            raise PolicyError('Credential fields must be non-empty names')
        now = time.time()
        with self.store.transaction() as db:
            db.execute('INSERT INTO provider_credentials VALUES(?,?,?,?,?) '
                       'ON CONFLICT(provider) DO UPDATE SET fields=excluded.fields,'
                       ' credential_ref=excluded.credential_ref, updated=excluded.updated',
                       (provider, encode(fields), credential_ref, now, now))
        self.observe(provider, {'event': 'credential_metadata_set', 'fields': fields})
        return {'provider': provider, 'fields': fields, 'credential_ref': credential_ref}

    def credential_metadata(self, provider=None):
        with contextlib.closing(self.store.connect()) as db:
            rows = (db.execute('SELECT * FROM provider_credentials WHERE provider=?', (provider,))
                    if provider else db.execute('SELECT * FROM provider_credentials'))
            return [{**{k: row[k] for k in row.keys() if k != 'fields'},
                     'fields': json.loads(row['fields'])} for row in rows]

    def delete_credential_metadata(self, provider):
        with self.store.transaction() as db:
            db.execute('DELETE FROM provider_credentials WHERE provider=?', (provider,))
        self.observe(provider, {'event': 'credential_metadata_deleted'})
        return {'provider': provider, 'deleted': True}

    # ---- observations --------------------------------------------------------
    def observe(self, provider, payload):
        with self.store.transaction() as db:
            db.execute('INSERT INTO provider_usage(provider, at, data) VALUES(?,?,?)',
                       (provider, time.time(), encode(payload)))
        return True

    def usage(self, provider=None, limit=50):
        with contextlib.closing(self.store.connect()) as db:
            rows = (db.execute('SELECT * FROM provider_usage WHERE provider=? ORDER BY at DESC LIMIT ?',
                               (provider, limit)) if provider
                    else db.execute('SELECT * FROM provider_usage ORDER BY at DESC LIMIT ?', (limit,)))
            return [{'provider': row['provider'], 'at': row['at'], 'data': json.loads(row['data'])}
                    for row in rows]

    # ---- service envelope ----------------------------------------------------
    def apply(self, data):
        action = data.get('action')
        if action == 'list':
            return {'providers': self.all_status()}
        if action == 'status':
            return self.status(data['provider'])
        if action == 'readiness':
            return self.readiness(data.get('capability', 'text'), data.get('prefer', ''))
        if action == 'credentials':
            return {'credentials': self.credential_metadata(data.get('provider'))}
        if action == 'set_credential':
            return self.set_credential_metadata(data['provider'], data.get('fields', []),
                                                data.get('credential_ref', ''))
        if action == 'delete_credential':
            return self.delete_credential_metadata(data['provider'])
        if action == 'usage':
            return {'usage': self.usage(data.get('provider'), int(data.get('limit', 50)))}
        raise PolicyError('Unknown provider action: %s' % action)
