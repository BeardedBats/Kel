"""Real stage metadata and scratch Git; fake build tools, no App or Data replacement."""
import json,os,subprocess,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from kel.core import Store,PolicyError
from kel import kibble_release as release

class ReleaseTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='kel-release-test-');self.addCleanup(self.tmp.cleanup)
  self.base=Path(self.tmp.name);self.root=self.base/'Kel';self.root.mkdir()
  subprocess.run(['git','init','-q',str(self.root)],check=True)
  (self.root/'source.txt').write_text('original');(self.root/'.gitignore').write_text('dist/\ndesktop/out/\n')
  subprocess.run(['git','-C',str(self.root),'add','.'],check=True)
  subprocess.run(['git','-C',str(self.root),'-c','user.name=Audit','-c','user.email=audit@example.test','commit','-qm','baseline'],check=True)
  self.store=Store(self.base/'Data/engine');release.ensure(self.store)
  self.service=Mock(store=self.store,handoff_lock=threading.RLock())
  self.job={'id':'job-1','verdict':'VERIFIED','contract':{'root':str(self.root),'context':{'kibble':{'fix_id':'FIX-0001'}}}}
  self.store.get=Mock(return_value=self.job)
 def stage(self):
  from kel.runner import process_identity
  sha,stamp=release.fingerprint(self.root);candidate=self.base/'Temp/Candidate-abc123';candidate.mkdir(parents=True)
  data={'release_id':'abc123','fix_id':'FIX-0001','job_id':'job-1','source_root':str(self.root),'source_sha':sha,'source_fingerprint':stamp,'state':'QUEUED','stage':'Queued','candidate_path':str(candidate),'installer_path':None,'installed':False,'created':1,'updated':1,'pid':os.getpid(),'owner':process_identity(os.getpid()),'error':None}
  with self.store.transaction() as db:db.execute('INSERT OR REPLACE INTO kibble_releases VALUES(?,?,?)',('FIX-0001','abc123',json.dumps(data)))
  return candidate
 def fake(self,command,cwd,log):
  with log.open('a') as out:out.write('fake process output\n')
  if 'nsis' in command:
   candidate=Path(json.loads(Path(command[command.index('--config')+1]).read_text())['directories']['output'])
   for name in ['win-unpacked/Kel.exe','win-unpacked/resources/app.asar','win-unpacked/resources/kel-engine/KelEngine.exe','Kel-Kibble-Update-1.7.0-x64.exe']:
    p=candidate/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fake artifact')
 def test_ready_has_artifacts_digest_and_log_without_installing(self):
  candidate=self.stage()
  with patch.object(release,'_run',side_effect=self.fake) as run:release._build(self.store,'FIX-0001','abc123')
  data=release.status(self.store,'FIX-0001');self.assertEqual(data['state'],'READY');self.assertFalse(data['installed'])
  self.assertTrue(Path(data['installer_path']).is_file());self.assertEqual(len(data['installer_sha256']),64)
  self.assertIn('fake process output',data['log']);self.assertFalse((self.base/'App').exists())
  self.assertTrue((candidate/'kibble-candidate.json').is_file());self.assertEqual(run.call_count,3)
  self.assertNotIn('build-with-builder.js',run.call_args_list[-1].args[0])
 def test_source_conflict_refuses_before_build(self):
  self.stage();(self.root/'source.txt').write_text('changed')
  with patch.object(release,'_run') as run:release._build(self.store,'FIX-0001','abc123')
  self.assertEqual(release.status(self.store,'FIX-0001')['state'],'FAILED');run.assert_not_called()
 def test_mid_build_conflict_never_becomes_ready(self):
  self.stage()
  def fake(command,cwd,log):
   self.fake(command,cwd,log)
   if 'nsis' in command:(self.root/'source.txt').write_text('concurrent edit')
  with patch.object(release,'_run',side_effect=fake):release._build(self.store,'FIX-0001','abc123')
  data=release.status(self.store,'FIX-0001');self.assertEqual(data['state'],'FAILED');self.assertIsNone(data['installer_path'])
 def test_tool_failure_persists_across_store_reopen(self):
  self.stage()
  with patch.object(release,'_run',side_effect=PolicyError('The tool failed.')):release._build(self.store,'FIX-0001','abc123')
  data=release.status(Store(self.store.root),'FIX-0001');self.assertEqual(data['state'],'FAILED');self.assertEqual(data['error'],'The tool failed.')
 def test_missing_package_parts_never_ready(self):
  self.stage()
  with patch.object(release,'_run'):release._build(self.store,'FIX-0001','abc123')
  self.assertEqual(release.status(self.store,'FIX-0001')['state'],'FAILED')
 def test_fingerprint_tracks_new_and_deleted_source(self):
  before=release.fingerprint(self.root)[1];(self.root/'new.py').write_text('new')
  self.assertNotEqual(before,release.fingerprint(self.root)[1]);(self.root/'new.py').unlink()
  self.assertEqual(before,release.fingerprint(self.root)[1]);(self.root/'source.txt').unlink()
  self.assertNotEqual(before,release.fingerprint(self.root)[1])
 def test_dead_owner_and_bounded_log(self):
  candidate=self.stage();(candidate/'build.log').write_text('\n'.join(str(n) for n in range(1000)))
  with patch.object(release,'_owner_alive',return_value=False):data=release.status(self.store,'FIX-0001')
  self.assertEqual(data['state'],'INTERRUPTED');self.assertEqual(len(data['log']),60);self.assertEqual(data['log'][-1],'999')
 def test_requires_verified_explicit_apply_and_matching_finding(self):
  app={'state':'APPLIED','root':str(self.root),'auto':False}
  with patch('kel.kibble_work.progress',return_value={'job_id':'job-1'}),patch('kel.kibble_work.source_root',return_value=self.root),patch('kel.auto_apply.describe',return_value={'job-1':app}):
   self.assertEqual(release._checked_root(self.service,'FIX-0001'),(self.root,'job-1'));app['auto']=True
   with self.assertRaises(PolicyError):release._checked_root(self.service,'FIX-0001')
   app['auto']=False;self.job['verdict']='UNCERTAIN'
   with self.assertRaises(PolicyError):release._checked_root(self.service,'FIX-0001')
   self.job['verdict']='VERIFIED'
   with self.assertRaises(PolicyError):release._checked_root(self.service,'FIX-0002')
 def test_duplicate_start_reuses_active_release(self):
  self.stage()
  with patch.object(release,'_checked_root') as checked,patch.object(release,'_launch') as thread:data=release.start(self.service,'FIX-0001')
  self.assertEqual(data['release_id'],'abc123');checked.assert_not_called();thread.assert_not_called()
 def test_start_records_candidate_and_launches_background_builder(self):
  with patch.object(release,'_checked_root',return_value=(self.root,'job-1')),patch.object(release,'_launch') as thread:data=release.start(self.service,'FIX-0001')
  self.assertEqual(data['state'],'QUEUED');self.assertEqual(Path(data['candidate_path']).parent,self.base/'Temp')
  thread.assert_called_once();self.assertFalse(data['installed'])

 def test_installed_requires_matching_marker_and_new_packaged_engine(self):
  candidate=self.stage()
  with patch.object(release,'_run',side_effect=self.fake):release._build(self.store,'FIX-0001','abc123')
  data=release.status(self.store,'FIX-0001')
  marker=json.loads((candidate/'kibble-installed-update.json').read_text())
  app=self.base/'App/resources';app.mkdir(parents=True)
  (app/'kibble-installed-update.json').write_text(json.dumps(marker))
  engine=app/'kel-engine/KelEngine.exe';engine.parent.mkdir();engine.write_bytes(b'new engine')
  self.assertFalse(release._installed(data))
  with patch.object(release.sys,'frozen',True,create=True),patch.object(release.sys,'executable',str(engine)),patch.object(release,'_launched_after',return_value=True):
   self.assertTrue(release.status(self.store,'FIX-0001')['installed'])
   marker['release_id']='another-update';(app/'kibble-installed-update.json').write_text(json.dumps(marker))
   self.assertFalse(release.status(self.store,'FIX-0001')['installed'])
 def test_changed_repaired_file_requires_check_again(self):
  from kel.core import digest
  app={'state':'APPLIED','root':str(self.root),'auto':False}
  journal={'plan':{'changes':{'source.txt':{'after':digest(b'original')}}}}
  with patch('kel.kibble_work.progress',return_value={'job_id':'job-1'}),patch('kel.kibble_work.source_root',return_value=self.root),patch('kel.auto_apply.describe',return_value={'job-1':app}),patch('kel.apply_changes.application',return_value=journal):
   release._checked_root(self.service,'FIX-0001');(self.root/'source.txt').write_text('changed later')
   with self.assertRaises(PolicyError):release._checked_root(self.service,'FIX-0001')
 def test_build_config_includes_marker_and_required_runtime_resources(self):
  candidate=self.stage();config=json.loads(release._config(self.root,candidate).read_text())
  names={entry['to'] for entry in config['extraResources']}
  self.assertTrue({'kibble-installed-update.json','kel-engine','bundled-aioncore','hub'}.issubset(names))
  self.assertIsNone(config['publish']);self.assertEqual(Path(config['directories']['output']),candidate)

 def test_old_running_engine_never_claims_new_marker_installed(self):
  candidate=self.stage()
  with patch.object(release,'_run',side_effect=self.fake):release._build(self.store,'FIX-0001','abc123')
  app=self.base/'App/resources';app.mkdir(parents=True)
  (app/'kibble-installed-update.json').write_bytes((candidate/'kibble-installed-update.json').read_bytes())
  engine=app/'kel-engine/KelEngine.exe';engine.parent.mkdir();engine.write_bytes(b'new engine')
  with patch.object(release.sys,'frozen',True,create=True),patch.object(release.sys,'executable',str(engine)),patch.object(release,'_launched_after',return_value=False):
   self.assertFalse(release.status(self.store,'FIX-0001')['installed'])
