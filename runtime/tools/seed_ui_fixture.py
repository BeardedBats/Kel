"""Seed an isolated Kel data dir with representative UI fixture states.

Usage (run from runtime/):
    python tools/seed_ui_fixture.py --data <isolated-data-dir> [--project-root <dir>]

Creates, through real production code paths (Store / Context / Memory):
  - conversations with messages (conversation list + chat states)
  - a PAUSED job with an UNCERTAIN milestone (Continue-work / Work states)
  - an AWAITING_USER job with a PENDING approval (approval badge + panel)
  - memory records with mixed type/trust levels (Knowledge panel states)

Safety: refuses to run unless the data dir is inside a `dev-tools` run
directory; intended for isolated capture runs only, never live user data.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def contract(request='Do the work'):
    return {'request': request,
            'milestones': [{'id': 'm1', 'objective': 'Draft the thing', 'filename': 'out.md',
                            'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 40}]}]}


def seed_job(store, conversation, **changes):
    job_id = store.create(contract(), conversation=conversation)
    with store.transaction() as db:
        job = store._get(db, job_id)
        for key in ('state', 'verdict'):
            if key in changes:
                job[key] = changes[key]
        for mid, patch_ in (changes.get('milestones') or {}).items():
            job['milestones'][mid].update(patch_)
        store._save(db, job, 'fixture.seed')
    return job_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--project-root', default=None)
    args = ap.parse_args()
    data = Path(args.data).resolve()
    if 'dev-tools' not in str(data).lower():
        print('REFUSED: data dir is not inside a dev-tools run directory', file=sys.stderr)
        return 2

    from kel.core import Store, digest, encode
    from kel.context import Context
    from kel.memory import Memory

    store = Store(data)
    context = Context(store)
    if args.project_root:
        root = Path(args.project_root).resolve()
        context.project('Baseline Fixture', root=str(root), project_id='default',
                        notes='Fixture project for packaged UI baseline captures.')

    c1 = context.conversation('default', title='Baseline fixture chat')
    store.add_message('Capture the packaged baseline at five widths and all states.',
                      role='user', conversation=c1)
    store.add_message('Baseline captures are underway. The frozen V1.3 package is the visual reference.',
                      role='assistant', conversation=c1)

    c2 = context.conversation('default', title='Approval fixture chat')
    store.add_message('Prepare the release-notes draft for review.',
                      role='user', conversation=c2)

    store.add_message('Capture the packaged baseline at five widths and all states.',
                      role='user', conversation='main')
    store.add_message('Baseline captures are underway. The frozen V1.3 package is the visual reference.',
                      role='assistant', conversation='main')
    job_paused = seed_job(store, 'main', state='PAUSED',
                          milestones={'m1': {'state': 'UNCERTAIN', 'attempts': 1}})
    job_approval = seed_job(store, 'main', state='AWAITING_USER',
                            milestones={'m1': {'state': 'UNCERTAIN', 'attempts': 1}})
    action = {'kind': 'command', 'command': 'echo fixture'}
    with store.transaction() as db:
        db.execute("CREATE TABLE IF NOT EXISTS approval_actions("
                   "approval_id TEXT PRIMARY KEY,action TEXT)")
        db.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?,?)",
                   ('ap-fixture-1', job_approval, 'run-fixture', digest(action),
                    'PENDING', time.time() + 3600, None))
        db.execute("INSERT INTO approval_actions VALUES(?,?)",
                   ('ap-fixture-1', encode(action)))

    mem = Memory(store)
    mem.record('default', 'decision', 'Visual baseline',
               {'value': 'frozen-v1.3'},
               'Use the frozen V1.3 package as the visual baseline for captures.',
               source_type='user_instruction', user_confirmed=1,
               source_ref='docs/v1.4/KEL_V1.4_BASELINE.md')
    mem.record('default', 'fact', 'Test suite',
               {'value': '267 passed + 10 subtests'},
               'V1.3 baseline engine suite: 267 passed + 10 subtests.',
               source_type='repo_inspection', source_ref='README.md')
    mem.propose('default', 'observation', 'Drawer density',
                {'value': 'rows feel dense at 1280 width'},
                'Work drawer rows look dense at 1280 width (fixture inference).',
                confidence=0.6, source_ref='fixture:seed')

    # --- Gate 3/4 fixtures: team roles, assignments, activity, solution brief --------------
    from kel.solution import SolutionBriefs
    from kel.team import Team

    team = Team(store)
    team.seed_defaults()
    impl = team.create_assignment(job_paused, 'm1', 'implementation-engineer',
                                  project_id='default', provider='fixture',
                                  model='fixture-model')
    team.attach_run(impl['assignment_id'], 'run-fixture-1', provider='fixture',
                    model='fixture-model')
    team.record_activity(impl['assignment_id'], 'step.started', {'step': 1})
    team.record_activity(impl['assignment_id'], 'decision.made',
                         {'summary': 'Chose the smallest coherent change (fixture).'})
    team.add_artifact(impl['assignment_id'], 'fixture-digest-1', 'report.md', 'artifact')
    team.set_state(impl['assignment_id'], 'WAITING')
    qa = team.create_assignment(job_approval, 'm1', 'qa-engineer', project_id='default')

    briefs = SolutionBriefs(store)
    brief = briefs.open_brief('default',
                              'Choose the V1.4 direction and capture the V1.3 baseline.',
                              conversation_id='main')
    briefs.update(brief,
                  request='Redesign the shell; the frozen V1.3 package stays the visual baseline.',
                  assumptions=['Probe captures need an isolated data root.'],
                  verified_constraints=['Frozen V1.3 hashes verified 3/3.'],
                  criteria=['clarity', 'accessibility', 'migration cost'])
    briefs.add_option(brief, 'desk', 'Desk', 'Light neutral, cards plus focused sheets.',
                      'implement', tradeoffs=['lower density'], cost='medium', complexity=3,
                      reversible=True)
    briefs.add_option(brief, 'console', 'Console', 'Dark, table-first, permanent inspector.',
                      'implement', tradeoffs=['migration cost'], cost='high', complexity=4,
                      reversible=True)
    briefs.compare(brief, 'clarity', 'desk', 4, 'verdict-first summary')
    briefs.compare(brief, 'clarity', 'console', 3, 'state scanning first')
    briefs.search(brief, [{'what': 'Donor theme tokens', 'where': 'desktop/uno.config.ts',
                           'ref': 'uno.config.ts', 'verdict': 'adapt'}])
    briefs.opportunity(brief, 'Figma source', 'Higher visual fidelity',
                       'Closer to brand intent', 'Use rendered captures only',
                       classification='ASK_ONCE', access_needed='read-only Figma file')
    briefs.idea(brief, 'Ship a dark console first', 'BETTER_LATER',
                'Revisit after the light base ships.')
    briefs.recommend(brief, 'desk', 'Best fit for the readability bar and the approval sheet.',
                     'Rendered density tests failing in the Work Center',
                     'Revert that surface to the V1.3 donor styling.')
    briefs.review(brief, 'independent-reviewer', 'OPTIMAL_ENOUGH',
                  'Compared fairly; risks and evidence-to-switch recorded.')
    briefs.approve(brief, actor='user')

    print(json.dumps({'schema': 1, 'data': str(data),
                      'conversations': [c1, c2],
                      'jobs': {'paused': job_paused, 'approval': job_approval},
                      'team': {'assignment': impl['assignment_id'],
                               'qa': qa['assignment_id'], 'roles': len(team.roster())},
                      'brief': brief, 'brief_state': 'APPROVED'},
                     indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
