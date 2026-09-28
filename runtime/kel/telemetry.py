"""Measured routing inputs. Missing prices and quality evidence remain unknown."""
import json
import time
from .appserver import CodexConnection
from .core import encode


def refresh_codex(store, connection_factory=None):
    """Read Codex's plan limits (`account/rateLimits/read`) into every Codex adapter's state through
    `kel.quota` (windows, pace samples, reset-aware percent left). Plans whose windows have reset
    since they were last seen are refreshed first, so a used-up plan never stays used up."""
    from .quota import expire, from_codex_read, observe
    try:
        expire(store)
    except Exception:
        pass
    folder = store.root/'telemetry'; folder.mkdir(exist_ok=True)
    connection = (connection_factory or CodexConnection)(folder, folder/'logs')
    try:
        response = connection.quota()
    finally:
        connection.close()
    snapshot = from_codex_read(response)
    if not snapshot:
        return None
    remaining = observe(store, snapshot)
    bucket = (response.get('rateLimitsByLimitId') or {}).get('codex') or response.get('rateLimits') or {}
    if bucket.get('planType') not in (None, 'free') and remaining and remaining > 0:
        with store.transaction() as db:
            for provider in ('codex', 'codex-code'):
                old = db.execute('SELECT data FROM providers WHERE id=?', (provider,)).fetchone()
                state = json.loads(old['data']) if old else {'failures': 0, 'circuit_until': 0}
                state.update(cost=0, cost_basis='subscription capacity; no credit purchase', cost_is_estimate=False)
                db.execute('INSERT INTO providers VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                           (provider, encode(state)))
    return {'remaining': remaining, 'windows': snapshot['windows'], 'observed_at': time.time()}
