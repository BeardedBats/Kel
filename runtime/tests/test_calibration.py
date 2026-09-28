"""Routing 2 §5.7 — the calibration harness: deterministic checks, measured latency and tokens,
recorded per task class and model, advisory only (shown beside the ranking, never reordering it).
Only fixture models run here; a live campaign is Nick's call.
"""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from kel import calibration, staff, task_routing
from kel.core import Store


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ['CODEX_HOME'] = str(Path(self.tmp.name) / 'codex-home')
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)


class CheckTests(unittest.TestCase):
    def test_every_check_is_deterministic_and_says_what_it_proves(self):
        self.assertEqual(calibration.check('apple\nmango\npear', {'kind': 'regex', 'value': r'(?s)apple.*pear'})[0], True)
        self.assertEqual(calibration.check('{"name": "x", "country": "y"}', {'kind': 'json_keys',
                                                                          'value': ['name', 'country']}), (True, 'is JSON with name, country'))
        self.assertFalse(calibration.check('not json', {'kind': 'json_keys', 'value': ['name']})[0])
        self.assertFalse(calibration.check('1. a\n2. b\n3. c\n4. d', {'kind': 'not_regex', 'value': r'(?m)^\s*4[.)]'})[0])
        with self.assertRaises(ValueError):
            calibration.check('x', {'kind': 'vibes'})

    def test_the_fixture_answers_pass_their_own_suite(self):
        model = calibration.FixtureModel()
        for task in calibration.SUITE:
            text = model.execute(task['prompt'])['text']
            self.assertTrue(all(calibration.check(text, item)[0] for item in task['checks']), task['id'])


class RunTests(Base):
    def test_a_fixture_campaign_is_recorded_per_class_and_model(self):
        judged = []
        campaign = calibration.run(self.store, {'fixture-good': calibration.FixtureModel(),
                                                'fixture-weak': calibration.FixtureModel(wrong={'utility-json'})},
                                   judge=lambda task, text: judged.append(task['id']) or 1.0)
        self.assertTrue(campaign)
        out = calibration.summary(self.store)
        self.assertEqual(out['utility']['fixture-good']['pass_rate'], 1.0)
        self.assertEqual(out['utility']['fixture-weak']['pass_rate'], 0.5)
        self.assertFalse(out['utility']['fixture-good']['live'], 'fixture numbers are never measurements')
        self.assertIsNotNone(out['coding']['fixture-good']['avg_processed'])
        self.assertEqual(len(judged), 2 * len(calibration.SUITE), 'the judge sees every answer, beside the checks')
        self.assertEqual(calibration.summary(self.store, live_only=True), {})

    def test_results_are_advisory_and_never_reorder_the_ranking(self):
        from kel import role_models
        role_models.set_role(self.store, 'utility', 'automatic')
        adapters = {'codex', 'claude', 'deepseek'}
        before = [e['model'] for e in task_routing.ranking(self.store, 'utility', adapters=adapters)]

        class Failing:
            def execute(self, prompt, **kwargs):
                return {'outcome': 'SUCCESS', 'text': 'nope'}

        top = before[0]
        calibration.run(self.store, {top: Failing()}, live=True, task_classes=('utility',))
        after = [e['model'] for e in task_routing.ranking(self.store, 'utility', adapters=adapters)]
        self.assertEqual(before, after)
        view = task_routing.overview(self.store, adapters)
        utility = next(c for c in view['classes'] if c['task_class'] == 'utility')
        entry = next(m for m in utility['models'] if m['id'] == top)
        self.assertEqual(entry['calibration']['pass_rate'], 0.0)
        self.assertIn('advisory', view['calibration_note'])

    def test_the_command_line_runs_fixtures_only(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.assertEqual(calibration.main(['--data', str(Path(self.tmp.name) / 'cli'), '--fixture']), 0)
        self.assertIn('fixture-weak', buffer.getvalue())
        with self.assertRaises(SystemExit):
            with redirect_stdout(io.StringIO()):
                import contextlib
                with contextlib.redirect_stderr(io.StringIO()):
                    calibration.main(['--data', str(Path(self.tmp.name) / 'cli')])

    def test_the_migration_is_recorded_once(self):
        calibration.ensure_schema(self.store)
        calibration.ensure_schema(self.store)
        import contextlib
        with contextlib.closing(self.store.connect()) as db:
            rows = db.execute('SELECT name FROM schema_migrations WHERE version=37').fetchall()
        self.assertEqual([r['name'] for r in rows], ['v2-routing-2'])


if __name__ == '__main__':
    unittest.main()
