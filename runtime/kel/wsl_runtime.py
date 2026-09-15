"""Native coding in a dedicated WSL runtime without Windows drive mounts."""
import contextlib
import io
import json
import os
from pathlib import Path,PurePosixPath
import subprocess
import tarfile
import time
from .core import PolicyError,digest
from .coding import file_manifest
from .appserver import CodexConnection

DISTRO='KelV1Runtime'
LINUX_PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'

def wsl(args,input=None,timeout=30):
    result=subprocess.run(['wsl.exe','-d',DISTRO,'--exec',*args],input=input,capture_output=True,
        timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise PolicyError('Isolated runtime: '+result.stderr.decode('utf-8','replace')[:1000])
    return result.stdout


def runtime_ready():
    try:
        return wsl(['/bin/sh','-c','test ! -e /mnt/c && test ! -e /mnt/host/c && test -x /usr/bin/python3 && test -x /usr/local/bin/codex && test -x /usr/local/bin/claude && test -f /opt/kel/node_modules/@anthropic-ai/claude-agent-sdk/sdk.mjs && printf ready'],timeout=5)==b'ready'
    except (OSError,subprocess.SubprocessError,PolicyError):return False


def sync_in(local,remote):
    file_manifest(local)
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w') as archive:
        archive.add(local,arcname='.',recursive=True)
    if stream.tell()>100_000_000:raise PolicyError('Coding snapshot exceeds the 100 MB transfer limit')
    wsl(['/usr/bin/python3','-c',
        'import sys,tarfile,os;root=sys.argv[1];os.makedirs(root,exist_ok=False);tarfile.open(fileobj=sys.stdin.buffer,mode="r|*").extractall(root,filter="data")',remote],stream.getvalue())


def sync_out(remote,local):
    raw=wsl(['/usr/bin/python3','-c',
        'import sys,tarfile; a=tarfile.open(fileobj=sys.stdout.buffer,mode="w|");a.add(sys.argv[1],arcname=".",filter=lambda i: None if any(p in (".git","__pycache__",".pytest_cache","node_modules",".venv") for p in i.name.split("/")) else i);a.close()',remote])
    if len(raw)>100_000_000:raise PolicyError('Worker export exceeds the 100 MB evidence limit')
    contents={};folded=set()
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as archive:
        for member in archive:
            path=PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or any(':' in p or '\\' in p for p in path.parts):raise PolicyError('Worker export escaped its workspace')
            if member.isdir():continue
            if not member.isfile() or member.size>10_000_000:raise PolicyError('Worker exported a link, device, or oversized file')
            name=path.as_posix().removeprefix('./')
            if name.casefold() in folded or any(p.endswith(('.', ' ')) or p.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]} for p in path.parts):raise PolicyError('Worker export has an ambiguous Windows filename')
            folded.add(name.casefold())
            contents[name]=archive.extractfile(member).read()
    before=file_manifest(local)
    for name in before.keys()-contents.keys():(local/name).unlink()
    for name,content in contents.items():
        target=local/name;target.parent.mkdir(parents=True,exist_ok=True)
        if before.get(name)!=digest(content):target.write_bytes(content)
    file_manifest(local)


def command_argv(command):
    first=Path(command[0]).name.lower()
    if first in ('python','python3','python.exe','python3.exe'):return ['/usr/bin/python3',*command[1:]]
    if first in ('node','node.exe'):return ['/usr/bin/node',*command[1:]]
    if first in ('npm','npm.cmd','npm.exe'):return ['/usr/bin/npm',*command[1:]]
    if first in ('bash','sh','git','pytest'):return [first,*command[1:]]
    raise PolicyError('This test command needs a supported Linux runtime: Python, Node, npm, shell, Git, or pytest')


def stop_group(group):
    import re
    if not re.fullmatch('[a-f0-9]{32}',group):raise PolicyError('Invalid isolated worker group')
    code='''import pathlib,sys,time
p=pathlib.Path('/sys/fs/cgroup/kel-v1')/sys.argv[1]
if not p.exists():raise SystemExit(2)
(p/'cgroup.kill').write_text('1')
deadline=time.monotonic()+5
while 'populated 1' in (p/'cgroup.events').read_text():
 if time.monotonic()>deadline:raise SystemExit(3)
 time.sleep(.05)
print('STOPPED')
'''
    return wsl(['/usr/bin/python3','-c',code,group],timeout=10).strip()==b'STOPPED'


class WSLCodexConnection(CodexConnection):
    def __init__(self,workspace,logs,provider='codex'):
        self.provider=provider
        self.local=Path(workspace).resolve()
        self.group=digest(str(Path(logs).resolve()))[:32]
        self.remote='/work/'+digest(str(self.local))[:20]+'-'+self.group
        if not runtime_ready():raise PolicyError('The isolated coding runtime is unavailable. No Windows fallback is allowed.')
        exists=wsl(['/usr/bin/python3','-c','import os,sys;print(os.path.exists(sys.argv[1]))',self.remote]).strip()==b'True'
        if not exists:sync_in(self.local,self.remote)
        wrapper=Path(__file__).with_name('native_group.py').read_bytes()
        self.wrapper='/opt/kel/group-'+digest(wrapper)+'.py'
        wsl(['/usr/bin/python3','-c','import sys,os,tempfile;fd,p=tempfile.mkstemp(dir="/opt/kel");os.write(fd,sys.stdin.buffer.read());os.close(fd);os.replace(p,sys.argv[1])',self.wrapper],wrapper)
        profile={'/': 'deny',':minimal':'read','/usr':'read','/bin':'read','/lib':'read','/etc':'read',self.remote:'write'}
        toml='{'+','.join(json.dumps(k)+'='+json.dumps(v) for k,v in profile.items())+'}'
        argv=['wsl.exe','-d',DISTRO,'--cd',self.remote,'--exec','/usr/bin/env','-i','HOME=/root','PATH='+LINUX_PATH,
            'CODEX_HOME=/root/.codex','/usr/bin/python3',self.wrapper,self.group,'/usr/local/bin/codex','app-server','--stdio',
            '-c','web_search="disabled"','-c','analytics.enabled=false',
            '-c','shell_environment_policy.inherit="none"','-c','shell_environment_policy.set={PATH="'+LINUX_PATH+'",PYTHONDONTWRITEBYTECODE="1"}',
            '-c','default_permissions="kel-strict"','-c','permissions.kel-strict.filesystem='+toml,
            '-c','permissions.kel-strict.network.enabled=false']
        for feature in ('multi_agent','multi_agent_v2','apps','plugins','hooks','memories','browser_use','computer_use','image_generation','goals','in_app_browser','browser_use_external'):
            argv+=['--disable',feature]
        if provider=='claude':
            script=Path(__file__).with_name('native_claude.mjs').read_bytes()
            worker_script='/opt/kel/worker-'+digest(script)+'.mjs'
            wsl(['/usr/bin/python3','-c','import sys,pathlib,os,tempfile;raw=sys.stdin.buffer.read();fd,p=tempfile.mkstemp(dir="/opt/kel");os.write(fd,raw);os.close(fd);os.replace(p,sys.argv[1])',worker_script],script)
            argv=['wsl.exe','-d',DISTRO,'--cd',self.remote,'--exec','/usr/bin/env','-i','HOME=/root','PATH='+LINUX_PATH,'/usr/bin/python3',self.wrapper,self.group,'/usr/bin/node',worker_script]
        super().__init__(self.local,logs,process_argv=argv)

    def call(self,method,params,timeout=25):
        params=dict(params)
        if method=='initialize' and self.provider=='claude':params['apiKey']=os.environ.get('ANTHROPIC_API_KEY')
        if method in ('thread/start','thread/resume','turn/start','command/exec'):
            if 'cwd' in params:
                if params['cwd'] not in (str(self.local),self.remote):raise PolicyError('Native request changed workspace')
                params['cwd']=self.remote
            params.pop('sandbox',None);params.pop('sandboxPolicy',None)
            params['permissionProfile']='kel-strict'
        if method=='command/exec':
            params['command']=command_argv(params['command'])
            if self.provider=='claude':
                argv=['wsl.exe','-d',DISTRO,'--exec','/usr/bin/python3',self.wrapper,self.group,'/usr/bin/timeout','95','/usr/bin/bwrap',
                    '--unshare-all','--die-with-parent','--new-session','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib',
                    '--ro-bind','/bin','/bin','--ro-bind','/etc','/etc','--bind',self.remote,'/workspace',
                    '--proc','/proc','--dev','/dev','--tmpfs','/tmp','--chdir','/workspace','--cap-drop','ALL',
                    '--','/usr/bin/env','-i','PATH='+LINUX_PATH,'PYTHONDONTWRITEBYTECODE=1',*params['command']]
                out=self.logs/'trusted-tests.stdout';err=self.logs/'trusted-tests.stderr'
                with out.open('wb') as stdout,err.open('wb') as stderr:
                    p=subprocess.Popen(argv,stdout=stdout,stderr=stderr,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    deadline=time.monotonic()+100
                    while p.poll() is None:
                        if time.monotonic()>deadline or out.stat().st_size+err.stat().st_size>2_000_000:
                            p.kill();p.wait(timeout=5)
                            raise PolicyError('Isolated tests exceeded their time or output limit; no passing receipt was recorded')
                        time.sleep(.05)
                result={'exitCode':p.returncode,'stdout':out.read_text(encoding='utf-8',errors='replace'),'stderr':err.read_text(encoding='utf-8',errors='replace'),
                        '_kel_execution':{'runtime':'WSL 2 / Alpine 3.22.5','argv':params['command'],'cwd':'/workspace'}}
                sync_out(self.remote,self.local)
                return result
        result=super().call(method,params,timeout)
        if method=='command/exec':
            sync_out(self.remote,self.local)
            result['_kel_execution']={'runtime':'WSL 2 / Alpine 3.22.5','argv':params['command'],'cwd':self.remote}
        return result

    def before_event(self,event):
        if event.get('method')=='turn/completed':sync_out(self.remote,self.local)

    def close(self):
        try:stop_group(self.group)
        finally:super().close()
