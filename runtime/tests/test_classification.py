"""Routing 2 §5.5 — the turn model's reading classifies the work; the regex floors are a safety net.

The model says what kind of work it is (research, coding, design, writing, utility) and its tier
(fast, standard, deep). Floors may force coding (a code change in a project Kel can test, an explicit
coding request, a new app) or research (an explicit research request), never downgrade the model's
coding or research to writing, and classify on their own only when no model reading exists.
No provider is called.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from kel import staff, turn
from kel.coding import git


class FakeTurn:
    def __init__(self, answer):
        self.answer = answer

    def execute(self, prompt, system=None, images=None, **kwargs):
        return {'outcome': 'SUCCESS', 'text': json.dumps(self.answer)}


PACKET = {'project': {'name': 'Home', 'decisions': ''}, 'history': [], 'files': []}


class DecideTests(unittest.TestCase):
    def test_the_model_names_the_class_and_tier(self):
        out = turn.decide(FakeTurn({'action': 'start_background_work', 'title': 'Compare phone plans',
                                    'acknowledgement': "I'm starting on that now in the background.",
                                    'task_class': 'research', 'tier': 'deep'}), PACKET, 'Compare plans', [])
        self.assertEqual((out['action'], out['task_class'], out['tier']), ('start_background_work', 'research', 'deep'))

    def test_unknown_values_are_ignored(self):
        self.assertEqual(turn.classification({'task_class': 'hacking', 'tier': 'ultra'}), {})
        self.assertEqual(turn.classification({'task_class': 'Design', 'tier': 'FAST'}),
                         {'task_class': 'design', 'tier': 'fast'})
        out = turn.decide(FakeTurn({'action': 'start_background_work', 'title': 'x', 'task_class': 42}),
                          PACKET, 'Do a thing', [])
        self.assertNotIn('task_class', out)

    def test_the_prompt_asks_for_the_class(self):
        self.assertIn('"task_class"', turn.TURN_SYSTEM)
        self.assertIn('"tier"', turn.TURN_SYSTEM)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        from kel.service import Service
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none',
                          CODEX_HOME=str(Path(self.tmp.name) / 'codex-home'))
        os.environ.pop('ANTHROPIC_API_KEY', None)
        os.environ.pop('KEL_WORKFORCE', None)
        self.service = Service(Path(self.tmp.name) / 'data')
        self.addCleanup(self.service.shutdown)
        root = Path(self.tmp.name) / 'proj'
        root.mkdir()
        (root / 'calc.py').write_text('def add(a, b):\n    return a + b\n')
        git(root, 'init')
        git(root, 'add', '-A')
        git(root, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost', 'commit', '-m', 'base')
        self.project = self.service.projects.create('Calc', root=str(root), test_command=['python', '-c', 'pass'])
        self.packet = {'project': {'id': self.project['id'], 'root': self.project['root']}, 'files': [],
                       'kind_source': 'router'}

    def classify(self, text, decision, kind='conversation', packet=None):
        packet = dict(packet or self.packet)
        return self.service._classify('s-none', text, packet, kind, False, decision), packet

    def test_the_models_reading_is_primary(self):
        out, _ = self.classify('What are the best budget laptops right now?', {'task_class': 'research', 'tier': 'standard'})
        self.assertEqual((out['task_class'], out['source']), ('research', 'model'))
        out, _ = self.classify('Make my about page feel warmer', {'task_class': 'design', 'tier': 'fast'})
        self.assertEqual((out['task_class'], out['tier']), ('design', 'fast'))

    def test_a_floor_forces_coding_but_never_downgrades(self):
        measured = 'In this project, add a multiply(a, b) function to calc.py and a pytest test for it.'
        out, _ = self.classify(measured, {'task_class': 'writing'})
        self.assertEqual((out['task_class'], out['forced_by']), ('coding', 'floor'))
        out, _ = self.classify('research the history of calc.py style guides', {'task_class': 'coding'})
        self.assertEqual(out['task_class'], 'coding', "the model's coding is never turned into something else")
        out, _ = self.classify('Draft a note to the team', {'task_class': 'research'})
        self.assertEqual(out['task_class'], 'research', "a floor never turns the model's research into writing")

    def test_without_a_model_the_floors_classify(self):
        self.assertEqual(self.classify('research the best hiking boots', {})[0]['task_class'], 'research')
        self.assertEqual(self.classify('Rename these headings to title case', {})[0]['task_class'], 'utility')
        self.assertEqual(self.classify('Write a short poem about rain', {})[0]['source'], 'floors')

    def test_the_class_decides_what_compiles(self):
        _, packet = self.classify('Find out what changed in the latest tax rules', {'task_class': 'research'})
        contract = self.service._compile_work('s1', 'main', 'Find out what changed in the latest tax rules',
                                              packet, 'conversation', False)
        self.assertEqual(contract['kind'], 'research')
        self.assertEqual(contract['classification']['task_class'], 'research')
        measured = 'In this project, add a multiply(a, b) function to calc.py and a pytest test for it.'
        _, packet = self.classify(measured, {'task_class': 'coding', 'tier': 'standard'})
        contract = self.service._compile_work('s2', 'main', measured, packet, 'conversation', False)
        self.assertEqual(contract['kind'], 'coding')

    def test_staffing_uses_the_class_for_the_role_and_tier(self):
        contract = {'request': 'Make the landing copy friendlier', 'milestones': [
            {'id': 'd', 'objective': 'x', 'filename': 'd.md', 'depends_on': [], 'checks': []}],
            'classification': {'task_class': 'design', 'tier': 'deep'}}
        record = staff.plan_job(self.service.store, contract)
        self.assertEqual(record['steps']['d']['dispatch'], 'deep')
        milestone = contract['milestones'][0]
        self.assertEqual(staff._role_for_step('writing', milestone, 'D1', False, 'plain text', None, 'design'),
                         'designer')
        self.assertEqual(staff._role_for_step('writing', milestone, 'D1', True, 'a new screen layout', None,
                                              'writing'), 'writer', "the model's class outranks the word list (D-88)")
        self.assertEqual(staff._role_for_step('writing', milestone, 'D1', False, 'plain text', None, 'utility'),
                         'utility')

if __name__ == '__main__':
    unittest.main()
