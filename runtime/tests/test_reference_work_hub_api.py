"""Selected inert bytes cross existing scoped authority before extraction and adoption."""
import base64
import contextlib
import sys
import types
from unittest.mock import Mock, patch

import pytest

from kel.core import PolicyError
from kel.service import Service
from kel.work_hub import WorkHub

PATH='/api/work-hub/references'


@pytest.fixture
def api(tmp_path):
    service=Service(tmp_path/'engine')
    service.engine.adapters={}
    extractor=Mock(return_value={'text':'Selected file text.','kind':'pdf','extraction':'pdf-text','pages':1})
    module=types.ModuleType('kel.reference_extract');module.extract_reference=extractor
    with patch.dict(sys.modules,{'kel.reference_extract':module}):
        try:yield service,WorkHub(service),extractor
        finally:service.shutdown()


def extract(service, **changes):
    data={'action':'extract','project_id':'default','name':'notes.pdf','content':base64.b64encode(b'%PDF-selected-inert').decode('ascii')}
    data.update(changes)
    return service.action(PATH,data)


def test_extract_review_adopt_original_and_no_jobs(api):
    service,hub,extractor=api
    source=extract(service)
    extractor.assert_called_once_with('notes.pdf',b'%PDF-selected-inert')
    assert source['state']=='staged' and source['source_bytes']==19
    assert hub.get(PATH,{'project_id':'default'})['entries'][0]['id']==source['id']
    preview=service.action('/api/work-hub/imports',{'action':'preview','project_id':'default','content':'Transcript.', 'extraction_ids':[source['id']]})
    assert preview['reference_files'][0]['source']['id']==source['id']
    receipt=service.action('/api/work-hub/imports',{'action':'confirm','project_id':'default','preview_id':preview['preview_id'],'digest':preview['digest'],'confirm':True})
    original=service.action(PATH,{'action':'original','project_id':'default','id':source['id']})
    assert base64.b64decode(original['content'])==b'%PDF-selected-inert'
    assert original['metadata']['state']=='adopted'
    state=service.state(receipt['conversation_id'])
    assert state['jobs']==[] and 'Selected file text.' in state['messages'][0]['text']


@pytest.mark.parametrize('changes',[{'project_id':'missing'},{'project_id':'*'},{'name':'../private.pdf'},
                                    {'content':'not base64!'},{'content':''},{'content':['bad']},
                                    {'path':'C:/private.pdf'},{'url':'https://example.org/file'},
                                    {'source_sha256':'forged'}])
def test_invalid_scope_bytes_and_arbitrary_reads_refused_before_extract(api,changes):
    service,_,extractor=api
    with pytest.raises(PolicyError):extract(service,**changes)
    extractor.assert_not_called()


def test_extraction_error_and_secret_text_are_not_persisted(api):
    service,_,extractor=api
    extractor.side_effect=ValueError('No readable PDF text was found.')
    with pytest.raises(PolicyError,match='readable PDF'):extract(service)
    extractor.side_effect=None
    extractor.return_value={'text':'sk-'+'A'*24,'kind':'pdf','extraction':'pdf-text','pages':1}
    with pytest.raises(PolicyError,match='secret'):extract(service)
    with contextlib.closing(service.store.connect()) as db:
        assert db.execute('SELECT COUNT(*) FROM reference_sources').fetchone()[0]==0


def test_discard_exact_receipt_and_original_wrong_project_refused(api):
    service,hub,_=api
    source=extract(service)
    with patch.object(service,'_scope',return_value='other'):
        with pytest.raises(PolicyError):hub.act(PATH,{'action':'original','project_id':'other','id':source['id']})
    assert service.action(PATH,{'action':'discard','project_id':'default','id':source['id']})['discarded']
    with pytest.raises(PolicyError):service.action(PATH,{'action':'original','project_id':'default','id':source['id']})


def test_original_uses_read_scope_and_rejects_forged_fields(api):
    service,hub,_=api
    source=extract(service)
    with patch.object(service,'_scope',wraps=service._scope) as scope:
        hub.act(PATH,{'action':'original','project_id':'default','id':source['id']})
    assert scope.call_args.kwargs['write'] is False
    with pytest.raises(PolicyError):hub.act(PATH,{'action':'original','project_id':'default','id':source['id'],'text':'forged'})


def test_extract_returns_full_scoped_review_text_but_metadata_stays_small(api):
    service,hub,extractor=api
    text='Reviewed text. '*100+'Last page detail.'
    extractor.return_value={'text':text,'kind':'pdf','extraction':'pdf-text','pages':3}
    source=extract(service)
    assert source['text']==text and source['text_chars']==len(text)
    assert source['snippet']==text[:600] and len(source['text'])>600
    listed=hub.get(PATH,{'project_id':'default'})['entries'][0]
    assert 'text' not in listed and listed['snippet']==text[:600]
    original=service.action(PATH,{'action':'original','project_id':'default','id':source['id']})
    assert 'text' not in original['metadata']
    with patch.object(service,'_scope',return_value='other'):
        with pytest.raises(PolicyError):hub.get(PATH,{'project_id':'other'})
        with pytest.raises(PolicyError):hub.act(PATH,{'action':'original','project_id':'other','id':source['id']})
