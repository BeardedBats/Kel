"""Upgrade only a known idle legacy engine; keep a consistent SQLite backup."""
import contextlib
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
from .core import PolicyError
from .runner import process_identity,terminate_known_process

LEGACY_HASHES={'29ccd59d5adabb2e715708e8f5170d9505b4a26c59e363591631bc83697adc7c':'0.2.1'}


def image_path(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:raise PolicyError('Legacy engine process is no longer available')
    try:
        buffer=ctypes.create_unicode_buffer(32768);length=wintypes.DWORD(len(buffer))
        if not kernel.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(length)):raise PolicyError('Cannot identify the legacy executable')
        return Path(buffer.value)
    finally:kernel.CloseHandle(handle)


def require_idle(db):
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {'runs','jobs','effects','submissions'}.issubset(tables):raise PolicyError('Legacy data format is not recognized')
    if db.execute("SELECT count(*) FROM runs WHERE state IN ('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED','ORPHANED')").fetchone()[0]:raise PolicyError('Legacy worker has active or unresolved work')
    if db.execute("SELECT count(*) FROM submissions WHERE state='PLANNING'").fetchone()[0]:raise PolicyError('Legacy planning is still running')
    if db.execute("SELECT count(*) FROM effects WHERE state!='OBSERVED'").fetchone()[0]:raise PolicyError('An external effect needs reconciliation before migration')
    for row in db.execute('SELECT data FROM jobs'):
        if json.loads(row[0])['state'] not in ('CLOSED','CANCELLED'):raise PolicyError('Finish or cancel legacy work before this update')


def migrate_idle(root,pid):
    if os.name!='nt':raise PolicyError('This migration is for the known Windows 0.2.1 engine')
    root=Path(root).resolve(strict=True)
    descriptor=json.loads((root/'desktop-session.json').read_text())
    if descriptor.get('pid')!=pid:raise PolicyError('Legacy service identity changed')
    identity=process_identity(pid)
    binary=image_path(pid)
    if binary.name.lower()!='kelengine.exe' or hashlib.sha256(binary.read_bytes()).hexdigest() not in LEGACY_HASHES:
        raise PolicyError('Unknown legacy engine. Automatic termination is not authorized for this executable.')
    if not identity:raise PolicyError('Cannot prove legacy process ownership')
    query=f'(Get-CimInstance Win32_Process -Filter "ProcessId={int(pid)}").CommandLine | ConvertTo-Json -Compress'
    result=subprocess.run(['powershell.exe','-NoProfile','-Command',query],capture_output=True,text=True,timeout=10,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    command=json.loads(result.stdout)
    shell=ctypes.WinDLL('shell32');shell.CommandLineToArgvW.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype=ctypes.POINTER(wintypes.LPWSTR)
    count=ctypes.c_int();values=shell.CommandLineToArgvW(command,ctypes.byref(count))
    try:args=[values[i] for i in range(count.value)]
    finally:
        kernel=ctypes.WinDLL('kernel32');kernel.LocalFree.argtypes=[wintypes.HLOCAL];kernel.LocalFree(values)
    if '--data' not in args or Path(args[args.index('--data')+1]).resolve()!=root:
        raise PolicyError('Legacy process belongs to another data folder')
    path=root/'kel.sqlite3'
    backup=root/'migration-backups'/('0.2.1-'+str(time.time_ns())+'.sqlite3');backup.parent.mkdir(exist_ok=True)
    with contextlib.closing(sqlite3.connect(path,timeout=10,isolation_level=None)) as barrier:
        barrier.execute('BEGIN IMMEDIATE')
        try:
            require_idle(barrier)
            with contextlib.closing(sqlite3.connect(path)) as source,contextlib.closing(sqlite3.connect(backup)) as target:
                source.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise PolicyError('Migration backup failed its integrity check')
            if not terminate_known_process(pid,identity):raise PolicyError('Legacy engine identity changed before shutdown')
        finally:barrier.rollback()
    deadline=time.monotonic()+5
    while process_identity(pid)==identity:
        if time.monotonic()>deadline:raise PolicyError('Legacy engine has not stopped')
        time.sleep(.05)
    # Windows can briefly retain the terminated process's WAL mapping. Wait for
    # a usable database before the desktop starts its replacement controller.
    ready_deadline=time.monotonic()+5
    while True:
        try:
            with contextlib.closing(sqlite3.connect(path,timeout=1)) as check:
                check.execute('PRAGMA synchronous=FULL')
                check.execute('PRAGMA wal_checkpoint(TRUNCATE)')
                if check.execute('PRAGMA journal_mode=DELETE').fetchone()[0].lower()!='delete':
                    raise sqlite3.OperationalError('Legacy WAL is still in use')
                if check.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise PolicyError('Migrated database failed its integrity check')
            break
        except sqlite3.OperationalError:
            if time.monotonic()>ready_deadline:raise
            time.sleep(.15)
    result={'from_version':'0.2.1','backup':str(backup),'state':'READY_FOR_CURRENT_ENGINE'}
    (root/'migration-receipt.json').write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--data',required=True);parser.add_argument('--pid',type=int,required=True)
    args=parser.parse_args();print(json.dumps(migrate_idle(args.data,args.pid)))
