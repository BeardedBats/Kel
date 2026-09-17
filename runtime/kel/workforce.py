"""Workforce OS foundations: schemas, registries and record safety (Phase 5.0).

Phase 5 is the Workforce OS from the V1.6 design set (`ux-audit/workforce-os/`, docs 03-15).
This module owns the additive V1.6 migration that creates the workforce record tables, the
shared id conventions, the skill-pack registry, and the one safety rule every workforce
record must pass: no hidden reasoning and no secret material ever lands in a durable row.

Design notes for this increment (schemas and registries only; no behavior changes):
- The design shorthand names a `contracts` table, but Kel already has a core `contracts`
  table (job contract versions, core.py). The workforce TaskContract ledger is therefore
  `task_contracts`, so the two records never mix. Documented deviation, not an accident.
- `task_contracts`, `workforce_messages` and `evidence_records` are append-only ledgers
  (doc 07: edits are new rows carrying `supersedes`). SQLite triggers refuse UPDATE and
  DELETE so the storage layer itself cannot rewrite history; corrections are new rows.
- `findings` carries workflow state (open/confirmed/dismissed/fixed) and stays mutable;
  `skill_packs` is a version catalog where an existing (name, version) pair is immutable.
- Ids use the design's ref prefixes (mis_/tsk_/ctr_/asn_/stf_/ev_/find_/msg_/pod_) with
  uuid4 bodies (this repository's uid convention) rather than ULIDs; DDL column names
  sender/recipient/reporter map to the doc 07/08 fields from/to/by.
- No consumer reads these tables yet: rollback is dropping them (or reverting this commit).
"""
import contextlib
import time
import uuid

from .core import PolicyError, digest, encode
from .memory import scan_secret
from .team import FORBIDDEN_DETAIL_KEYS

MIGRATION_VERSION = 16
MIGRATION_NAME = 'v16-workforce-schemas'

TABLES = ('task_contracts', 'workforce_messages', 'findings', 'evidence_records', 'skill_packs')

# Authority vocabulary shared by task contracts, skill packs and (later) authority bindings.
AUTHORITY_CLASSES = ('read-only', 'workspace-write', 'leased-write', 'external-effect')
AUTHORITY_RANK = {name: index for index, name in enumerate(AUTHORITY_CLASSES)}

# Id prefixes for the workforce ref vocabulary (docs 06/07). Validators never require a
# prefix; writers use them so cross-references read the way the design documents them.
ID_PREFIXES = ('mis_', 'tsk_', 'ctr_', 'asn_', 'stf_', 'ev_', 'find_', 'msg_', 'pod_')

DDL = """\
CREATE TABLE IF NOT EXISTS schema_migrations(
  version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS task_contracts(
  contract_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, version INTEGER NOT NULL,
  mission_id TEXT NOT NULL, parent_task TEXT, digest TEXT NOT NULL, data TEXT NOT NULL,
  created REAL NOT NULL, UNIQUE(task_id, version));
CREATE INDEX IF NOT EXISTS task_contracts_by_mission ON task_contracts(mission_id, created);
CREATE INDEX IF NOT EXISTS task_contracts_by_task ON task_contracts(task_id, version);
CREATE TRIGGER IF NOT EXISTS task_contracts_append_only_update
  BEFORE UPDATE ON task_contracts
  BEGIN SELECT RAISE(ABORT, 'task contracts are frozen at claim and append-only'); END;
CREATE TRIGGER IF NOT EXISTS task_contracts_append_only_delete
  BEFORE DELETE ON task_contracts
  BEGIN SELECT RAISE(ABORT, 'task contracts are append-only'); END;
CREATE TABLE IF NOT EXISTS workforce_messages(
  id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL, mission_id TEXT NOT NULL,
  task_id TEXT NOT NULL, sender TEXT NOT NULL, recipient TEXT NOT NULL, type TEXT NOT NULL,
  summary TEXT NOT NULL, refs TEXT NOT NULL, required_action TEXT NOT NULL,
  deadline REAL, budget_impact TEXT, details TEXT, supersedes TEXT, at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS workforce_messages_by_mission ON workforce_messages(mission_id, at);
CREATE INDEX IF NOT EXISTS workforce_messages_by_task ON workforce_messages(task_id, at);
CREATE TRIGGER IF NOT EXISTS workforce_messages_append_only_update
  BEFORE UPDATE ON workforce_messages
  BEGIN SELECT RAISE(ABORT, 'workforce messages are append-only; edits supersede'); END;
CREATE TRIGGER IF NOT EXISTS workforce_messages_append_only_delete
  BEFORE DELETE ON workforce_messages
  BEGIN SELECT RAISE(ABORT, 'workforce messages are append-only'); END;
CREATE TABLE IF NOT EXISTS findings(
  id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL, mission_id TEXT NOT NULL,
  task_id TEXT NOT NULL, lens TEXT NOT NULL, severity TEXT NOT NULL, confidence INTEGER NOT NULL,
  artifact TEXT, location TEXT, summary TEXT NOT NULL, evidence TEXT, fix TEXT,
  fingerprint TEXT NOT NULL, status TEXT NOT NULL, advisory INTEGER NOT NULL DEFAULT 0,
  reporter TEXT NOT NULL, confirmations TEXT, dismissal_reason TEXT,
  created REAL NOT NULL, updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS findings_by_fingerprint ON findings(fingerprint);
CREATE INDEX IF NOT EXISTS findings_by_mission ON findings(mission_id, status);
CREATE INDEX IF NOT EXISTS findings_by_lens ON findings(lens);
CREATE TABLE IF NOT EXISTS evidence_records(
  id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL, mission_id TEXT NOT NULL,
  task_id TEXT NOT NULL, evidence_class TEXT NOT NULL, label TEXT NOT NULL, command TEXT,
  exit_code INTEGER, output_digest TEXT, artifact_digest TEXT, ran_at REAL NOT NULL,
  freshness_window INTEGER NOT NULL, produced_by TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS evidence_by_task ON evidence_records(task_id, ran_at);
CREATE TRIGGER IF NOT EXISTS evidence_records_append_only_update
  BEFORE UPDATE ON evidence_records
  BEGIN SELECT RAISE(ABORT, 'evidence records are append-only; write a new record'); END;
CREATE TRIGGER IF NOT EXISTS evidence_records_append_only_delete
  BEFORE DELETE ON evidence_records
  BEGIN SELECT RAISE(ABORT, 'evidence records are append-only'); END;
CREATE TABLE IF NOT EXISTS skill_packs(
  name TEXT NOT NULL, version TEXT NOT NULL, digest TEXT NOT NULL, data TEXT NOT NULL,
  owner TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
  PRIMARY KEY(name, version));
CREATE INDEX IF NOT EXISTS skill_packs_by_name ON skill_packs(name, updated);
"""

# Hidden-reasoning keys are defined once by the team event contract; the workforce reuses the
# same vocabulary so "never recorded" means the same thing everywhere.
_FORBIDDEN_KEYS = tuple(key.lower() for key in FORBIDDEN_DETAIL_KEYS)


def new_id(prefix):
    """A fresh id in the workforce ref vocabulary (prefix + uuid4 hex)."""
    if not isinstance(prefix, str) or not prefix.endswith('_'):
        raise PolicyError('Workforce ids are a prefix ending with an underscore')
    return prefix + uuid.uuid4().hex


def find_unsafe(value, *, path='record'):
    """Every safety violation in a record-shaped value, as plain sentences.

    Illegal keys are hidden-reasoning surfaces (mirrors the team_events contract); illegal
    text is anything the memory scanner refuses as secret-like. Used by the schema
    validators at write time and by the sampling test over stored rows.
    """
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            name = str(key)
            if name.lower() in _FORBIDDEN_KEYS:
                found.append('%s.%s: hidden reasoning is never recorded' % (path, name))
            found.extend(find_unsafe(item, path='%s.%s' % (path, name)))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found.extend(find_unsafe(item, path='%s[%d]' % (path, index)))
    elif isinstance(value, str):
        secret = scan_secret(value)
        if secret:
            found.append('%s: looks like %s and is never recorded' % (path, secret))
    return found


def assert_safe(record, *, path='record'):
    found = find_unsafe(record, path=path)
    if found:
        raise PolicyError('Unsafe workforce record: ' + '; '.join(found[:3]))
    return True


def require_text(value, what, *, max_len=None, allow_empty=False):
    if not isinstance(value, str):
        raise PolicyError('%s must be a string' % what)
    if not allow_empty and not value.strip():
        raise PolicyError('%s must be a nonempty string' % what)
    if max_len is not None and len(value) > max_len:
        raise PolicyError('%s stays under %d characters' % (what, max_len))
    return value


def require_number(value, what, *, allow_none=False):
    if value is None and allow_none:
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PolicyError('%s must be a number' % what)
    return value


def require_integer(value, what, *, lo=None, hi=None):
    if type(value) is not int:
        raise PolicyError('%s must be an integer' % what)
    if lo is not None and value < lo:
        raise PolicyError('%s must be at least %d' % (what, lo))
    if hi is not None and value > hi:
        raise PolicyError('%s must be at most %d' % (what, hi))
    return value


def ensure_schema(store):
    """Create the V1.6 workforce tables (additive and idempotent; existing data untouched)."""
    with contextlib.closing(store.connect()) as db:
        db.executescript(DDL)
        if not db.execute('SELECT 1 FROM schema_migrations WHERE version=?',
                          (MIGRATION_VERSION,)).fetchone():
            db.execute('INSERT INTO schema_migrations(version,name,applied,note) VALUES(?,?,?,?)',
                       (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                        'tables=5; task_contracts/workforce_messages/evidence_records append-only'))
    return True


# --- skill pack registry (workforce-os doc 03 §5) ------------------------------------------

SKILL_PACK_REQUIRED = ('name', 'description', 'version', 'owner')
SKILL_PACK_OPTIONAL = ('triggers', 'requirements', 'outputs', 'authority_hint', 'sources')
SKILL_PACK_FIELDS = SKILL_PACK_REQUIRED + SKILL_PACK_OPTIONAL
SKILL_PACK_LIST_FIELDS = ('triggers', 'requirements', 'outputs', 'sources')
MAX_PACKS_PER_WORKER = 4


def validate_skill_pack(pack):
    """Refuse a malformed skill pack (doc 03 §5 frontmatter, v1)."""
    if not isinstance(pack, dict):
        raise PolicyError('A skill pack is an object')
    unknown = sorted(set(pack) - set(SKILL_PACK_FIELDS))
    if unknown:
        raise PolicyError('A skill pack has unknown fields: %s' % ', '.join(unknown))
    for field in SKILL_PACK_REQUIRED:
        if not isinstance(pack.get(field), str) or not pack[field].strip():
            raise PolicyError('Skill packs need a nonempty %s' % field)
    if len(pack['description']) > 500:
        raise PolicyError('Skill pack descriptions stay under 500 characters')
    hint = pack.get('authority_hint')
    if hint is not None and hint not in AUTHORITY_CLASSES:
        raise PolicyError('A skill pack authority hint is one of %s' % ', '.join(AUTHORITY_CLASSES))
    for field in SKILL_PACK_LIST_FIELDS:
        if field in pack:
            items = pack[field]
            if not isinstance(items, list) or any(not isinstance(x, str) or not x.strip() for x in items):
                raise PolicyError('Skill pack %s is a list of nonempty strings' % field)
    assert_safe(pack, path='skill_pack')
    return pack


def register_skill_pack(store, pack, *, now=None):
    """Register one pack version in the catalog. An existing (name, version) is immutable."""
    validate_skill_pack(pack)
    body = encode(pack)
    stamp = digest(pack)
    name, version = pack['name'], pack['version']
    moment = time.time() if now is None else now
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT digest FROM skill_packs WHERE name=? AND version=?',
                         (name, version)).fetchone()
        if row:
            if row[0] != stamp:
                raise PolicyError('Skill pack %s %s is immutable; bump the version' % (name, version))
            return {'name': name, 'version': version, 'digest': stamp, 'state': 'existing'}
        db.execute('INSERT INTO skill_packs(name,version,digest,data,owner,created,updated)'
                   ' VALUES(?,?,?,?,?,?,?)', (name, version, stamp, body, pack['owner'], moment, moment))
    return {'name': name, 'version': version, 'digest': stamp, 'state': 'registered'}
