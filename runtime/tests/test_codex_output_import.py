"""Documented Codex exec JSONL subset, not live CLI or native continuation proof.

Primary schema: https://developers.openai.com/codex/noninteractive/
and openai/codex sdk/typescript/src/events.ts + items.ts. No upstream code copied.
"""
import contextlib
import json

import pytest

from kel.core import PolicyError, Store
from kel.work_import import WorkImports

THREAD = '0199a213-81c0-7800-8aa1-bbab2a035a53'


@pytest.fixture
def imports(tmp_path):
    store = Store(tmp_path / 'engine')
    with contextlib.closing(store.connect()) as db:
        db.executescript('CREATE TABLE projects(id TEXT PRIMARY KEY,name TEXT,root TEXT,context TEXT,updated REAL);'
                         'CREATE TABLE conversations(id TEXT PRIMARY KEY,project_id TEXT,title TEXT,created REAL);')
        db.execute("INSERT INTO projects VALUES('p','Project',NULL,'',1)")
    return WorkImports(store)


def stream(*extra, thread=THREAD):
    records = [{'type': 'thread.started', 'thread_id': thread}, {'type': 'turn.started'}, *extra,
               {'type': 'item.completed', 'item': {'id': 'item_3', 'type': 'agent_message',
                                                   'text': 'The draft links to its original task.'}},
               {'type': 'turn.completed', 'usage': {'input_tokens': 10, 'cached_input_tokens': 0,
                                                   'output_tokens': 8, 'reasoning_output_tokens': 0}}]
    return '\n'.join(json.dumps(record) for record in records)


def test_completed_output_preserves_ids_and_imports_no_native_authority(imports):
    preview = imports.preview('p', stream(), format='codex-exec-jsonl')
    assert preview['source'] == 'codex' and preview['source_id'] == THREAD
    assert preview['source_thread_id'] == THREAD
    assert preview['messages'][0]['id'] == 'item_3'
    assert preview['source_completion'] == 'turn.completed'
    assert preview['continuation_supported'] is False
    receipt = imports.confirm(preview['preview_id'], preview['digest'], 'p', True)
    assert receipt['mode'] == 'import'
    assert imports.store.list_jobs() == []
    with contextlib.closing(imports.store.connect()) as db:
        message = db.execute('SELECT role,text,meta FROM messages WHERE conversation_id=?',
                             (receipt['conversation_id'],)).fetchone()
    assert message['role'] == 'user' and 'external-untrusted' in message['meta']
    assert 'item_3' in message['text']


def test_tool_reasoning_and_future_events_are_explicitly_omitted(imports):
    log = stream({'type': 'item.completed', 'item': {'id': 'reasoning', 'type': 'reasoning', 'text': 'Source reasoning'}},
                 {'type': 'item.completed', 'item': {'id': 'command', 'type': 'command_execution',
                    'command': 'do a thing', 'aggregated_output': 'untrusted tool output', 'status': 'completed'}},
                 {'type': 'future.event', 'payload': {'arbitrary': 'not adopted'}})
    preview = imports.preview('p', log, format='codex-exec-jsonl', source='codex')
    assert len(preview['messages']) == 1
    omitted = {item['name'] for item in preview['omissions']}
    assert {'Original prompt and attachments', 'item.reasoning', 'item.command_execution', 'future.event'} <= omitted
    assert 'untrusted tool output' not in json.dumps(preview)
    assert 'Source reasoning' not in json.dumps(preview)


def test_repeated_codex_output_dedupes_without_claiming_completion(imports):
    one = imports.preview('p', stream(), format='codex-exec-jsonl')
    a = imports.confirm(one['preview_id'], one['digest'], 'p', True)
    two = imports.preview('p', stream(), format='codex-exec-jsonl', title='Another visible title')
    b = imports.confirm(two['preview_id'], two['digest'], 'p', True)
    assert b['duplicate'] and a['conversation_id'] == b['conversation_id']


@pytest.mark.parametrize('log', ['not JSON', json.dumps({'type': 'thread.started', 'thread_id': THREAD}),
    stream({'type': 'thread.started', 'thread_id': 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'}),
    stream({'type': 'item.completed', 'item': {'id': 'item_3', 'type': 'agent_message', 'text': 'Duplicate'}}),
    stream(thread='not-a-native-id')], ids=['malformed', 'no-messages', 'mixed-threads', 'duplicate-items', 'bad-thread'])
def test_unsupported_or_ambiguous_logs_fail_without_persistence(imports, log):
    with pytest.raises(PolicyError):
        imports.preview('p', log, format='codex-exec-jsonl')
    with contextlib.closing(imports.store.connect()) as db:
        assert db.execute('SELECT COUNT(*) FROM work_import_previews').fetchone()[0] == 0


def test_decoded_secret_in_omitted_event_is_refused(imports):
    log = stream({'type': 'item.completed', 'item': {'id': 'command', 'type': 'command_execution',
                                                  'aggregated_output': 'sk-' + 'Z' * 24}}).replace('sk-', '\\u0073\\u006b-')
    with pytest.raises(PolicyError, match='secret-like'):
        imports.preview('p', log, format='codex-exec-jsonl')


def test_later_unfinished_turn_does_not_inherit_prior_completion(imports):
    log = stream() + '\n' + json.dumps({'type': 'turn.started'})
    preview = imports.preview('p', log, format='codex-exec-jsonl')
    assert preview['source_completion'] == 'unknown'
    assert any(item['name'] == 'Source completion' for item in preview['omissions'])


def test_codex_output_cannot_be_misattributed_as_claude(imports):
    with pytest.raises(PolicyError, match='Codex source'):
        imports.preview('p', stream(), format='codex-exec-jsonl', source='claude')
