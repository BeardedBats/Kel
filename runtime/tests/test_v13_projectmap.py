"""V1.3 Gate 3: durable project map (docs/v1.3/KEL_V1.3_ARCHITECTURE.md 2-4; MAP-01..07)."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import kel.projectmap as pm
from kel.core import Store
from kel.context import Context
from kel.projectmap import ProjectMap


class ProjectMapCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'proj'
        self.root.mkdir()
        (self.root / 'main.py').write_text('print(1)\n', encoding='utf-8')
        (self.root / 'tests').mkdir()
        (self.root / 'tests' / 'test_x.py').write_text(
            'def test_x():\n    assert True\n', encoding='utf-8')
        (self.root / 'package.json').write_text(json.dumps({
            'name': 'demo',
            'scripts': {'build': 'vite build', 'lint': 'oxlint', 'test': 'vitest run'},
            'dependencies': {'react': '^19.0.0', 'vite': '^7.0.0'}}), encoding='utf-8')
        (self.root / 'bun.lock').write_text('', encoding='utf-8')
        (self.root / 'tsconfig.json').write_text('{"compilerOptions":{}}', encoding='utf-8')
        (self.root / 'LICENSE').write_text('Apache-2.0\n', encoding='utf-8')
        for args in (['init', '-q'], ['config', 'user.email', 't@t'], ['config', 'user.name', 't'],
                     ['add', '-A'], ['commit', '-qm', 'init']):
            subprocess.run(['git', '-C', str(self.root), *args], check=True,
                           capture_output=True)
        self.store = Store(str(Path(self.temp.name) / 'data'))
        self.context = Context(self.store)
        self.pid = self.context.project('Demo', root=str(self.root), project_id='p1')
        self.maps = ProjectMap(self.store)

    def test_map01_commands_and_entry_points(self):
        latest = self.maps.refresh(self.pid, reason='test')
        commands = latest['sections']['execution']['content']['commands']
        self.assertEqual(commands['build'], 'bun run build')
        self.assertEqual(commands['lint'], 'bun run lint')
        self.assertEqual(commands['test'], 'bun run test')
        architecture = latest['sections']['architecture']['content']
        self.assertIn('main.py', architecture['entry_points'])
        self.assertIn('react', architecture['key_dependencies'])

    def test_map02_sources_and_trust_labels(self):
        latest = self.maps.refresh(self.pid)
        for name, section in latest['sections'].items():
            self.assertTrue(section['sources'], name)
            self.assertEqual(section['trust'], 'verified', name)
            self.assertIn('inputs', section)

    def test_map03_one_config_change_refreshes_only_affected_sections(self):
        first = self.maps.refresh(self.pid)
        with mock.patch.object(pm, '_inspect_execution', wraps=pm._inspect_execution) as spy, \
                mock.patch.object(pm, '_inspect_architecture',
                                  wraps=pm._inspect_architecture) as arch:
            (self.root / 'tsconfig.json').write_text('{"compilerOptions":{"strict":true}}',
                                                     encoding='utf-8')
            second = self.maps.refresh(self.pid)
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(arch.call_count, 0)
        self.assertEqual(second['sections']['architecture']['digest'],
                         first['sections']['architecture']['digest'])
        self.assertIn('execution', second['note'])

    def test_map04_stale_sections_for_changed_paths(self):
        self.maps.refresh(self.pid)
        self.assertEqual(self.maps.stale_sections(self.pid, ['tsconfig.json']), ['execution'])
        self.assertEqual(self.maps.stale_sections(self.pid, ['package.json']),
                         ['architecture', 'execution'])

    def test_map05_manual_refresh_and_unchanged_noop(self):
        first = self.maps.refresh(self.pid)
        again = self.maps.refresh(self.pid, reason='manual')
        self.assertEqual(again['version'], first['version'])
        self.assertIn('unchanged', again['note'])
        forced = self.maps.refresh(self.pid, force=True, reason='manual')
        self.assertEqual(forced['version'], first['version'] + 1)

    def test_map06_greenfield_project_map(self):
        green = Path(self.temp.name) / 'green'
        green.mkdir()
        subprocess.run(['git', '-C', str(green), 'init', '-q'], check=True, capture_output=True)
        pid = self.context.project('Green', root=str(green), project_id='g1')
        latest = self.maps.refresh(pid)
        self.assertEqual(latest['version'], 1)
        self.assertEqual(latest['sections']['execution']['content']['commands'], {})
        self.assertEqual(latest['sections']['identity']['content']['languages'], [])
        self.assertIsNone(latest['sections']['identity']['content']['repo'])

    def test_map07_no_rescan_when_nothing_changed(self):
        self.maps.refresh(self.pid)
        with mock.patch.object(pm, '_inspect_execution', wraps=pm._inspect_execution) as spy, \
                mock.patch.object(pm, '_inspect_identity', wraps=pm._inspect_identity) as ident:
            self.maps.refresh(self.pid)
        self.assertEqual(spy.call_count, 0)
        self.assertEqual(ident.call_count, 0)


if __name__ == '__main__':
    unittest.main()
