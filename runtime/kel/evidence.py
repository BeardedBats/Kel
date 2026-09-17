"""Evidence records: write and freshness (Phase 5.0).

Docs 06/07: evidence is produced during work, bound to the exact command and the unchanged
artifact digest; a green exit is never enough on its own and evidence is never authored
after the fact. Freshness = inside the declared window; content-binding = the artifact
digest still matches what was tested. This module writes append-only rows into
`evidence_records` and answers those two questions. Claim wiring arrives with the D1
increment.
"""
import contextlib
import time

from .core import PolicyError, digest
from .workforce import assert_safe, new_id, require_integer, require_number, require_text

SCHEMA_VERSION = 1
EVIDENCE_CLASSES = ('test_run', 'check_result', 'review_record', 'scanner', 'runtime_probe',
                    'research_source')
COMMAND_BOUND_CLASSES = ('test_run', 'check_result', 'scanner', 'runtime_probe')
DEFAULT_FRESHNESS_WINDOW = 24 * 60  # minutes
EVIDENCE_FIELDS = ('id', 'schema_version', 'mission_id', 'task_id', 'evidence_class', 'label',
                   'command', 'exit_code', 'output_digest', 'artifact_digest', 'ran_at',
                   'freshness_window', 'produced_by')


def validate_evidence(record):
    """Refuse a malformed evidence record (docs 06/07, schema v1)."""
    if not isinstance(record, dict):
        raise PolicyError('An evidence record is an object')
    unknown = sorted(set(record) - set(EVIDENCE_FIELDS))
    if unknown:
        raise PolicyError('An evidence record has unknown fields: %s' % ', '.join(unknown))
    if record.get('schema_version') != SCHEMA_VERSION:
        raise PolicyError('Evidence schema_version must be %d' % SCHEMA_VERSION)
    require_text(record.get('id'), 'evidence id')
    require_text(record.get('mission_id'), 'mission_id')
    require_text(record.get('task_id'), 'task_id')
    klass = record.get('evidence_class')
    if klass not in EVIDENCE_CLASSES:
        raise PolicyError('Evidence classes are %s' % ', '.join(EVIDENCE_CLASSES))
    require_text(record.get('label'), 'evidence label')
    command = record.get('command')
    if klass in COMMAND_BOUND_CLASSES:
        require_text(command, 'evidence command (command-bound evidence needs the exact command)')
    elif command is not None:
        require_text(command, 'evidence command')
    if record.get('exit_code') is not None:
        require_integer(record['exit_code'], 'evidence exit_code')
    for field in ('output_digest', 'artifact_digest'):
        if record.get(field) is not None:
            require_text(record[field], 'evidence ' + field)
    require_number(record.get('ran_at'), 'evidence ran_at')
    require_integer(record.get('freshness_window'), 'evidence freshness_window', lo=1)
    require_text(record.get('produced_by'), 'evidence produced_by (never blank)')
    assert_safe(record, path='evidence')
    return record


def write_evidence(store, *, mission_id, task_id, evidence_class, label, produced_by,
                   command=None, exit_code=None, output=None, output_digest=None,
                   artifact_digest=None, ran_at=None, freshness_window=DEFAULT_FRESHNESS_WINDOW):
    """Write one append-only evidence row and return it (digest computed when output given)."""
    if output is not None and output_digest is None:
        output_digest = 'sha256:' + digest(output)
    record = {
        'id': new_id('ev_'),
        'schema_version': SCHEMA_VERSION,
        'mission_id': mission_id,
        'task_id': task_id,
        'evidence_class': evidence_class,
        'label': label,
        'command': command,
        'exit_code': exit_code,
        'output_digest': output_digest,
        'artifact_digest': artifact_digest,
        'ran_at': time.time() if ran_at is None else ran_at,
        'freshness_window': freshness_window,
        'produced_by': produced_by,
    }
    validate_evidence(record)
    with contextlib.closing(store.connect()) as db:
        db.execute('INSERT INTO evidence_records(id,schema_version,mission_id,task_id,'
                   'evidence_class,label,command,exit_code,output_digest,artifact_digest,'
                   'ran_at,freshness_window,produced_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (record['id'], record['schema_version'], record['mission_id'], record['task_id'],
                    record['evidence_class'], record['label'], record['command'], record['exit_code'],
                    record['output_digest'], record['artifact_digest'], record['ran_at'],
                    record['freshness_window'], record['produced_by']))
    return record


def freshness(record, *, now=None):
    """True while the record is inside its declared freshness window (minutes)."""
    ran_at = record.get('ran_at')
    window = require_integer(record.get('freshness_window'), 'evidence freshness_window', lo=1)
    require_number(ran_at, 'evidence ran_at')
    return (time.time() if now is None else now) <= ran_at + window * 60


def content_bound(record, artifact_digest):
    """True when the record's artifact digest matches the artifact content at hand."""
    require_text(artifact_digest, 'artifact digest')
    return record.get('artifact_digest') == artifact_digest
