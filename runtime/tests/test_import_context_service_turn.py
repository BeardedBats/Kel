"""Imported coverage survives enrichment failure and turn prompt compaction."""
import contextlib
import json
from unittest.mock import patch

import pytest

from kel.core import PolicyError
from kel.service import Service
from kel.turn import build_prompt, PROMPT_BUDGET


def test_turn_preserves_source_once_after_other_context_is_trimmed():
    source = {'text': 'SELECTED-END-FACT ' + ('reference ' * 1000), 'coverage': {'complete': False}}
    packet = {'history': [{'role': 'user', 'text': 'old ' * 10000}],
              'context_packet': {'text': 'optional ' * 10000},
              'imported_sources': [source],
              'imported_context': {'state': 'degraded'}}
    prompt = build_prompt(packet, 'Explain the selected fact.', [], forced=True)
    assert prompt.count('SELECTED-END-FACT') == 1
    assert '"complete": false' in prompt and '"state": "degraded"' in prompt
    assert len(prompt) <= PROMPT_BUDGET


def test_turn_fails_instead_of_silently_dropping_selected_source():
    with pytest.raises(PolicyError, match='selected imported excerpts exceed'):
        build_prompt({'imported_sources': [{'text': 'source ' * 5000}]}, 'Explain this fact.', [])


def test_submit_keeps_partial_coverage_when_enrichment_fails(tmp_path):
    service = Service(tmp_path / 'engine')
    service.engine.adapters = {}
    try:
        preview = service.action('/api/work-hub/imports', {
            'action': 'preview', 'project_id': 'default', 'content': 'Overview. ' + ('ordinary notes. ' * 4300),
            'format': 'text', 'source': 'claude'})
        receipt = service.action('/api/work-hub/imports', {
            'action': 'confirm', 'project_id': 'default', 'preview_id': preview['preview_id'],
            'digest': preview['digest'], 'confirm': True})
        with patch('kel.composer.Composer.build', side_effect=RuntimeError('fixture enrichment failure')), \
                patch.object(service.requests, 'submit'):
            sid = service.submit({'conversation': receipt['conversation_id'], 'text': 'Explain the overview notes.'})
        with contextlib.closing(service.store.connect()) as db:
            status = json.loads(db.execute('SELECT status FROM submission_context WHERE submission_id=?', (sid,)).fetchone()[0])
        assert status['state'] == 'degraded' and status['error_code'] == 'RuntimeError'
        assert status['import_coverage'][0]['coverage']['complete'] is False
        assert any(item['kind'] == 'imported_sources' for item in status['omissions'])
    finally:
        service.shutdown()
