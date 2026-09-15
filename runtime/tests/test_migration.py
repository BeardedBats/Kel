import sqlite3,unittest,json
from kel.core import PolicyError
from kel.migration import require_idle

class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript('CREATE TABLE runs(state TEXT);CREATE TABLE jobs(data TEXT);CREATE TABLE effects(state TEXT);CREATE TABLE submissions(state TEXT);')
    def tearDown(self):self.db.close()
    def test_active_or_unresolved_states_block_upgrade(self):
        for table,column,value in [('runs','state','RUNNING'),('runs','state','ORPHANED'),('effects','state','SUBMITTED'),('submissions','state','PLANNING'),('jobs','data',json.dumps({'state':'PAUSED'}))]:
            self.db.execute('INSERT INTO '+table+' VALUES(?)',(value,))
            with self.assertRaises(PolicyError):require_idle(self.db)
            self.db.execute('DELETE FROM '+table)
    def test_closed_work_migrates(self):
        self.db.execute('INSERT INTO jobs VALUES(?)',(json.dumps({'state':'CLOSED'}),))
        require_idle(self.db)

if __name__=='__main__':unittest.main()
