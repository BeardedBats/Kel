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
  self.validate=patch.object(release,'_validate_candidate');self.validator=self.validate.start();self.addCleanup(self.validate.stop)
 def stage(self):
  from kel.runner import process_identity
  sha,stamp=release.fingerprint(self.root);candidate=self.base/'Temp/Candidate-abc123';candidate.mkdir(parents=True)
  data={'release_id':'abc123','fix_id':'FIX-0001','job_id':'job-1','source_root':str(self.root),'source_sha':sha,'source_fingerprint':stamp,'state':'QUEUED','stage':'Queued','candidate_path':str(candidate),'installer_path':None,'installed':False,'created':1,'updated':1,'pid':os.getpid(),'owner':process_identity(os.getpid()),'error':None}
  with self.store.transaction() as db:db.execute('INSERT OR REPLACE INTO kibble_releases VALUES(?,?,?)',('FIX-0001','abc123',json.dumps(data)))
  return candidate
 def fake(self,command,cwd,log,**kwargs):
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
  self.assertTrue((candidate/'kibble-candidate.json').is_file());self.assertEqual(run.call_count,6)
  self.assertNotIn('build-with-builder.js',run.call_args_list[-1].args[0])
 def test_source_conflict_refuses_before_build(self):
  self.stage();(self.root/'source.txt').write_text('changed')
  with patch.object(release,'_run') as run:release._build(self.store,'FIX-0001','abc123')
  self.assertEqual(release.status(self.store,'FIX-0001')['state'],'FAILED');run.assert_not_called()
 def test_mid_build_conflict_never_becomes_ready(self):
  self.stage()
  def fake(command,cwd,log,**kwargs):
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
  self.assertTrue(config['win']['signAndEditExecutable'])

 def test_busy_recovery_requires_validation_and_runs_once(self):
  candidate=self.stage();config=release._config(self.root,candidate);log=candidate/'build.log'
  def run(command,cwd,log):
   if '--prepackaged' not in command:
    log.write_text('Error: EBUSY copy resource');raise PolicyError('tool failed')
  with patch.object(release,'_run',side_effect=run) as runner:
   release._package(self.root,candidate,config,log)
  self.assertEqual(runner.call_count,2)
  self.assertTrue(self.validator.call_args_list[0].kwargs['repair'])
  self.assertEqual(self.validator.call_count,2)

 def test_busy_incomplete_candidate_never_retries(self):
  candidate=self.stage();config=release._config(self.root,candidate);log=candidate/'build.log'
  def run(*args):log.write_text('EBUSY');raise PolicyError('tool failed')
  self.validator.side_effect=PolicyError('candidate resource mismatch')
  with patch.object(release,'_run',side_effect=run) as runner:
   with self.assertRaises(PolicyError):release._package(self.root,candidate,config,log)
  self.assertEqual(runner.call_count,1)

 def test_old_busy_or_other_failure_does_not_retry(self):
  candidate=self.stage();config=release._config(self.root,candidate);log=candidate/'build.log';log.write_text('old EBUSY\n')
  with patch.object(release,'_run',side_effect=PolicyError('other failure')) as runner:
   with self.assertRaises(PolicyError):release._package(self.root,candidate,config,log)
  self.assertEqual(runner.call_count,1);self.validator.assert_not_called()

 def test_busy_retry_failure_stops_without_third_attempt(self):
  candidate=self.stage();config=release._config(self.root,candidate);log=candidate/'build.log'
  def run(*args):log.write_text('EBUSY');raise PolicyError('tool failed')
  with patch.object(release,'_run',side_effect=run) as runner:
   with self.assertRaises(PolicyError):release._package(self.root,candidate,config,log)
  self.assertEqual(runner.call_count,2)

 def test_real_resource_hash_mismatch_blocks_node_and_retry(self):
  candidate=self.stage();source=self.root/'resource.bin';source.write_bytes(b'new')
  dest=candidate/'win-unpacked/resources/resource.bin';dest.parent.mkdir(parents=True);dest.write_bytes(b'old')
  config=candidate/'builder-config.json';config.write_text(json.dumps({'extraResources':[{'from':str(source),'to':'resource.bin'}]}))
  self.validate.stop()
  with patch.object(release,'_run') as runner:
   with self.assertRaises(PolicyError):release._validate_candidate(self.root,candidate,config,candidate/'build.log',repair=True)
  runner.assert_not_called()

 def test_full_checks_precede_build_and_use_isolated_guards(self):
  candidate=self.stage()
  with patch.object(release,'_run',side_effect=self.fake) as runner:release._build(self.store,'FIX-0001','abc123')
  calls=runner.call_args_list
  self.assertEqual(calls[0].args[0][:5],['python','-m','pytest','-q','tests'])
  self.assertIn('--basetemp',calls[0].args[0]);self.assertIn('--cache=false',calls[1].args[0])
  self.assertIn('--maxWorkers=1',calls[1].args[0]);self.assertIn('--noEmit',calls[2].args[0])
  self.assertIn('PyInstaller',calls[3].args[0])
  env=calls[0].kwargs['trusted_env'];self.assertEqual(env['KEL_TURN_MODEL'],'none')
  self.assertEqual(env['KEL_GENERAL_ROOT'],'none');self.assertEqual(env['KEL_CLI_WEB'],'0')
  self.assertTrue(Path(env['AIONUI_DATA_DIR']).is_relative_to(candidate));self.assertTrue(Path(env['KEL_MEMORY_ROOT']).is_relative_to(candidate))
  for name in ('APPDATA','LOCALAPPDATA','TEMP','TMP','KEL_HOST_DATA_DIR'):
   self.assertTrue(Path(env[name]).is_relative_to(candidate))

 def test_failed_full_check_prevents_build_and_package(self):
  self.stage()
  with patch.object(release,'_run',side_effect=PolicyError('A full check failed.')) as runner:
   release._build(self.store,'FIX-0001','abc123')
  runner.assert_called_once();self.assertEqual(release.status(self.store,'FIX-0001')['state'],'FAILED')
  self.validator.assert_not_called()

 def test_old_running_engine_never_claims_new_marker_installed(self):
  candidate=self.stage()
  with patch.object(release,'_run',side_effect=self.fake):release._build(self.store,'FIX-0001','abc123')
  app=self.base/'App/resources';app.mkdir(parents=True)
  (app/'kibble-installed-update.json').write_bytes((candidate/'kibble-installed-update.json').read_bytes())
  engine=app/'kel-engine/KelEngine.exe';engine.parent.mkdir();engine.write_bytes(b'new engine')
  with patch.object(release.sys,'frozen',True,create=True),patch.object(release.sys,'executable',str(engine)),patch.object(release,'_launched_after',return_value=False):
   self.assertFalse(release.status(self.store,'FIX-0001')['installed'])
