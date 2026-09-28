"""FN-12: Recipes can be written, renamed and re-worded on the Recipes page; names saved from work
are never cut mid-word; steps say what they do; recipe runs are named "Ran <recipe>"."""
import tempfile
import unittest

from kel.context import Context
from kel.core import PolicyError, Store
from kel.engine import compile_document
from kel.office import recipe_title
from kel.recipes import RecipeLibrary, compile_recipe, step_title, words_upto


class FN12RecipeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        self.context = Context(self.store)
        self.library = RecipeLibrary(self.store)
        self.library.install_builtins()
        self.project = self.context.project('Recipes project', None, '')

    def test_words_are_never_cut_mid_word(self):
        text = 'Write me a short summary of the quarterly report for the board meeting next week please'
        cut = words_upto(text, 60)
        self.assertTrue(cut.endswith('…'))
        self.assertTrue(text.startswith(cut[:-1]))
        self.assertIn(text[len(cut) - 1], ' ')  # the cut falls on a space
        self.assertEqual(step_title('Draft the plan. Then check it.'), 'Draft the plan')

    def test_create_then_rename_and_reword_keeps_history(self):
        out = self.library.create(self.project, 'Weekly rankings refresh', 'Refresh the rankings table.',
                                  [{'objective': 'Collect this week’s numbers from the sheet.'},
                                   {'objective': 'Rewrite the rankings table with the new numbers.'}])
        rid = out['recipe_id']
        self.assertTrue(out['saved'])
        info = self.library.get(rid, project_id=self.project)
        self.assertEqual([s['title'] for s in info['recipe']['steps']],
                         ['Collect this week’s numbers from the sheet', 'Rewrite the rankings table with the new numbers'])
        self.library.update(rid, self.project, name='Rankings refresh')
        renamed = self.library.get(rid, project_id=self.project)
        self.assertEqual((renamed['recipe']['name'], renamed['version']), ('Rankings refresh', '1.0.1'))
        steps = [{'id': s['id'], 'objective': s['objective']} for s in renamed['recipe']['steps']]
        steps[1]['objective'] = 'Rewrite the table and note the biggest movers.'
        self.library.update(rid, self.project, steps=steps)
        edited = self.library.get(rid, project_id=self.project)
        self.assertEqual(edited['version'], '1.0.2')
        self.assertEqual(edited['recipe']['steps'][1]['title'], 'Rewrite the table and note the biggest movers')
        self.assertEqual(edited['recipe']['steps'][1]['checks'], renamed['recipe']['steps'][1]['checks'])
        self.assertEqual(len(self.library.versions(rid, project_id=self.project)), 3)
        self.assertEqual(self.library.update(rid, self.project, name='Rankings refresh')['saved'], False)
        with self.assertRaises(PolicyError):
            self.library.create(self.project, '  ', '', [{'objective': 'x'}])

    def test_a_builtin_is_edited_as_this_projects_copy(self):
        builtin = self.library.entries(project_id=self.project)[0]['recipe_id']
        self.library.update(builtin, self.project, name='My own version')
        self.assertEqual(self.library.get(builtin, project_id=self.project)['recipe']['name'], 'My own version')
        self.assertNotEqual(self.library.get(builtin)['recipe']['name'], 'My own version')

    def test_saved_from_work_has_a_whole_word_name_and_real_step_words(self):
        request = 'Write a short summary of the quarterly report so the board can read it before Friday’s meeting'
        job = self.store.create(compile_document(request), 10)
        proposal = self.library.propose_from_job(job)
        recipe = proposal['recipe']
        self.assertNotIn('Saved run', recipe['name'])
        self.assertTrue(request.startswith(recipe['name'].rstrip('…')))
        self.assertNotIn(job, recipe['description'])
        self.assertNotEqual(recipe['steps'][0]['title'], 'document')

    def test_runs_are_named_after_their_recipe(self):
        out = self.library.create(self.project, 'Inbox triage', '', [{'objective': 'Sort the inbox into three piles.'}])
        info = self.library.get(out['recipe_id'], project_id=self.project)
        contract = compile_recipe(info['recipe'], {}, self.project)
        self.assertNotIn('v1.0.0', contract['request'])
        self.assertNotIn(out['recipe_id'] + ')', contract['request'])
        self.assertEqual(recipe_title(contract), 'Ran Inbox triage')
        self.assertEqual(recipe_title({'request': 'Run recipe Saved run: Weekly v1.0.0 (job-3ad8abcd).'}), 'Ran Saved run: Weekly')


if __name__ == '__main__':
    unittest.main()
