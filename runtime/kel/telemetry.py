"""Measured routing inputs. Missing prices and quality evidence remain unknown."""
import contextlib
import time
from .appserver import CodexConnection
from .core import encode


def refresh_codex(store):
    folder=store.root/'telemetry';folder.mkdir(exist_ok=True)
    connection=CodexConnection(folder,folder/'logs')
    try:response=connection.quota()
    finally:connection.close()
    bucket=response.get('rateLimitsByLimitId',{}).get('codex') or response.get('rateLimits')
    if not bucket:return None
    windows=[bucket[k] for k in ('primary','secondary') if bucket.get(k) is not None]
    remaining=min((max(0,100-w['usedPercent']) for w in windows),default=None)
    resets=[w.get('resetsAt') for w in windows if w.get('usedPercent',0)>=100 and w.get('resetsAt')]
    with store.transaction() as db:
        import json
        for provider in ('codex','codex-code'):
            old=db.execute('SELECT data FROM providers WHERE id=?',(provider,)).fetchone()
            state=json.loads(old['data']) if old else {'failures':0,'circuit_until':0}
            state.update(quota=remaining,quota_unit='percent_remaining',quota_observed_at=time.time(),
                         quota_reset=min(resets) if resets else None,quota_source='account/rateLimits/read')
            if bucket.get('planType') not in (None,'free') and remaining and remaining>0:
                state.update(cost=0,cost_basis='subscription capacity; no credit purchase',cost_is_estimate=False)
            db.execute('INSERT INTO providers VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(provider,encode(state)))
    return {'remaining':remaining,'windows':windows,'observed_at':time.time()}
