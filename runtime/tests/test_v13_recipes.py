"""V1.3 Gate 5: reusable workflow recipes (KEL_V1.3_RECIPE_SPEC.md; REC-01..08)."""
import copy
import json
import tempfile
import unittest

from kel.context import Context
from kel.core import PolicyError, Store
from kel.recipes import (BUILTINS, CONTINUE_RECIPE_ID, RecipeLibrary, compile_recipe,
                         recipe_digest, validate_recipe)
from kel.continuation import Continuation
from kel.engine import Engine
from kel.native import FixtureAdapter


def simple_recipe(version='1.0.0', steps=2):
    step_list = [{'id': 'first', 'title': 'First', 'action': 'work',
                  'objective': 'Write the first artifact with enough text.',
                  'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 40}],
                  'retries': {'max_attempts': 2, 'on_fail': 'retry'}}]
    if steps == 2:
        step_list.append({'id': 'second', 'title': 'Second', 'action': 'work',
                          'objective': 'Write the second artifact.',
                          'depends_on': ['first'],
                          'checks': [{'kind': 'min_chars', 'value': 40}],
                          'retries': {'max_attempts': 2, 'on_fail': 'retry'}})
    return {'schema_version': 1, 'recipe_id': 'test-flow', 'recipe_version': version,
            'name': 'Test Flow', 'description': 'Minimal test flow.', 'source': 'builtin',
            'kind': 'document', 'inputs': [], 'steps': step_list,
            'permissions': ['project:read'], 'verification': ['min_chars'],
            'terminal_states': ['VERIFIED', 'FAILED', 'UNCERTAIN'], 'budget': 8,
            'retry_policy': {'max_attempts_per_milestone': 4, 'provider_switch_after': 2}}


class RecipeCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.context = Context(self.store)
        self.lib = RecipeLibrary(self.store)
        self.assertEqual(self.lib.install_builtins(), 5)

    def base(self, index=0):
        return json.loads(json.dumps(copy.deepcopy(BUILTINS[index])))

    def assertInvalid(self, data, fragment=None):
        with self.assertRaises(PolicyError) as cm:
            validate_recipe(data)
        if fragment:
            self.assertIn(fragment, str(cm.exception))
        return cm.exception

    def test_rec01_builtins_install_and_validate(self):
        self.assertEqual(self.lib.install_builtins(), 0)
        entries = {entry['recipe_id']: entry for entry in self.lib.entries()}
        self.assertEqual(set(entries), {r['recipe_id'] for r in BUILTINS})
        for recipe in BUILTINS:
            validate_recipe(recipe)
            info = self.lib.get(recipe['recipe_id'])
            self.assertEqual(info['scope'], 'builtin')
            self.assertEqual(info['version'], recipe['recipe_version'])
            self.assertEqual(info['digest'], recipe_digest(recipe))
        self.assertEqual(len(entries), 5)

    def test_rec02_unknown_fields_rejected(self):
        data = self.base()
        data['mystery'] = 1
        self.assertInvalid(data, 'unknown field')
        data = self.base()
        data['steps'][0]['command'] = 'rm -rf'
        self.assertInvalid(data, 'unknown field')
        data = self.base()
        data['steps'][0]['checks'][0]['exec'] = 'python x.py'
        self.assertInvalid(data, 'unknown field')
        data = self.base()
        data['inputs'][0]['regex'] = '.*'
        self.assertInvalid(data, 'unknown field')
        data = self.base()
        data['steps'][0]['retries']['backoff'] = 3
        self.assertInvalid(data, 'unknown field')

    def test_rec03_structural_rules(self):
        data = self.base()
        data['recipe_id'] = 'Bad_ID!'
        self.assertInvalid(data, 'recipe_id')
        data = self.base()
        data['recipe_version'] = '1.0'
        self.assertInvalid(data, 'MAJOR.MINOR.PATCH')
        data = self.base()
        data['steps'] = []
        self.assertInvalid(data, 'steps')
        data = self.base()
        data['steps'] = data['steps'] * 2
        self.assertInvalid(data, 'steps')
        data = self.base()
        data['steps'][1]['id'] = 'reproduce'
        self.assertInvalid(data, 'duplicate step id')
        data = self.base()
        data['steps'][1]['depends_on'] = ['ghost']
        self.assertInvalid(data, 'unknown step')
        data = self.base()
        data['steps'][0]['depends_on'] = ['reproduce']
        self.assertInvalid(data, 'cannot depend on itself')
        data = self.base()
        data['steps'][0]['depends_on'] = ['verify']
        self.assertInvalid(data, 'cycle')
        data = self.base()
        data['steps'][0]['objective'] = 'Use {undeclared_thing} now.'
        self.assertInvalid(data, 'references no declared input')
        data = self.base()
        data['terminal_states'] = ['VERIFIED']
        self.assertInvalid(data, 'UNCERTAIN')
        data = self.base()
        data['verification'] = []
        self.assertInvalid(data, 'verification')
        data = self.base()
        data['retry_policy']['provider_switch_after'] = 3
        self.assertInvalid(data, 'provider_switch_after')
        data = self.base()
        data['budget'] = 0
        self.assertInvalid(data, 'budget')
        data = self.base()
        data['steps'][0]['retries']['max_attempts'] = 5
        self.assertInvalid(data, 'max_attempts')
        data = self.base()
        data['steps'][0]['kind_override'] = 'coding'
        self.assertInvalid(data, 'only allowed for mixed')
        data = self.base(1)
        data['steps'][0].pop('kind_override')
        self.assertInvalid(data, 'mixed recipes require')

    def test_rec04_kind_minima_and_commands(self):
        data = self.base(3)
        data['permissions'].remove('web:search')
        self.assertInvalid(data, 'web:search')
        data = self.base()
        data['permissions'].remove('project:read')
        self.assertInvalid(data, 'project:read')
        data = self.base(2)
        data['permissions'].remove('commands:run')
        self.assertInvalid(data, 'commands:run')

    def test_rec05_compile_to_contract(self):
        contract = compile_recipe(self.lib.get('fix-bug')['recipe'], {'bug': 'crash on save'},
                                  project_id='p1', root=self.temp.name,
                                  tests=['python', '-m', 'pytest'])
        self.assertEqual(contract['kind'], 'coding')
        self.assertEqual(contract['recipe']['id'], 'fix-bug')
        self.assertEqual([m['id'] for m in contract['milestones']],
                         ['reproduce', 'fix', 'verify'])
        self.assertIn('crash on save', contract['milestones'][0]['objective'])
        self.assertEqual(contract['test_command'], ['python', '-m', 'pytest'])
        with self.assertRaises(PolicyError):
            compile_recipe(self.lib.get('fix-bug')['recipe'], {'bug': 'x'}, project_id='p1',
                           root=None, tests=['pytest'])
        with self.assertRaises(PolicyError):
            compile_recipe(self.lib.get('fix-bug')['recipe'], {}, project_id='p1',
                           root=self.temp.name, tests=['pytest'])
        with self.assertRaises(PolicyError):
            compile_recipe(self.lib.get('fix-bug')['recipe'], {'bug': 'x', 'nope': 1},
                           project_id='p1', root=self.temp.name, tests=['pytest'])
        audit = compile_recipe(self.lib.get('audit-and-repair')['recipe'], {},
                               project_id='p1', root=self.temp.name, tests=['pytest'])
        rendered = audit['milestones'][0]['objective']
        self.assertIn('quick', rendered)
        self.assertIn('unspecified', rendered)
        with self.assertRaises(PolicyError):
            compile_recipe(self.lib.get('audit-and-repair')['recipe'], {'depth': 'extreme'},
                           project_id='p1', root=self.temp.name, tests=['pytest'])
        descriptor = compile_recipe(self.lib.get('continue-work')['recipe'], {'hint': 'release'})
        self.assertTrue(descriptor['continuation'])
        self.assertEqual(descriptor['stages'],
                         ['resolve', 'validate', 'preserve', 'resume', 'review'])
        self.assertEqual(self.store.list_jobs(), [])

    def test_rec06_project_save_requires_confirmation(self):
        recipe = copy.deepcopy(simple_recipe())
        recipe['source'] = 'project'
        project_id = 'default'
        with self.assertRaises(PolicyError) as cm:
            self.lib.save(recipe, project_id=project_id)
        self.assertIn('confirmation', str(cm.exception))
        saved = self.lib.save(recipe, project_id=project_id, confirm=True)
        self.assertTrue(saved['saved'])
        again = self.lib.save(recipe, project_id=project_id, confirm=True)
        self.assertFalse(again['saved'])
        self.assertEqual(again['digest'], saved['digest'])

    def test_rec07_shadowing_and_immutability(self):
        base = self.base()
        base['source'] = 'project'
        base['recipe_version'] = '1.0.1'
        base['description'] = 'Project-local fix flow.'
        project_id = 'default'
        self.lib.save(base, project_id=project_id, confirm=True)
        shadow = self.lib.get('fix-bug', project_id=project_id)
        self.assertEqual(shadow['scope'], 'project')
        self.assertTrue(shadow['shadowed'])
        self.assertEqual(shadow['version'], '1.0.1')
        builtin = self.lib.get('fix-bug')
        self.assertEqual(builtin['scope'], 'builtin')
        self.assertEqual(builtin['version'], '1.0.0')
        clash = self.base()
        clash['source'] = 'project'
        clash['recipe_version'] = '1.0.1'
        clash['description'] = 'Different content under a taken version.'
        with self.assertRaises(PolicyError) as cm:
            self.lib.save(clash, project_id=project_id, confirm=True)
        self.assertIn('bump the version', str(cm.exception))
        versions = self.lib.versions('fix-bug', project_id=project_id)
        self.assertEqual({(v['scope'], v['version']) for v in versions},
                         {('builtin', '1.0.0'), ('project', '1.0.1')})

    def test_rec08_from_job_propose_confirm_and_job_check(self):
        job = self.store.create({'request': 'Write a small plan.',
                                 'milestones': [{'id': 'plan', 'objective': 'Write the plan.',
                                                 'filename': 'plan.md', 'depends_on': [],
                                                 'checks': [{'kind': 'min_chars', 'value': 40}]}]})
        draft = self.lib.propose_from_job(job)
        validate_recipe(draft['recipe'])
        self.assertTrue(draft['recipe']['recipe_id'].startswith('job-'))
        self.assertEqual(draft['recipe']['source'], 'from_job:' + job)
        with self.assertRaises(PolicyError):
            self.lib.save(draft['recipe'], project_id='default')
        saved = self.lib.save(draft['recipe'], project_id='default', confirm=True)
        self.assertTrue(saved['saved'])
        with self.assertRaises(PolicyError) as cm:
            self.lib.propose_from_job('not-a-job')
        self.assertIn('Job missing', str(cm.exception))
        ghost = copy.deepcopy(simple_recipe())
        ghost['source'] = 'from_job:00000000-0000-0000-0000-000000000000'
        with self.assertRaises(PolicyError) as cm:
            self.lib.save(ghost, project_id='default', confirm=True)
        self.assertIn('does not exist', str(cm.exception))

    def test_rec09_builtin_content_guard(self):
        with self.store.transaction() as db:
            db.execute("UPDATE recipes SET data='{}', digest='tampered'"
                       " WHERE recipe_id='fix-bug' AND scope='builtin'")
        with self.assertRaises(PolicyError) as cm:
            self.lib.install_builtins()
        self.assertIn('version bump', str(cm.exception))

    def drive_first_milestone(self, job):
        run = self.store.claim(job, 'first')
        self.store.enqueue_result('evt', run['id'], run['epoch'],
                                  {'outcome': 'SUCCESS', 'text': 'ACCEPT ' + 'x' * 60})
        self.store.consume()
        return self.store.verify(job, 'first')

    def test_rec10_accepted_steps_are_frozen(self):
        contract = compile_recipe(simple_recipe(), {}, project_id='default')
        engine = Engine(self.store, {'fixture': FixtureAdapter(output='ACCEPT ' + 'x' * 60)})
        try:
            job = engine.submit(contract)
            done = engine.wait(job, 5)
            self.assertEqual(done['verdict'], 'VERIFIED')
            with self.assertRaises(PolicyError):
                self.store.claim(job, 'first')
            self.assertEqual(self.store.get(job)['milestones']['first']['attempts'], 1)
        finally:
            engine.close()

    def test_rec11_failed_steps_receive_bounded_repair(self):
        engine = Engine(self.store, {'fixture': FixtureAdapter(
            output='ACCEPT ' + 'x' * 60, fail_first=True)})
        try:
            job = engine.submit(compile_recipe(simple_recipe(), {}, project_id='default'))
            done = engine.wait(job, 5)
            self.assertEqual(done['verdict'], 'VERIFIED')
            self.assertEqual(done['milestones']['first']['attempts'], 2)
        finally:
            engine.close()
        engine = Engine(self.store, {'fixture': FixtureAdapter(output='bad')})
        try:
            job = engine.submit(compile_recipe(simple_recipe(version='1.0.1'), {},
                                               project_id='default'))
            done = engine.wait(job, 5)
            self.assertEqual(done['verdict'], 'FAILED')
            self.assertEqual(done['milestones']['first']['attempts'], 4)
        finally:
            engine.close()

    def test_rec12_terminal_verdict_remains_kel_controlled(self):
        contract = compile_recipe(simple_recipe(), {}, project_id='default')
        self.assertNotIn('terminal_states', contract)
        self.assertNotIn('terminal_states', contract['milestones'][0])
        engine = Engine(self.store, {'fixture': FixtureAdapter(output='bad')})
        try:
            job = engine.submit(contract)
            done = engine.wait(job, 5)
            self.assertEqual(done['verdict'], 'FAILED')
        finally:
            engine.close()

    def test_rec13_interrupted_recipe_resumes_with_accepted_frozen(self):
        contract = compile_recipe(simple_recipe(), {}, project_id='default')
        job = self.store.create(contract, conversation='main')
        self.assertEqual(self.drive_first_milestone(job), 'VERIFIED')
        with self.store.transaction() as db:
            current = self.store._get(db, job)
            current['state'] = 'PAUSED'
            self.store._save(db, current, 'test.pause')
        cont = Continuation(self.store)
        result = cont.resolve('default', 'main')
        self.assertEqual(result['kind'], 'single')
        out = cont.execute_resume(job, 'main')
        self.assertIn(out['state'], ('READY', 'WAITING_RESOURCE'))
        final = self.store.get(job)
        self.assertEqual(final['milestones']['first']['state'], 'ACCEPTED')
        self.assertEqual(out['plan']['reopen'], ['second'])
        self.assertEqual(out['plan']['preserve'], ['first'])
        self.assertEqual(len(cont.links(job)), 1)

    def test_rec14_continue_recipe_creates_no_job(self):
        descriptor = compile_recipe(self.lib.get('continue-work')['recipe'], {})
        self.assertTrue(descriptor['continuation'])
        self.assertEqual(self.store.list_jobs(), [])


if __name__ == '__main__':
    unittest.main()
