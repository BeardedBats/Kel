from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from kel.core import Store, Conflict
from kel.engine import Engine
from kel.native import FixtureAdapter


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_stale_database_lease_does_not_block_startup(self):
        self.store.controller_lease('dead-process')
        engine = Engine(self.store, {'fixture': FixtureAdapter()})
        engine.close()

    def test_live_instance_still_blocks_second_instance(self):
        engine = Engine(self.store, {'fixture': FixtureAdapter()})
        try:
            with self.assertRaises(Conflict):
                Engine(self.store, {'fixture': FixtureAdapter()})
        finally:
            engine.close()

    def test_abrupt_exit_releases_kernel_lock_immediately(self):
        script = "from kel.core import Store; from kel.engine import Engine; import os,sys; e=Engine(Store(sys.argv[1]),{}); os._exit(23)"
        result = subprocess.run([sys.executable,'-c',script,self.temp.name],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,23,result.stderr)
        engine = Engine(self.store, {'fixture': FixtureAdapter()})
        engine.close()

    def test_duplicate_cli_reports_message_without_traceback(self):
        engine = Engine(self.store, {'fixture': FixtureAdapter()})
        try:
            p = subprocess.run([sys.executable,'-m','kel','--data',self.temp.name,'demo'],capture_output=True,text=True,timeout=10)
            self.assertEqual(p.returncode,2)
            self.assertIn('already open',p.stdout)
            self.assertNotIn('Traceback',p.stdout+p.stderr)
        finally:
            engine.close()
