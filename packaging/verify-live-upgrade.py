"""G11/G13 live migration probe: open a COPY of a real kel-desktop data root with V1.5 code.

Never mutates the original: everything happens under a scratch copy. The default source is this
machine's real `kel-desktop/work` root (a V1.3-origin store that was upgraded through V1.4:
migrations 1-4, 6-9). The probe starts the V1.5 Service exactly like the desktop shell does,
then reports schema_migrations and row counts before/after, checks SQLite integrity, and records
one authorization decision through the new boundary to prove migration 010's table is live on
upgraded data.

Usage: python packaging/verify-live-upgrade.py [source-data-dir] [scratch-dir]
"""
import shutil
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'runtime'))

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / 'AppData/Roaming/kel-desktop/work'
DST = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / 'AppData/Local/Temp/kel-mig'

TABLES = ('jobs', 'runs', 'memories', 'providers', 'capability_leases', 'guardrail_decisions',
          'recipes', 'roles', 'approvals', 'grants', 'memory_records')


def report(db_path, label):
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    mig = [(r['version'], r['name']) for r in
           con.execute('select version, name from schema_migrations order by version')]
    tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    counts = {}
    for t in TABLES:
        if t in tables:
            counts[t] = con.execute('select count(*) from %s' % t).fetchone()[0]
    integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
    con.close()
    print(label, 'migrations:', mig)
    print(label, 'counts:', dict(sorted(counts.items())))
    print(label, 'integrity:', integrity)
    return counts


def main():
    if not SRC.exists():
        print('source data dir not found:', SRC)
        print('RESULT: REVIEW')
        return
    if DST.exists():
        shutil.rmtree(DST)
    (DST / 'pre').mkdir(parents=True)
    for f in SRC.glob('kel.sqlite3*'):
        shutil.copy2(f, DST / 'pre' / f.name)
    print('copied:', sorted(p.name for p in (DST / 'pre').iterdir()))
    pre = report(DST / 'pre' / 'kel.sqlite3', 'PRE ')

    shutil.copytree(DST / 'pre', DST / 'post', dirs_exist_ok=True)

    # The real upgrade path: the desktop shell starts the V1.5 Service on the data root, and each
    # module's ensure_schema runs there (migration 010 lives with the authorization module).
    from kel.service import Service  # noqa: E402 - imported after sys.path setup
    service = Service(DST / 'post')
    service.shutdown()

    post = report(DST / 'post' / 'kel.sqlite3', 'POST')

    # Prove the new boundary works on upgraded data: one recorded decision, policy-stamped.
    from kel.authorize import Authorizer  # noqa: E402
    from kel.core import Store  # noqa: E402
    store = Store(DST / 'post')
    decision = Authorizer(store).decide({'actor': 'kel', 'action_kind': 'shell',
                                         'target': 'migration-probe', 'milestone': 'code'})
    con = sqlite3.connect(str(DST / 'post' / 'kel.sqlite3'))
    rows = con.execute('select decision, policy_version from guardrail_decisions '
                       'order by at desc limit 1').fetchall()
    con.close()
    print('probe decision:', decision['outcome'], '| recorded:', rows)

    lost = {t: (pre.get(t, 0), post.get(t, 0)) for t in pre if post.get(t, 0) < pre[t]}
    print('LOST_ROWS:', lost or 'none')
    migrations_now = [r[0] for r in sqlite3.connect(
        str(DST / 'post' / 'kel.sqlite3')).execute('select version from schema_migrations')]
    ok = not lost and 10 in migrations_now and rows and rows[0][1] == 'kel-authz-1.5'
    print('RESULT:', 'OK' if ok else 'REVIEW')


if __name__ == '__main__':
    main()
