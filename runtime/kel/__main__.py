"""A small one-voice terminal interface. Run python -m kel --help."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import threading
import time
from .core import Store, PolicyError, Conflict
from .engine import Engine, compile_document
from .internal import InternalAdapter
from .native import NativeAdapter, FixtureAdapter
from .commander import Commander


def adapters(root, fixture=False):
    if fixture:
        return {'fixture':FixtureAdapter(output='## Result\nThis is a local fixture document for recovery and verification checks.')}
    result={}
    for provider in ('codex','claude'):
        adapter=NativeAdapter(provider,root/'workspaces'/provider,root/'logs',timeout=90)
        if adapter.probe().get('installed'):result[provider]=adapter
    if os.environ.get('ANTHROPIC_API_KEY'):result['internal']=InternalAdapter()
    return result


def print_jobs(store):
    jobs=store.list_jobs()
    if not jobs:print('Kel: No saved jobs.')
    for j in jobs:
        print(f"{j['id'][:8]}  {j['state']:<17} {j['verdict']:<10} {j['contract']['request'][:70]}")


def resolve_job(store, prefix):
    matches=[j['id'] for j in store.list_jobs() if j['id'].startswith(prefix)]
    if len(matches)!=1:raise PolicyError('Use one unambiguous job ID')
    return matches[0]


def chat(store, workers):
    commander=Commander(workers['internal']) if 'internal' in workers else None
    engine=Engine(store,workers,reviewer=commander)
    stop=threading.Event()
    with contextlib.closing(store.connect()) as db:
        seen={r['id'] for r in db.execute('SELECT id FROM publications')}
    def background():
        while not stop.wait(.2):
            try:
                engine.tick()
                with contextlib.closing(store.connect()) as db:
                    publications=[dict(r) for r in db.execute('SELECT id,text FROM publications ORDER BY at')]
                for publication in publications:
                    if publication['id'] not in seen:
                        seen.add(publication['id']);print('\n'+publication['text'],flush=True)
            except Exception as exc:
                print('\nKel: Work paused by an engine error: '+str(exc))
                stop.set()
    t=threading.Thread(target=background,daemon=True);t.start()
    print('Kel compatibility prototype — one conversation, durable document jobs.')
    print('Type /help for commands. Jobs keep running while you type.')
    print('General document quality receives a separate review when the internal API is available.')
    try:
        while True:
            try:text=input('\nYou: ').strip()
            except EOFError:break
            if not text:continue
            if text in ('/quit','/exit'):break
            if text=='/help':
                print('Kel: /write REQUEST | /status | /show ID | /pause ID | /resume ID | /cancel ID | /quit')
            elif text in ('/status','status'):
                print_jobs(store)
            elif text.startswith('/show '):
                job=store.get(resolve_job(store,text.split(maxsplit=1)[1]))
                print(json.dumps(job,indent=2))
            elif text.startswith(('/pause ','/resume ','/cancel ')):
                action,prefix=text[1:].split(maxsplit=1)
                engine.control(resolve_job(store,prefix),action)
                print('Kel: '+action+' recorded.')
            elif text.startswith('/write '):
                request=text[7:].strip()
                contract,_=commander.plan(request) if commander else (compile_document(request),{})
                job=engine.submit(contract)
                print('Kel: Work saved as '+job[:8]+'. I will check the result before completion.')
            else:
                store.add_message(text)
                worker=workers.get('internal') or next(iter(workers.values()))
                answer=worker.execute('Answer this side question briefly. Do not start work or use tools.\n'+text)
                response=answer.get('text') if answer.get('outcome')=='SUCCESS' else 'The answer request failed; saved jobs are unchanged.'
                store.add_message(response,role='assistant')
                print('Kel: '+response)
    except (KeyboardInterrupt,PolicyError) as exc:
        print('\nKel: '+str(exc))
    finally:
        stop.set();t.join(timeout=95);engine.close()
        print('Kel: Active runs stopped and saved. Reopen to continue.')


def main():
    parser=argparse.ArgumentParser(description='Kel local compatibility prototype')
    parser.add_argument('--data',type=Path,default=Path(__file__).resolve().parents[1]/'data')
    sub=parser.add_subparsers(dest='command')
    sub.add_parser('chat');sub.add_parser('status');sub.add_parser('probe')
    sub.add_parser('rebuild');sub.add_parser('recover')
    demo=sub.add_parser('demo');demo.add_argument('--live',action='store_true')
    write=sub.add_parser('write');write.add_argument('request');write.add_argument('--provider',choices=['codex','claude','internal'])
    write.add_argument('--require',action='append',default=[]);write.add_argument('--timeout',type=int,default=120)
    write.add_argument('--plan',action='store_true',help='Use Commander to propose the document contract')
    args=parser.parse_args();store=Store(args.data)
    if args.command=='status':print_jobs(store);return
    if args.command=='rebuild':print('Rebuilt jobs:',store.rebuild());return
    if args.command=='recover':print('Fenced expired runs:',store.recover_expired());return
    if args.command=='probe':
        print(json.dumps({p:a.probe() for p,a in adapters(args.data).items() if hasattr(a,'probe')},indent=2));return
    workers=adapters(args.data,fixture=args.command=='demo' and not args.live)
    if not workers:raise SystemExit('No worker available. Run python -m kel demo for the offline fixture.')
    if args.command in (None,'chat'):chat(store,workers);return
    commander=Commander(workers['internal']) if 'internal' in workers else None
    engine=Engine(store,workers,reviewer=commander)
    try:
        if args.command=='demo':
            contract=compile_document('Write a short report with the heading ## Result.',required=['## Result'])
            job=engine.submit(contract)
        else:
            if args.plan:
                if not commander:raise PolicyError('Commander needs the internal API')
                contract,info=commander.plan(args.request)
                print('Contract proposal:',json.dumps(info))
            else:contract=compile_document(args.request,args.require)
            job=engine.submit(contract,args.provider)
        print('Saved job:',job,flush=True)
        result=engine.wait(job,getattr(args,'timeout',120))
        print_jobs(store)
        if result['state']=='CLOSED':print(store.publish(job)[0])
        else:print('Kel: Work remains saved. Inspect status for the remaining criteria.')
    finally:engine.close()


if __name__=='__main__':
    try:
        main()
    except Conflict as exc:
        print('Kel: '+str(exc))
        raise SystemExit(2)
