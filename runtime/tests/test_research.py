import copy
import tempfile
import unittest
from kel.core import Store
from kel.research import ResearchAdapter,check_research_evidence

def response():
    return {'stop_reason':'end_turn','content':[
        {'type':'server_tool_use','name':'web_search'},
        {'type':'web_search_tool_result','content':[{'type':'web_search_result','url':'https://docs.python.org/3/library/pathlib.html'}]},
        {'type':'text','text':'Path.resolve resolves symbolic links and removes parent references. Path.absolute makes a path absolute without resolving symbolic links.',
         'citations':[{'type':'web_search_result_location','url':'https://docs.python.org/3/library/pathlib.html','title':'Python pathlib','cited_text':'Resolve symlinks'}]}]}

class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def execute(self,value):return ResearchAdapter(self.store,transport=lambda *args:value).execute('Research pathlib',run_id='run')
    def test_receipt_binds_answer_and_search_response(self):
        r=self.execute(response());self.assertEqual(r['outcome'],'SUCCESS')
        self.assertTrue(check_research_evidence(self.store,'run',r['text']))
        self.assertFalse(check_research_evidence(self.store,'run',r['text']+' edited'))
        with self.store.transaction() as db:db.execute("UPDATE research_evidence SET response='{}'")
        self.assertFalse(check_research_evidence(self.store,'run',r['text']))
    def test_fabricated_citation_rejected(self):
        r=response();r['content'][-1]['citations'][0]['url']='https://invented.example/'
        self.assertEqual(self.execute(r)['outcome'],'FAILED')
    def test_missing_live_search_rejected(self):
        r=response();r['content']=r['content'][-1:]
        self.assertEqual(self.execute(r)['outcome'],'FAILED')
    def test_incomplete_search_fails(self):
        r=response();r['stop_reason']='pause_turn'
        self.assertEqual(self.execute(r)['outcome'],'FAILED')
    def test_search_error_not_successful_result(self):
        r=response();r['content'][1]['content']={'type':'web_search_tool_result_error','error_code':'max_uses_exceeded'}
        self.assertEqual(self.execute(r)['outcome'],'FAILED')

if __name__=='__main__':unittest.main()
