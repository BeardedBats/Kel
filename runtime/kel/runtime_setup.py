"""Install the dedicated local runtime from pinned public packages."""
import contextlib
import hashlib
import io
import os
from pathlib import Path
import subprocess
import tarfile
import urllib.request
from .core import PolicyError
from .instance_lock import InstanceLock
from .wsl_runtime import DISTRO,LINUX_PATH,runtime_ready,wsl

ALPINE_URL='https://dl-cdn.alpinelinux.org/alpine/v3.22/releases/x86_64/alpine-minirootfs-3.22.5-x86_64.tar.gz'
ALPINE_SHA='4b4daa9fe2fc696c4919c4412a4c3d3e770d8fb70292a004a2c72f5096175282'


def ensure_runtime(data_root):
    folder=Path(data_root)/'runtime-setup';folder.mkdir(parents=True,exist_ok=True)
    lock=InstanceLock(folder)
    try:
        if not runtime_ready():
            result=subprocess.run(['wsl.exe','--list','--quiet'],capture_output=True,timeout=10,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            names=result.stdout.decode('utf-16-le',errors='replace')
            if DISTRO not in names:
                with urllib.request.urlopen(ALPINE_URL,timeout=30) as response:raw=response.read(10_000_001)
                if hashlib.sha256(raw).hexdigest()!=ALPINE_SHA:raise PolicyError('Runtime download did not match its pinned checksum')
                archive=folder/'base.tar'
                with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as src,tarfile.open(archive,'w') as dst:
                    for member in src:dst.addfile(member,src.extractfile(member) if member.isfile() else None)
                    settings=b'[automount]\nenabled=false\n[interop]\nenabled=false\nappendWindowsPath=false\n'
                    member=tarfile.TarInfo('etc/wsl.conf');member.size=len(settings);member.mode=0o644;dst.addfile(member,io.BytesIO(settings))
                result=subprocess.run(['wsl.exe','--import',DISTRO,str(folder/'distribution'),str(archive),'--version','2'],capture_output=True,timeout=120,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if result.returncode:raise PolicyError('Windows could not create the isolated runtime. WSL 2 must be available.')
            wsl(['/sbin/apk','add','--no-cache','python3','nodejs','npm','git','bash','bubblewrap','socat','util-linux','ca-certificates'],timeout=120)
            wsl(['/usr/bin/env','PATH='+LINUX_PATH,'npm','install','-g','@openai/codex@0.144.5','@anthropic-ai/claude-code@2.1.270'],timeout=120)
            wsl(['/usr/bin/env','PATH='+LINUX_PATH,'npm','install','--prefix','/opt/kel','@anthropic-ai/claude-agent-sdk@0.3.270'],timeout=120)
        auth=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'auth.json'
        if auth.is_file():
            # The official CLI consumes its existing sign-in. Never log its bytes.
            wsl(['/usr/bin/python3','-c',
                'import os,sys,tempfile;os.makedirs("/root/.codex",mode=0o700,exist_ok=True);fd,p=tempfile.mkstemp(dir="/root/.codex");os.write(fd,sys.stdin.buffer.read());os.close(fd);os.replace(p,"/root/.codex/auth.json")'],auth.read_bytes())
        if not runtime_ready():raise PolicyError('Isolated runtime checks failed; no unsafe fallback is enabled')
    finally:lock.close()
