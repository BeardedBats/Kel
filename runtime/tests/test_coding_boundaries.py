import os
from pathlib import Path
import tempfile
import unittest
from kel.coding import file_manifest,snapshot,git
from kel.core import PolicyError


class CodingBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.source=self.root/'source';self.source.mkdir()
        self.outside=self.root/'outside';self.outside.mkdir()
        (self.outside/'private.txt').write_text('OUTSIDE-47')
        self.links=[]

    def tearDown(self):
        for link in self.links:
            if link.is_junction():os.rmdir(link)
            elif link.is_symlink():link.unlink()
        self.temp.cleanup()

    def directory_link(self,path,target):
        if os.name=='nt':
            import _winapi
            _winapi.CreateJunction(str(target),str(path))
        else:path.symlink_to(target,target_is_directory=True)
        self.links.append(path)

    def repo(self):
        (self.source/'app.py').write_text('answer=1\n')
        git(self.source,'init');git(self.source,'add','-A')
        git(self.source,'-c','user.name=Test','-c','user.email=test@localhost','commit','-m','fixture')

    def test_excluded_folder_junction_is_rejected(self):
        self.directory_link(self.source/'node_modules',self.outside)
        with self.assertRaises(PolicyError):file_manifest(self.source)
        self.assertEqual((self.outside/'private.txt').read_text(),'OUTSIDE-47')

    def test_link_nested_in_excluded_folder_is_rejected(self):
        folder=self.source/'node_modules';folder.mkdir()
        self.directory_link(folder/'escape',self.outside)
        with self.assertRaises(PolicyError):file_manifest(self.source)

    def test_hard_link_to_outside_is_rejected(self):
        os.link(self.outside/'private.txt',self.source/'alias.txt')
        with self.assertRaises(PolicyError):file_manifest(self.source)

    def test_source_link_rejected_before_snapshot_creation(self):
        self.repo()
        self.directory_link(self.source/'escape',self.outside)
        target=self.root/'snapshot'
        with self.assertRaises(PolicyError):snapshot(self.source,target)
        self.assertFalse(target.exists())

    def test_tracked_link_mode_is_rejected_even_if_materialized_as_text(self):
        self.repo()
        blob=git(self.source,'hash-object','-w','--stdin',input=b'../outside/private.txt').decode().strip()
        git(self.source,'update-index','--add','--cacheinfo','120000',blob,'alias')
        target=self.root/'snapshot'
        with self.assertRaises(PolicyError):snapshot(self.source,target)
        self.assertFalse(target.exists())

    def test_snapshot_preserves_dirty_and_untracked_source_without_aliases(self):
        self.repo()
        (self.source/'app.py').write_text('answer=2\n')
        (self.source/'notes.txt').write_text('local notes')
        before=file_manifest(self.source);target=self.root/'snapshot'
        snapshot(self.source,target)
        self.assertEqual(file_manifest(target),before)
        (target/'app.py').write_text('answer=3\n')
        self.assertEqual(file_manifest(self.source),before)

    def test_snapshot_preserves_crlf_and_disables_implicit_conversion(self):
        self.repo()
        (self.source/'test_example.py').write_bytes(b'answer=1\r\n')
        git(self.source,'add','-A')
        git(self.source,'-c','user.name=Test','-c','user.email=test@localhost','commit','-m','CRLF fixture')
        before=file_manifest(self.source);target=self.root/'snapshot'
        snapshot(self.source,target)
        self.assertEqual(file_manifest(target),before)
        self.assertEqual(git(target,'config','core.autocrlf').strip(),b'false')


if __name__=='__main__':unittest.main()
