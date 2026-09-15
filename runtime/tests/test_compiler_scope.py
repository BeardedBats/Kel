import json
import unittest
from kel.commander import Commander


class ScopeTests(unittest.TestCase):
    def proposed_parts(self, quotes):
        class Model:
            def execute(self,prompt):
                return {'outcome':'SUCCESS','text':json.dumps({'milestones':[
                    {'id':str(i),'filename':str(i)+'.md','depends_on':[],
                     'objective':'Invented demand: publish the result.',
                     'source_quote':q,'checks':[{'kind':'contains','value':'INVENTED'}]}
                    for i,q in enumerate(quotes)]})}
        return Commander(Model())

    def test_multiple_parts_cannot_add_objectives_or_checks(self):
        request='Write a setup guide. Write a troubleshooting guide. Use plain language.'
        contract,trace=self.proposed_parts(['Write a setup guide.', 'Write a troubleshooting guide.']).plan(request)
        self.assertEqual(trace['mode'],'model_proposal')
        self.assertEqual(len(contract['milestones']),3)
        self.assertNotIn('INVENTED',json.dumps(contract))
        self.assertNotIn('publish the result',json.dumps(contract))
        self.assertIn(request,contract['milestones'][-1]['objective'])
        self.assertEqual(contract['milestones'][-1]['depends_on'],['0','1'])
        for part in contract['milestones'][:-1]:
            self.assertIn(part['source_quote'],part['objective'])

    def test_unanchored_or_duplicate_parts_fall_back_without_changing_request(self):
        request='Write a setup guide. Write a troubleshooting guide.'
        for quotes in ([None,None],['Write a setup guide.','Send it to everyone.'],
                       ['Write a setup guide.','Write a setup guide.'],['','Write a setup guide.']):
            with self.subTest(quotes=quotes):
                contract,trace=self.proposed_parts(quotes).plan(request)
                self.assertEqual(trace['mode'],'template_fallback')
                self.assertEqual(contract['milestones'][0]['objective'],request)

    def test_planner_cannot_add_single_deliverable_restrictions(self):
        class Model:
            def execute(self,prompt):
                self.prompt=prompt
                return {'outcome':'SUCCESS','text':json.dumps({'milestones':[{
                    'id':'guide','objective':'Use facts only, no explanations. Marker exactly once at the top.',
                    'filename':'guide.md','depends_on':[],
                    'checks':[{'kind':'contains','value':'INVENTED'},
                              {'kind':'manual_review','rubric':'Marker exactly once at the top.'}]}]})}
        model=Model()
        request='Write a practical guide from the attached facts. Include the marker.'
        context={'files':[{'text':'The marker is SOURCE-47.'}]}
        contract,_=Commander(model).plan(request,context=context)
        self.assertEqual(contract['milestones'][0]['objective'],request)
        self.assertNotIn('INVENTED',json.dumps(contract))
        self.assertNotIn('Marker exactly once at the top.',json.dumps(contract))
        self.assertIn('SOURCE-47',model.prompt)

    def test_explicit_user_restrictions_survive(self):
        class Model:
            def execute(self,prompt):return {'outcome':'FAILED','error':'offline'}
        request='Put MARKER exactly once at the top. Use only supplied facts.'
        contract,_=Commander(Model()).plan(request)
        self.assertEqual(contract['milestones'][0]['objective'],request)


if __name__=='__main__':unittest.main()
