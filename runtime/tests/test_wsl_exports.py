import io,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from kel.core import PolicyError
from kel.wsl_runtime import sync_out,command_argv

def archive(entries):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w') as out:
        for name,kind in entries:
            member=tarfile.TarInfo(name)
            if kind=='link':member.type=tarfile.SYMTYPE;member.linkname='/outside'
            else:member.size=2
            out.addfile(member,io.BytesIO(b'OK') if kind!='link' else None)
    return stream.getvalue()

class ExportTests(unittest.TestCase):
    def test_malicious_exports_never_change_original_files(self):
        cases=[[('../escape','file')],[('/absolute','file')],[('link','link')],[('A.txt','file'),('a.txt','file')],[('NUL.txt','file')],[('file.','file')]]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'original').write_text('KEEP')
            for entries in cases:
                with self.subTest(entries=entries),patch('kel.wsl_runtime.wsl',return_value=archive(entries)):
                    with self.assertRaises(PolicyError):sync_out('/work/test',root)
                    self.assertEqual((root/'original').read_text(),'KEEP')
    def test_windows_only_command_never_runs_outside_isolation(self):
        with self.assertRaises(PolicyError):command_argv(['powershell.exe','-Command','anything'])

if __name__=='__main__':unittest.main()
