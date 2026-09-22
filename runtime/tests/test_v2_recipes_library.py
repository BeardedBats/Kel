"""V2-07 — the recipe library's own surfaces (search, favourites, recent, categories, duplicate,
history, last result).

Reuse first: everything here reads the tables the line already has (`recipes`, `recipe_marks`, and
the jobs the engine keeps). No second workflow, no second store, nothing re-implemented.
"""
import tempfile
import time
import unittest

from kel.context import Context
from kel.core import PolicyError, Store
from kel.engine import compile_document
from kel.recipes import RecipeLibrary, validate_recipe


def recipe(recipe_id='acceptance-flow', version='1.0.0', category=None):
    item = {'schema_version': 1, 'recipe_id': recipe_id, 'recipe_version': version,
            'name': 'Acceptance Flow', 'description': 'A short flow for the library tests.',
            'source': 'project', 'kind': 'document', 'inputs': [],
            'steps': [{'id': 'first', 'title': 'Draft the note', 'action': 'work',
                       'objective': 'Write the note with enough text to pass the check.',
                       'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 40}],
                       'retries': {'max_attempts': 2, 'on_fail': 'retry'}}],
            'permissions': ['project:read'], 'verification': ['min_chars'],
            'terminal_states': ['VERIFIED', 'FAILED', 'UNCERTAIN'], 'budget': 8,
            'retry_policy': {'max_attempts_per_milestone': 4, 'provider_switch_after': 2}}
    if category:
        item['category'] = category
    return item


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.store = Store(self.tmp.name)
        self.context = Context(self.store)
        self.library = RecipeLibrary(self.store)
        self.library.install_builtins()
        self.project = self.context.project('Acceptance project', None, 'library tests')
        self.other = self.context.project('Acceptance other', None, 'library tests')

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass


class LibrarySurfaceTests(Base):
    def test_entries_carry_category_favourite_and_use(self):
        self.library.save(recipe(category='Housekeeping'), project_id=self.project, confirm=True)
        entries = {item['recipe_id']: item for item in self.library.entries(project_id=self.project)}
        self.assertIn('acceptance-flow', entries)
        self.assertEqual(entries['acceptance-flow']['category'], 'Housekeeping')
        self.assertFalse(entries['acceptance-flow']['favourite'])
        self.assertEqual(entries['acceptance-flow']['runs'], 0)

    def test_search_matches_name_description_and_step_titles(self):
        self.library.save(recipe(category='Housekeeping'), project_id=self.project, confirm=True)
        found = self.library.search(self.project, 'draft the note')
        self.assertEqual([item['recipe_id'] for item in found], ['acceptance-flow'])
        self.assertTrue(self.library.search(self.project, 'acceptance flow'))
        self.assertEqual(self.library.search(self.project, 'nothing-matches-this'), [])
        with self.assertRaises(PolicyError):
            self.library.search(self.project, '   ')

    def test_favourites_recent_and_runs_follow_real_use(self):
        self.library.save(recipe(), project_id=self.project, confirm=True)
        self.assertEqual(self.library.favourites(self.project), [])
        self.library.mark(self.project, 'acceptance-flow', favourite=True)
        self.assertEqual([item['recipe_id'] for item in self.library.favourites(self.project)],
                         ['acceptance-flow'])
        self.assertEqual(self.library.recent(self.project), [])
        self.library.mark(self.project, 'acceptance-flow', opened=True)
        recent = self.library.recent(self.project)
        self.assertEqual([item['recipe_id'] for item in recent], ['acceptance-flow'])
        self.library.mark(self.project, 'acceptance-flow', run=True, job_id='job-x')
        entry = next(item for item in self.library.entries(project_id=self.project)
                     if item['recipe_id'] == 'acceptance-flow')
        self.assertEqual(entry['runs'], 1)
        self.assertIsNotNone(entry['last_run_at'])
        self.assertLessEqual(time.time() - entry['last_run_at'], 5)

    def test_categories_count_every_recipe(self):
        self.library.save(recipe(category='Housekeeping'), project_id=self.project, confirm=True)
        counts = {item['name']: item['count'] for item in self.library.categories(self.project)}
        self.assertEqual(counts.get('Housekeeping'), 1)
        self.assertGreaterEqual(counts.get('Uncategorised', 0), 1)

    def test_duplicate_drafts_a_copy_and_saving_keeps_it_in_one_project(self):
        self.library.save(recipe(category='Housekeeping'), project_id=self.project, confirm=True)
        draft = self.library.duplicate('acceptance-flow', self.project)
        copy = draft['recipe']
        self.assertEqual(copy['recipe_id'], 'acceptance-flow-copy')
        self.assertEqual(copy['source'], 'project')
        self.assertEqual(copy['recipe_version'], '0.1.0')
        self.assertEqual(len(copy['steps']), 1, 'the copy carries the original steps')
        self.assertEqual(draft['copied_from'], 'acceptance-flow')
        # The draft is not a saved recipe until the person saves it.
        self.assertNotIn('acceptance-flow-copy',
                         [item['recipe_id'] for item in self.library.entries(project_id=self.project)])
        self.library.save(copy, project_id=self.project, confirm=True)
        self.assertIn('acceptance-flow-copy',
                      [item['recipe_id'] for item in self.library.entries(project_id=self.project)])
        self.assertNotIn('acceptance-flow-copy',
                         [item['recipe_id'] for item in self.library.entries(project_id=self.other)],
                         'a project copy never leaks into another project')
        # A second duplicate finds a free id instead of colliding.
        again = self.library.duplicate('acceptance-flow', self.project)
        self.assertNotEqual(again['recipe']['recipe_id'], 'acceptance-flow-copy')

    def test_history_and_last_result_read_the_jobs_the_engine_keeps(self):
        self.library.save(recipe(), project_id=self.project, confirm=True)
        empty = self.library.last_result(self.project, 'acceptance-flow')
        self.assertEqual(empty['state'], 'never_run')
        self.assertIn('has not run', empty['sentence'])
        contract = compile_document('Write the acceptance note with enough text.', required=[])
        contract = dict(contract)
        contract['recipe'] = {'id': 'acceptance-flow', 'version': '1.0.0'}
        job_id = self.store.create(contract, conversation=self.project)
        with self.store.transaction() as db:
            job = self.store._get(db, job_id)
            job['milestones'][list(job['milestones'])[0]]['artifact'] = {
                'run_id': 'run-1', 'path': 'changes.md', 'sha256': 'abc'}
            job.update(state='CLOSED', verdict='VERIFIED')
            self.store._save(db, job, 'test.settle')
        history = self.library.history(self.project, 'acceptance-flow')
        self.assertEqual([item['job_id'] for item in history], [job_id])
        self.assertEqual(history[0]['artifact'], 'changes.md')
        latest = self.library.last_result(self.project, 'acceptance-flow')
        self.assertEqual(latest['job_id'], job_id)
        self.assertIn('finished', latest['sentence'])
        self.assertTrue(latest['can_run_again'])

    def test_a_category_must_be_short(self):
        with self.assertRaises(PolicyError):
            validate_recipe(recipe(category='x' * 41))
        validate_recipe(recipe(category='Housekeeping'))


if __name__ == '__main__':
    unittest.main()
