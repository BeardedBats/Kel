"""D-62 — General gets a default folder: Documents\\Kel Projects\\General, made when work needs it.

The suite runs with KEL_GENERAL_ROOT=none (conftest) so nothing touches the real Documents folder;
these tests point it at a temporary folder, or at a temporary USERPROFILE for the real default.
"""
import contextlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kel import projects as projects_module  # noqa: E402
from kel.context import Context  # noqa: E402
from kel.core import PolicyError, Store  # noqa: E402
from kel.projectmap import ProjectMap  # noqa: E402
from kel.projects import GENERAL, Projects, default_general_root, ensure_folder  # noqa: E402


class GeneralFolderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.base = Path(self.tmp.name)
        self.default = self.base / 'Documents' / 'Kel Projects' / 'General'
        env = patch.dict(os.environ, {'KEL_GENERAL_ROOT': str(self.default)})
        env.start()
        self.addCleanup(env.stop)

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def general_root(self, store):
        with contextlib.closing(store.connect()) as db:
            return db.execute('SELECT root FROM projects WHERE id=?', (GENERAL,)).fetchone()['root']

    def test_the_real_default_is_documents_kel_projects_general(self):
        with patch.dict(os.environ, {'USERPROFILE': str(self.base)}):
            os.environ.pop('KEL_GENERAL_ROOT', None)
            self.assertEqual(default_general_root(), self.base / 'Documents' / 'Kel Projects' / 'General')
        with patch.dict(os.environ, {'KEL_GENERAL_ROOT': 'none'}):
            self.assertIsNone(default_general_root())

    def test_a_fresh_install_gets_the_folder_as_general_root_without_creating_it(self):
        store = Store(self.base / 'data')
        Context(store)
        row = Projects(store).row(GENERAL)
        self.assertEqual(row['root'], str(self.default))
        self.assertFalse(row['has_folder'])
        self.assertFalse(self.default.exists(), 'the folder is made on demand, not at start-up')
        with contextlib.closing(store.connect()) as db:
            name = db.execute('SELECT name FROM schema_migrations WHERE version=35').fetchone()['name']
        self.assertEqual(name, 'v2-general-folder')

    def test_projects_before_context_still_gives_general_its_folder(self):
        store = Store(self.base / 'data')
        Projects(store)
        Context(store)  # its INSERT OR IGNORE must not replace the row the migration wrote
        self.assertEqual(self.general_root(store), str(self.default))

    def test_an_existing_install_without_a_general_folder_gets_one(self):
        with patch.dict(os.environ, {'KEL_GENERAL_ROOT': 'none'}):
            store = Store(self.base / 'data')
            Context(store)
            Projects(store)
        self.assertIsNone(self.general_root(store))
        with store.transaction() as db:  # an install from before D-62
            db.execute('DELETE FROM schema_migrations WHERE version=35')
        Projects(store)
        self.assertEqual(self.general_root(store), str(self.default))

    def test_a_folder_the_person_chose_is_never_replaced(self):
        mine = self.base / 'mine'
        mine.mkdir()
        with patch.dict(os.environ, {'KEL_GENERAL_ROOT': 'none'}):
            store = Store(self.base / 'data')
            Context(store)
            Projects(store).update(GENERAL, {'root': str(mine)})
        with store.transaction() as db:
            db.execute('DELETE FROM schema_migrations WHERE version=35')
        Projects(store)
        self.assertEqual(self.general_root(store), str(mine.resolve()))
        ensure_folder(store, str(self.default))
        self.assertFalse(self.default.exists(), 'only General\'s own default folder is ever made')

    def test_first_use_creates_the_folder_and_the_person_can_change_it(self):
        store = Store(self.base / 'data')
        Context(store)
        projects = Projects(store)
        ProjectMap(store).refresh(GENERAL, force=True)
        self.assertTrue(self.default.is_dir())
        self.assertTrue(projects.row(GENERAL)['has_folder'])
        other = self.base / 'elsewhere'
        other.mkdir()
        changed = projects.update(GENERAL, {'root': str(other)})
        self.assertEqual(changed['root'], str(other.resolve()))
        with self.assertRaises(PolicyError):
            projects.update(GENERAL, {'root': str(self.base / 'missing')})

    def test_ensure_folder_ignores_every_other_path(self):
        store = Store(self.base / 'data')
        Context(store)
        Projects(store)
        stranger = self.base / 'stranger'
        self.assertEqual(ensure_folder(store, str(stranger)), str(stranger))
        self.assertFalse(stranger.exists())
        self.assertIsNone(ensure_folder(store, None))

    def test_the_migration_marker_is_part_of_the_ledger(self):
        self.assertEqual(projects_module.GENERAL_FOLDER_VERSION, 35)


class GeneralRoutingTests(unittest.TestCase):
    """A greenfield request in General still makes its own project; General's folder stays unmade."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / 'home'
        self.default = self.home / 'Documents' / 'Kel Projects' / 'General'
        env = patch.dict(os.environ, {'KEL_GENERAL_ROOT': str(self.default), 'KEL_SKIP_TELEMETRY': '1',
                                      'KEL_REVIEWER': 'none', 'KEL_TURN_MODEL': 'none'})
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop('ANTHROPIC_API_KEY', None)
        from kel.service import Service
        self.service = Service(Path(self.tmp.name) / 'data')
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.service.shutdown()
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def test_greenfield_in_general_creates_its_own_project(self):
        import time
        self.assertEqual(Projects(self.service.store).row(GENERAL)['root'], str(self.default))
        with patch('pathlib.Path.home', return_value=self.home):
            sid = self.service.submit({'text': 'I want to create a little app that shows the weather',
                                       'conversation': 'main'})
            deadline = time.time() + 15
            state = None
            while time.time() < deadline:
                with contextlib.closing(self.service.store.connect()) as db:
                    state = db.execute('SELECT state FROM submissions WHERE id=?', (sid,)).fetchone()['state']
                if state not in ('PLANNING',):
                    break
                time.sleep(.05)
        self.assertEqual(state, 'DISPATCHED')
        jobs = [j for j in self.service.store.list_jobs() if j['conversation'] == 'main']
        self.assertEqual(len(jobs), 1)
        contract = jobs[0]['contract']
        self.assertTrue(contract.get('greenfield'))
        self.assertNotEqual(os.path.normcase(contract['root']), os.path.normcase(str(self.default)))
        self.assertFalse(self.default.exists(), 'a new project never writes into the General folder')


if __name__ == '__main__':
    unittest.main()
