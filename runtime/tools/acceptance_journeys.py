"""V2-18 — synthetic V2 acceptance journeys against a real, owned engine.

Run from `runtime/`:

    python tools/acceptance_journeys.py --root C:/Users/Nick/KelV2Runs/prepared/engine \
        --journeys J-FIX,J-UPGRADE,J-SEC,J-KBU

Design rules this runner holds to:

- **Identity before use.** `desktop-session.json` is a file, not a fact. The runner proves the
  recorded pid is alive, that its command line names this data root, and that the recorded port is
  owned by that pid. Any mismatch is a hard error: no fallback engine, no blind retry.
- **Synthetic inputs, real paths.** Findings, fixture repositories and turns are synthetic; the
  engine, its HTTP surface, its SQLite store, the isolated coding workspaces, the real installed
  runtimes and the real backup/containment machinery are not simulated.
- **Separate claims.** For the Kibble Build Update journey a CLOSED job or a candidate row alone
  proves nothing: mission creation, promotion refusal, candidate-record creation, a verified
  artifact with source provenance and the complete repair-to-candidate journey are recorded as
  separate claims.
- **Labelled fixtures.** Anything that cannot be exercised here (external services, Muse audio,
  the phone) is recorded as a labelled fixture or as pending — never as a pass.
"""
import argparse
import base64
import contextlib
import json
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = r'C:\Users\Nick\KelV2Runs\prepared\engine'
DEFAULT_FIXTURES = r'C:\Users\Nick\KelV2Runs\prepared\acceptance'
PROTECTED_APP = r'C:\Users\Nick\KelDogfoodCandidate'


# --------------------------------------------------------------------------------------- shell helpers
def powershell(script, timeout=60):
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', script],
                                capture_output=True, text=True, timeout=timeout)
    except Exception as exc:                                     # pragma: no cover -环境 dependent
        return '', str(exc), 1
    return (result.stdout or '').strip(), (result.stderr or '').strip(), result.returncode


def process_command_line(pid):
    out, _, _ = powershell("Get-CimInstance Win32_Process -Filter 'ProcessId=%d' | "
                           "Select-Object -ExpandProperty CommandLine" % int(pid))
    return out or None


def port_owner(port):
    out, _, _ = powershell("(Get-NetTCPConnection -LocalPort %d -State Listen -ErrorAction "
                           "SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess)"
                           % int(port))
    try:
        return int(out)
    except (TypeError, ValueError):
        return None


def git(path, *args):
    result = subprocess.run(['git', '-C', str(path)] + list(args), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError('git %s failed: %s' % (' '.join(args), (result.stderr or '').strip()))
    return result.stdout.strip()


def git_ok(path, *args):
    try:
        git(path, *args)
        return True
    except Exception:
        return False


# -------------------------------------------------------------------------------------- engine client
class IdentityError(RuntimeError):
    pass


class EngineClient:
    """An HTTP client bound to one proven-live engine on one data root."""

    def __init__(self, root):
        self.root = Path(root)
        descriptor_path = self.root / 'desktop-session.json'
        if not descriptor_path.is_file():
            raise IdentityError('no desktop-session.json under %s' % self.root)
        descriptor = json.loads(descriptor_path.read_text(encoding='utf-8-sig'))
        self.url = str(descriptor['url']).rstrip('/')
        self.token = descriptor['token']
        self.pid = int(descriptor['pid'])
        self.version = descriptor.get('engine_version')
        self.port = urllib.parse.urlparse(self.url).port

    def identity(self):
        """Prove the descriptor describes the engine on this root. Never trust the file."""
        problems = []
        command_line = process_command_line(self.pid)
        if not command_line:
            problems.append('pid %d is not running' % self.pid)
        else:
            normalized = command_line.replace('\\', '/').lower()
            if str(self.root).replace('\\', '/').lower() not in normalized:
                problems.append('pid %d is not the engine for this root' % self.pid)
        owner = port_owner(self.port)
        if owner != self.pid:
            problems.append('port %s is owned by %s, not pid %d' % (self.port, owner, self.pid))
        return {'pid': self.pid, 'port': self.port, 'url': self.url,
                'command_line': command_line, 'port_owner': owner, 'problems': problems}

    def call(self, route, payload=None, timeout=60):
        """One engine call; HTTP 400 (a refusal) is raised as PolicyRefusal with its sentence."""
        request = urllib.request.Request(
            self.url + route,
            data=json.dumps(payload).encode() if payload is not None else None,
            method='POST' if payload is not None else 'GET')
        request.add_header('Authorization', 'Bearer ' + self.token)
        if payload is not None:
            request.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode() or 'null')
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors='replace')
            try:
                sentence = json.loads(body).get('error', body)
            except ValueError:
                sentence = body
            raise PolicyRefusal('%s %s -> %s' % (route, payload.get('action') if isinstance(payload, dict) else '', sentence))

    def refusal(self, route, payload, timeout=60):
        """Call something expected to be refused; return the sentence (or a failure note)."""
        try:
            result = self.call(route, payload, timeout=timeout)
            return {'refused': False, 'answer': result}
        except PolicyRefusal as exc:
            return {'refused': True, 'sentence': exc.sentence}


class PolicyRefusal(RuntimeError):
    def __init__(self, sentence):
        super().__init__(sentence)
        self.sentence = sentence


# ------------------------------------------------------------------------------------- fixture helpers
CALC = '''def add(a, b):
    """V2-18 fixture: this is the deliberate defect the mission must repair."""
    return a - b


def multiply(a, b):
    return a * b
'''

TEST_CALC = '''import unittest

from calc import add, multiply


class CalcTests(unittest.TestCase):
    def test_multiply_still_works(self):
        self.assertEqual(multiply(3, 4), 12)

    def test_add(self):
        self.assertEqual(add(2, 3), 5)


if __name__ == '__main__':
    unittest.main()
'''


def ensure_fixture(path):
    """A real git repository with a real failing test. Synthetic content, real paths."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    (path / 'calc.py').write_text(CALC, encoding='utf-8')
    (path / 'test_calc.py').write_text(TEST_CALC, encoding='utf-8')
    if not (path / '.git').is_dir():
        git(path, 'init', '-q')
    git(path, 'add', '-A')
    if git(path, 'status', '--porcelain'):
        git(path, '-c', 'user.name=Kel V2 acceptance', '-c', 'user.email=kel@localhost',
            'commit', '-q', '-m', 'V2-18 fixture baseline: add() is wrong on purpose')
    return {'root': str(path), 'revision': git(path, 'rev-parse', 'HEAD'),
            'clean': not git(path, 'status', '--porcelain'),
            'labelled_fixture': 'synthetic repository; the defect is deliberate'}


# -------------------------------------------------------------------------------------------- journeys
def journey_fix_capture(client, ctx):
    """§27 Fix Capture — a real finding captured, read back and re-statused through the store."""
    journey = {'id': 'J-FIX', 'name': 'Fix Capture round trip', 'shell_required': False,
               'requirements': ['Fix Capture: real friction capture'], 'detail': {}}
    saved = client.call('/api/dogfood', {'action': 'save',
                                         'transcript': 'V2-18 synthetic capture: the Send button stays '
                                                       'disabled after a reply lands.',
                                         'route': '/guid', 'page_title': 'Guid',
                                         'version': client.version})
    fix_id = saved['id']
    read_back = client.call('/api/dogfood', {'action': 'get', 'id': fix_id})
    client.call('/api/dogfood', {'action': 'set_status', 'id': fix_id, 'status': 'BATCHED'})
    after = client.call('/api/dogfood', {'action': 'get', 'id': fix_id})
    listed = client.call('/api/dogfood', {'action': 'list', 'status': 'BATCHED'})
    journey['detail'] = {'fix': fix_id, 'captured_status': saved.get('status'),
                         'read_back_route': read_back.get('route'),
                         'status_after_set': after.get('status'),
                         'listed_batched': [f['id'] for f in listed['fixes']][:8],
                         'counts': listed.get('counts'),
                         'fixture': 'synthetic transcript; the real Fix Capture store and routes'}
    ok = (saved.get('status') == 'OPEN' and read_back.get('route') == '/guid'
          and after.get('status') == 'BATCHED' and fix_id in [f['id'] for f in listed['fixes']])
    journey['status'] = 'PASSED' if ok else 'FAILED'
    if not ok:
        journey['problem'] = 'the capture did not round-trip through the real store'
    return journey


def journey_upgrade(client, ctx):
    """§27 Upgrade — the real inventory (read-only) still covers V2 state."""
    journey = {'id': 'J-UPGRADE', 'name': 'Durable state inventory', 'shell_required': False,
               'requirements': ['Upgrade: preserve durable user state'], 'detail': {}}
    inventory = client.call('/api/backup', {'action': 'inventory'})
    tables = inventory.get('tables') or {}
    expected = ('connections', 'oauth_flows', 'connection_events', 'routing_outcomes', 'model_prefs',
                'network_policy', 'network_events', 'memories', 'projects', 'conversations',
                'dogfood_fixes', 'build_missions', 'build_candidates', 'schema_migrations')
    missing = [name for name in expected if name not in tables]
    journey['detail'] = {'tables': len(tables), 'migrations': len(inventory.get('migrations') or []),
                         'missing': missing,
                         'v2_counts': {name: tables.get(name) for name in expected if name in tables}}
    journey['status'] = 'PASSED' if not missing else 'FAILED'
    if missing:
        journey['problem'] = 'the inventory no longer covers: %s' % ', '.join(missing)
    return journey


def journey_security(client, ctx):
    """§27 Security — real execution boundaries refuse protected and non-repository roots."""
    journey = {'id': 'J-SEC', 'name': 'Execution boundaries refuse protected sources',
               'shell_required': False,
               'requirements': ['Security: execution boundaries', 'Security: authority narrowing'],
               'detail': {}}
    # A real, open finding, so the ONLY thing that can refuse these starts is the source root
    # itself (an unrelated refusal would prove nothing).
    seed = client.call('/api/dogfood', {'action': 'save',
                                        'transcript': 'V2-18 synthetic finding for the boundary '
                                                      'journey: the source root must be refused.',
                                        'route': '/work', 'page_title': 'Work',
                                        'version': client.version})
    finding = seed['id']
    # 1. Kel's own data root — refused by rule, whatever the environment says.
    sensitive = client.refusal('/api/dogfood', {'action': 'build_update', 'op': 'start',
                                                'findings': [finding],
                                                'source_root': str(client.root),
                                                'tests': ['python', '-m', 'unittest']})
    # 2. The stable dogfood app — refused through KEL_PROTECTED_PATHS, which the desktop sets.
    protected = client.refusal('/api/dogfood', {'action': 'build_update', 'op': 'start',
                                                'findings': [finding],
                                                'source_root': PROTECTED_APP,
                                                'tests': ['python', '-m', 'unittest']})
    # 3. A real folder that is not a repository — Kel's own sentence, never a raw git message.
    not_a_repo = Path(ctx['fixtures']) / 'not-a-repo'
    not_a_repo.mkdir(parents=True, exist_ok=True)
    (not_a_repo / 'notes.txt').write_text('not a repository\n', encoding='utf-8')
    plain = client.refusal('/api/dogfood', {'action': 'build_update', 'op': 'start',
                                            'findings': [finding],
                                            'source_root': str(not_a_repo),
                                            'tests': ['python', '-m', 'unittest']})
    journey['detail'] = {'finding': finding, 'sensitive_root': str(client.root),
                         'sensitive_refusal': sensitive, 'protected_root': PROTECTED_APP,
                         'protected_refusal': protected, 'non_repository_refusal': plain,
                         'fixture': 'a real folder that is not a repository (synthetic content)'}
    # The sentences must name the REAL reason. Measured first: an earlier version of this journey
    # "passed" on an unknown-finding refusal and on a leaked git message — it had proved nothing.
    sensitive_ok = (sensitive.get('refused')
                    and 'will not use' in sensitive.get('sentence', ''))
    protected_ok = (protected.get('refused')
                    and 'will not use' in protected.get('sentence', ''))
    plain_sentence = plain.get('sentence', '')
    # Kel's own sentence leads; git's detail may follow in parentheses (that is the fix), so the
    # check is that the raw message is not what the person reads first.
    plain_body = plain_sentence.split('->')[-1].strip()
    plain_ok = (plain.get('refused')
                and plain_body.startswith('That folder is not a Git repository')
                and not plain_body.lower().startswith('fatal:'))
    if sensitive_ok and protected_ok and plain_ok:
        journey['status'] = 'PASSED'
    elif sensitive_ok and plain_ok and not protected_ok:
        # Honest labelling: without the desktop's KEL_PROTECTED_PATHS the stable-app rule is not
        # loaded in this engine, so the check cannot be claimed at all.
        journey['status'] = 'PENDING'
        journey['problem'] = ('the stable-app root was not refused: this engine was started without '
                              'KEL_PROTECTED_PATHS (the desktop sets it at spawn)')
    else:
        journey['status'] = 'FAILED'
        journey['problem'] = ('the sensitive root was not refused in plain words' if not sensitive_ok
                              else 'a non-repository source did not get Kel\'s own sentence')
    return journey


def journey_kibble(client, ctx, dispatch=True, wait=900, poll=10):
    """The complete Kibble Build Update journey, with its claims kept separate."""
    journey = {'id': 'J-KBU', 'name': 'Kibble Build Update — separate claims', 'shell_required': False,
               'requirements': ['Fix Capture: real friction capture', 'Work: real autonomous execution',
                                'Recovery: failures without lost work',
                                'Security: execution boundaries'],
               'claims': {}, 'detail': {}}
    fixture = ensure_fixture(Path(ctx['fixtures']) / 'kibble-repo')
    ctx['fixture'] = fixture
    detail = journey['detail']
    detail['fixture'] = fixture

    findings = []
    for text in ('V2-18 synthetic finding A: add() returns the difference, not the sum.',
                 'V2-18 synthetic finding B: the failing unit test is the acceptance signal.'):
        saved = client.call('/api/dogfood', {'action': 'save', 'transcript': text,
                                             'route': '/work', 'page_title': 'Work',
                                             'version': client.version})
        findings.append(saved['id'])
    detail['findings'] = findings

    started = client.call('/api/dogfood', {'action': 'build_update', 'op': 'start',
                                           'findings': findings,
                                           'source_root': fixture['root'],
                                           'tests': ['python', '-m', 'unittest', '-v'],
                                           'scope': ['calc.py'],
                                           'conversation': 'main'})
    mission, job_id = started['mission'], started['job']
    detail['mission'] = {'id': mission['id'], 'job': job_id,
                         'baseline_revision': mission['baseline_revision'],
                         'source_root': mission['source_root'],
                         'job_kind': (started.get('contract') or {}).get('kind'),
                         'test_command': (started.get('contract') or {}).get('test_command')}

    # Claim 1 — mission creation: the record, the verified baseline, the untouched checkout.
    source_untouched = (git(fixture['root'], 'status', '--porcelain') == ''
                        and git(fixture['root'], 'rev-parse', 'HEAD') == fixture['revision'])
    journey['claims']['mission_created'] = {
        'status': 'PASSED' if (mission['baseline_revision'] == fixture['revision']
                               and mission['source_root'].replace('\\', '/').lower()
                               == fixture['root'].replace('\\', '/').lower()
                               and (started.get('contract') or {}).get('kind') == 'coding'
                               and source_untouched
                               and mission['findings'][0]['id'] == findings[0]) else 'FAILED',
        'detail': {'baseline_matches_fixture_head': mission['baseline_revision'] == fixture['revision'],
                   'job_is_a_coding_contract': (started.get('contract') or {}).get('kind') == 'coding',
                   'source_checkout_untouched': source_untouched,
                   'finding_context_recorded': mission['findings'][0]}}

    # Claim 1b — promotion refuses before anything exists.
    fresh = client.refusal('/api/dogfood', {'action': 'build_update', 'op': 'promote'})
    journey['claims']['promotion_refused_at_start'] = {
        'status': 'PASSED' if fresh.get('refused') else 'FAILED', 'detail': fresh}

    # Claim 2a — nothing is created before the mission settles.
    before = client.call('/api/dogfood', {'action': 'build_update', 'op': 'candidate',
                                          'mission': mission['id']})
    detail['candidate_before_settle'] = {'state': before.get('state'),
                                         'created': before.get('candidate') is not None}
    journey['claims']['candidate_gated_while_building'] = {
        'status': 'PASSED' if (before.get('state') == 'BUILDING'
                               and before.get('candidate') is None) else 'FAILED',
        'detail': detail['candidate_before_settle']}

    # The real dispatch: the engine claims the coding job and the isolated runtime repairs the copy.
    route = None
    if dispatch:
        deadline = time.time() + wait
        last = None
        while time.time() < deadline:
            state = client.call('/api/dogfood', {'action': 'build_update', 'op': 'status',
                                                 'mission': mission['id']})
            last = state['job']
            if last and last.get('state') in ('CLOSED', 'CANCELLED', 'FAILED'):
                break
            try:
                routes = client.call('/api/state').get('routes') or {}
                route = routes.get(job_id) or route
            except Exception:
                pass
            time.sleep(poll)
        detail['job_after_dispatch'] = last
        detail['route'] = route
    else:
        detail['job_after_dispatch'] = 'not dispatched (--no-runtime)'

    settled = detail['job_after_dispatch']
    closed = isinstance(settled, dict) and settled.get('state') == 'CLOSED'

    candidate = client.call('/api/dogfood', {'action': 'build_update', 'op': 'candidate',
                                             'mission': mission['id']})
    detail['candidate'] = {key: candidate.get('candidate', {}).get(key)
                           for key in ('id', 'review_state', 'revision', 'artifact_location',
                                       'fixed_findings', 'unresolved_findings')}
    detail['candidate_evidence'] = (candidate.get('candidate') or {}).get('evidence')

    # Claim 2b — the candidate record exists, outside the source checkout.
    record = candidate.get('candidate') or {}
    artifact = str(record.get('artifact_location') or '')
    inside_source = artifact and Path(artifact) == Path(fixture['root'])
    journey['claims']['candidate_record_created'] = {
        'status': 'PASSED' if (candidate.get('state') in ('READY_FOR_REVIEW', 'APPROVED', 'REJECTED')
                               and artifact and not inside_source) else 'FAILED',
        'detail': {'state': candidate.get('state'), 'artifact_location': artifact,
                   'inside_source_checkout': bool(inside_source)}}

    # Claim 3 — a verified artifact with real source provenance (only if the run really produced one).
    evidence = (record.get('evidence') or {})
    provenance = None
    if evidence.get('workspace'):
        workspace = evidence['workspace']
        provenance = {'workspace': workspace,
                      'workspace_under_data_root': str(Path(ctx['root']).resolve()).lower()
                                                   in str(Path(workspace).resolve()).lower(),
                      'baseline_is_ancestor': git_ok(workspace, 'merge-base', '--is-ancestor',
                                                     mission['baseline_revision'], 'HEAD'),
                      'workspace_head': git(workspace, 'rev-parse', 'HEAD') if git_ok(
                          workspace, 'rev-parse', 'HEAD') else None,
                      'patch_digest': evidence.get('patch_digest'),
                      'build_report': (Path(artifact) / 'build-report.json').is_file()}
    detail['provenance'] = provenance
    journey['claims']['artifact_verified_with_provenance'] = {
        'status': 'PASSED' if (evidence.get('verified') is True and provenance
                               and provenance['workspace_under_data_root']
                               and provenance['baseline_is_ancestor']
                               and provenance['build_report']
                               and record.get('fixed_findings') == findings
                               and not record.get('unresolved_findings')) else
                  ('PENDING' if not closed else 'FAILED'),
        'detail': {'verified_flag': evidence.get('verified'), 'provenance': provenance,
                   'fixed_findings': record.get('fixed_findings'),
                   'unresolved_findings': record.get('unresolved_findings'),
                   'job_closed': closed}}

    # Claim 4 — the complete journey: repair reached the candidate, a person reviews, nothing installs.
    review = None
    second_review = None
    promote_after = None
    if record.get('id'):
        review = client.call('/api/dogfood', {'action': 'build_update', 'op': 'review',
                                              'candidate': record['id'], 'decision': 'approve',
                                              'note': 'V2-18 synthetic acceptance review'})
        second_review = client.refusal('/api/dogfood', {'action': 'build_update', 'op': 'review',
                                                        'candidate': record['id'],
                                                        'decision': 'reject'})
        promote_after = client.refusal('/api/dogfood', {'action': 'build_update', 'op': 'promote',
                                                        'candidate': record['id']})
    statuses_after = {fix_id: client.call('/api/dogfood', {'action': 'get', 'id': fix_id}).get('status')
                      for fix_id in findings}
    detail['review'] = review
    detail['second_review'] = second_review
    detail['promote_after_approval'] = promote_after
    detail['finding_statuses_after'] = statuses_after
    source_still_untouched = (git(fixture['root'], 'status', '--porcelain') == ''
                              and git(fixture['root'], 'rev-parse', 'HEAD') == fixture['revision'])
    detail['source_checkout_untouched_at_end'] = source_still_untouched
    complete = (journey['claims']['mission_created']['status'] == 'PASSED'
                and journey['claims']['candidate_record_created']['status'] == 'PASSED'
                and journey['claims']['artifact_verified_with_provenance']['status'] == 'PASSED'
                and (review or {}).get('review_state') == 'APPROVED'
                and second_review and second_review.get('refused')
                and promote_after and promote_after.get('refused')
                and all(value == 'OPEN' for value in statuses_after.values())
                and source_still_untouched)
    journey['claims']['complete_journey'] = {
        'status': 'PASSED' if complete else ('PENDING' if not closed else 'FAILED'),
        'detail': {'review_state': (review or {}).get('review_state'),
                   'second_review_refused': bool(second_review and second_review.get('refused')),
                   'promote_refused_after_approval': bool(promote_after and promote_after.get('refused')),
                   'fix_capture_statuses_unchanged': statuses_after,
                   'source_checkout_untouched': source_still_untouched}}

    # Claim 5 — nothing installs: the refusal is a sentence, and no installed path was written.
    journey['claims']['no_install_path'] = {
        'status': 'PASSED' if (fresh.get('refused') and promote_after
                               and promote_after.get('refused')) else 'FAILED',
        'detail': {'promote_before': fresh, 'promote_after_approval': promote_after}}

    statuses = [claim.get('status') for claim in journey['claims'].values()]
    journey['status'] = ('PASSED' if all(value == 'PASSED' for value in statuses)
                         else 'PENDING' if 'PENDING' in statuses else 'FAILED')
    return journey


def journey_kibble_negatives(client, ctx, dispatch=False, wait=900, poll=10):
    """A cancelled mission and a plain failing test command must never yield a ready claim."""
    journey = {'id': 'J-KBU-NEG', 'name': 'Kibble negatives — no false ready claim',
               'shell_required': False,
               'requirements': ['Recovery: failures without lost work', 'Work: real autonomous execution'],
               'claims': {}, 'detail': {}}
    fixture = ensure_fixture(Path(ctx['fixtures']) / 'kibble-negatives')
    saved = client.call('/api/dogfood', {'action': 'save',
                                         'transcript': 'V2-18 synthetic negative: the mission will be '
                                                       'cancelled before it can produce an artifact.',
                                         'route': '/work', 'page_title': 'Work',
                                         'version': client.version})
    fix_id = saved['id']
    started = client.call('/api/dogfood', {'action': 'build_update', 'op': 'start',
                                           'findings': [fix_id],
                                           'source_root': fixture['root'],
                                           'tests': ['python', '-m', 'unittest', '-v'],
                                           'scope': ['calc.py']})
    mission, job_id = started['mission'], started['job']
    client.call('/api/control', {'action': 'cancel', 'job': job_id})
    settled = None
    deadline = time.time() + 120
    while time.time() < deadline:
        state = client.call('/api/dogfood', {'action': 'build_update', 'op': 'status',
                                             'mission': mission['id']})
        settled = state
        if state['job'] and state['job'].get('state') in ('CLOSED', 'CANCELLED', 'FAILED'):
            break
        time.sleep(poll)
    candidate = client.call('/api/dogfood', {'action': 'build_update', 'op': 'candidate',
                                             'mission': mission['id']})
    record = candidate.get('candidate') or {}
    journey['claims']['cancelled_mission_claims_nothing'] = {
        'status': 'PASSED' if not (record.get('evidence') or {}).get('verified') else 'FAILED',
        'detail': {'job_state': (settled or {}).get('job', {}).get('state'),
                   'candidate_state': candidate.get('state'),
                   'evidence': record.get('evidence') or None}}

    if dispatch:
        failed = client.call('/api/dogfood', {'action': 'save',
                                              'transcript': 'V2-18 synthetic negative: the test command '
                                                            'itself fails, so nothing can be verified.',
                                              'route': '/work', 'page_title': 'Work',
                                              'version': client.version})
        second = client.call('/api/dogfood', {'action': 'build_update', 'op': 'start',
                                              'findings': [failed['id']],
                                              'source_root': fixture['root'],
                                              'tests': ['python', '-c', 'import sys; sys.exit(1)'],
                                              'scope': ['calc.py']})
        deadline = time.time() + wait
        state = None
        while time.time() < deadline:
            state = client.call('/api/dogfood', {'action': 'build_update', 'op': 'status',
                                                 'mission': second['mission']['id']})
            if state['job'] and state['job'].get('state') in ('CLOSED', 'CANCELLED', 'FAILED'):
                break
            time.sleep(poll)
        assembled = client.call('/api/dogfood', {'action': 'build_update', 'op': 'candidate',
                                                 'mission': second['mission']['id']})
        record = assembled.get('candidate') or {}
        evidence = record.get('evidence') or {}
        still_open = client.call('/api/dogfood', {'action': 'get', 'id': failed['id']}).get('status')
        journey['claims']['failed_tests_never_verified'] = {
            'status': 'PASSED' if (evidence.get('verified') in (False, None)
                                   and not record.get('fixed_findings')
                                   and still_open == 'OPEN') else 'FAILED',
            'detail': {'job_state': (state or {}).get('job', {}).get('state'),
                       'verified': evidence.get('verified'),
                       'fixed_findings': record.get('fixed_findings'),
                       'unresolved_findings': record.get('unresolved_findings'),
                       'finding_status': still_open}}
    else:
        journey['claims']['failed_tests_never_verified'] = {
            'status': 'PENDING', 'detail': 'run with --runtime-negatives to dispatch a really failing '
                                           'test command'}

    statuses = [claim.get('status') for claim in journey['claims'].values()]
    journey['status'] = ('PASSED' if all(value == 'PASSED' for value in statuses)
                         else 'PENDING' if 'PENDING' in statuses else 'FAILED')
    return journey


def _state(client, conversation):
    return client.call('/api/state?conversation=' + urllib.parse.quote(conversation))


def _wait_for_job(client, conversation, wait, poll):
    """Wait until the conversation has a settled job; return (job, state_seen)."""
    deadline = time.time() + wait
    job = None
    state = {}
    while time.time() < deadline:
        state = _state(client, conversation)
        jobs = state.get('jobs') or []
        if jobs:
            job = sorted(jobs, key=lambda item: item.get('created') or 0)[-1]
            if job.get('state') in ('CLOSED', 'CANCELLED'):
                break
        time.sleep(poll)
    return job, state


def journey_model(client, ctx, wait=600, poll=10):
    """§27 Models — a real turn, and the stored route read back rather than recomputed."""
    journey = {'id': 'J-MODEL', 'name': 'Routing read-back and fallback chain',
               'shell_required': False,
               'requirements': ['Models: routing, fallback, transparency'], 'detail': {}}
    project = client.call('/api/project', {'name': 'acceptance-model-%d' % int(time.time()),
                                           'context': 'V2-18 routing read-back'})['id']
    conversation = client.call('/api/conversation', {'project': project})['id']
    client.call('/api/send', {'text': 'Write a short note titled Acceptance Tuesday about what makes '
                                       'a good landing page headline.',
                              'conversation': conversation})
    job, state = _wait_for_job(client, conversation, wait, poll)
    why = client.call('/api/model', {'action': 'why', 'conversation': conversation})
    journey['detail'] = {'conversation': conversation,
                         'job': (job or {}).get('id'), 'job_state': (job or {}).get('state'),
                         'why': why}
    selected = str(why.get('selected') or '')
    chain = why.get('chain') or []
    ok = (bool(selected) and selected == str(why.get('provider') or '')
          and str(why.get('job') or '') == str((job or {}).get('id') or '')
          and len(chain) >= 1 and chain[0] == selected
          and 'Kel is using' in str(why.get('answer') or ''))
    journey['status'] = 'PASSED' if ok else 'FAILED'
    if not ok:
        journey['problem'] = ('the read-back did not match the stored route: selected=%r provider=%r '
                              'job=%r chain=%r' % (selected, why.get('provider'), why.get('job'), chain))
    return journey


def journey_conversation(client, ctx, wait=420, poll=6):
    """§27 Conversation — two real turns in one thread, answered in context and persisted."""
    journey = {'id': 'J-CONV', 'name': 'Conversation, continuation and persistence',
               'shell_required': False,
               'requirements': ['Conversation: discussion and continuation'], 'detail': {}}
    project = client.call('/api/project', {'name': 'acceptance-conv-%d' % int(time.time()),
                                           'context': 'V2-18 conversation journey'})['id']
    conversation = client.call('/api/conversation', {'project': project})['id']
    client.call('/api/send', {'text': 'In one short sentence: which day follows Tuesday?',
                              'conversation': conversation})
    first = None
    deadline = time.time() + wait
    while time.time() < deadline:
        state = _state(client, conversation)
        messages = state.get('messages') or []
        if len(messages) >= 2:
            first = messages[-1].get('text')
            break
        time.sleep(poll)
    client.call('/api/send', {'text': 'And in one short sentence: which day comes before it?',
                              'conversation': conversation})
    second = None
    deadline = time.time() + wait
    while time.time() < deadline:
        state = _state(client, conversation)
        messages = state.get('messages') or []
        if len(messages) >= 4:
            second = messages[-1].get('text')
            break
        time.sleep(poll)
    state = _state(client, conversation)
    messages = state.get('messages') or []
    roles = [m.get('role') for m in messages]
    listed = [c.get('id') for c in (state.get('conversations') or [])]
    journey['detail'] = {'conversation': conversation, 'messages': len(messages), 'roles': roles,
                         'first_reply': (first or '')[:200], 'second_reply': (second or '')[:200],
                         'conversation_listed': conversation in listed}
    ok = (len(messages) >= 4 and roles[:4] == ['user', 'assistant', 'user', 'assistant']
          and first and second and first.strip() != second.strip()
          and conversation in listed)
    journey['status'] = 'PASSED' if ok else 'FAILED'
    if not ok:
        journey['problem'] = 'the second turn did not land in the same persisted thread'
    return journey


def journey_projects(client, ctx):
    """§27 Projects — two real contexts, and no contamination between them."""
    journey = {'id': 'J-PROJ', 'name': 'Two projects, no contamination', 'shell_required': False,
               'requirements': ['Projects: multiple real contexts'], 'detail': {}}
    stamp = int(time.time())
    alpha = client.call('/api/project', {'id': 'acceptance-alpha-%d' % stamp,
                                         'name': 'acceptance-alpha-%d' % stamp,
                                         'context': 'V2-18 synthetic project alpha'})['id']
    beta = client.call('/api/project', {'id': 'acceptance-beta-%d' % stamp,
                                        'name': 'acceptance-beta-%d' % stamp,
                                        'context': 'V2-18 synthetic project beta'})['id']
    again = client.call('/api/project', {'id': 'acceptance-alpha-%d' % stamp,
                                         'name': 'acceptance-alpha-%d' % stamp,
                                         'context': 'V2-18 synthetic project alpha'})['id']
    conv_alpha = client.call('/api/conversation', {'project': alpha})['id']
    conv_beta = client.call('/api/conversation', {'project': beta})['id']
    payload = base64.b64encode(b'V2-18 acceptance attachment').decode()
    attached = client.call('/api/attach', {'conversation': conv_alpha,
                                           'name': 'acceptance-alpha.txt',
                                           'content': payload, 'mime': 'text/plain'})
    work_alpha = client.call('/api/work?conversation=' + urllib.parse.quote(conv_alpha))
    work_beta = client.call('/api/work?conversation=' + urllib.parse.quote(conv_beta))
    state_alpha = _state(client, conv_alpha)
    state_beta = _state(client, conv_beta)
    journey['detail'] = {'alpha': alpha, 'beta': beta, 'project_idempotent': alpha == again,
                         'attached': attached,
                         'conversations_differ': conv_alpha != conv_beta,
                         'alpha_project_in_work': work_alpha.get('project_id'),
                         'beta_project_in_work': work_beta.get('project_id'),
                         'alpha_attachments': [f.get('name') for f in
                                               (state_alpha.get('attachments') or [])],
                         'beta_attachments': [f.get('name') for f in
                                              (state_beta.get('attachments') or [])]}
    ok = (alpha == again and conv_alpha != conv_beta
          and work_alpha.get('project_id') == alpha and work_beta.get('project_id') == beta
          and [f.get('name') for f in (state_alpha.get('attachments') or [])]
          == ['acceptance-alpha.txt']
          and not (state_beta.get('attachments') or []))
    journey['status'] = 'PASSED' if ok else 'FAILED'
    if not ok:
        journey['problem'] = 'the two projects are not isolated on the real store'
    return journey


def journey_memory(client, ctx):
    """§27 Memory — the person's own surfaces: what Kel learned, its history, its suggestions."""
    journey = {'id': 'J-MEM', 'name': 'Memory and learning surfaces', 'shell_required': False,
               'requirements': ['Memory: useful recall, controlled learning'], 'detail': {}}
    learnings = client.call('/api/memory', {'action': 'learnings', 'conversation': 'main',
                                            'include_disabled': True, 'include_stale': True})
    history = client.call('/api/memory', {'action': 'history', 'conversation': 'main'})
    suggestions = client.call('/api/memory', {'action': 'suggest_learnings', 'conversation': 'main'})
    work = client.call('/api/work?conversation=main')
    records = ((work.get('memory') or {}).get('records')) or []
    items = learnings.get('learnings') or []
    fields = sorted(items[0].keys()) if items else []
    journey['detail'] = {'learnings': len(items), 'learning_fields': fields,
                         'history_entries': len(history.get('entries') or []),
                         'suggestions': len(suggestions.get('proposals') or suggestions.get('created') or []),
                         'project_memories': len(records),
                         'sample': (items[:1] or records[:1])}
    ok = (isinstance(items, list) and isinstance(history.get('entries'), list)
          and len(history.get('entries') or []) > 0)
    journey['status'] = 'PASSED' if ok else 'FAILED'
    if not ok:
        journey['problem'] = 'the memory surfaces did not answer with the real audit trail'
    return journey


RECIPE_SCOPE = ('library', 'search', 'favourites', 'recent', 'categories', 'create', 'edit',
                'duplicate', 'project attachment', 'run', 'run again', 'history', 'last result',
                'suggestions')


def _op_exists(client, payload):
    """Does this engine action exist? A content refusal still proves the op; “Unknown action” does not."""
    try:
        answer = client.call('/api/recipes', payload)
        return {'supported': True, 'keys': sorted(answer.keys())[:10]}
    except PolicyRefusal as exc:
        sentence = exc.sentence or ''
        return {'supported': 'Unknown recipe action' not in sentence, 'sentence': sentence[:140]}


def journey_recipes(client, ctx):
    """§27 Recipes — the library works; V2-07's own scope is measured item by item."""
    journey = {'id': 'J-RECIPE', 'name': 'Recipe library and the V2-07 scope', 'shell_required': False,
               'requirements': ['Recipes: repeated workflows'], 'detail': {}}
    listed = client.call('/api/recipes', {'action': 'list', 'conversation': 'main'})
    entries = listed.get('entries') or []
    first = next((e for e in entries if e.get('recipe_id') != 'continue-work'), entries[0] if entries else None)
    detail = {'entries': len(entries)}
    if first:
        got = client.call('/api/recipes', {'action': 'get', 'conversation': 'main',
                                           'recipe_id': first['recipe_id']})
        preview = client.call('/api/recipes', {'action': 'preview', 'conversation': 'main',
                                               'recipe_id': first['recipe_id'], 'inputs': {}})
        detail['recipe_id'] = first['recipe_id']
        detail['entry_fields'] = sorted(first.keys())
        detail['get_ok'] = bool(got.get('recipe'))
        detail['preview_keys'] = sorted(preview.keys())
    # The V2-07 scope, probed against the live surface instead of assumed: an op that answers
    # “Unknown recipe action” is missing; any other answer (success or a content refusal) proves the
    # op exists.
    probes = {'search': {'query': 'audit'},
              'favourites': {'favourite': True},
              'recent': {},
              'categories': {},
              'history': {'recipe_id': (first or {}).get('recipe_id')},
              'last_result': {'recipe_id': (first or {}).get('recipe_id')},
              'duplicate': {'recipe_id': (first or {}).get('recipe_id')}}
    detail['ops'] = {}
    for op, payload in probes.items():
        detail['ops'][op] = _op_exists(client, dict(payload, action=op, conversation='main'))
    for op, payload in (('save', {}), ('run', {'recipe_id': 'no-such-recipe'}),
                        ('propose_from_job', {'job_id': 'no-such-job'})):
        detail['ops'][op] = _op_exists(client, dict(payload, action=op, conversation='main'))
    supported = {'library': bool(entries),
                 'create': detail['ops']['save']['supported'],
                 'edit': detail['ops']['save']['supported'],
                 'run': detail['ops']['run']['supported'],
                 'project attachment': bool(detail['ops']['save']['supported']),
                 'suggestions': (detail['ops']['propose_from_job']['supported']),
                 'search': detail['ops']['search']['supported'],
                 'favourites': detail['ops']['favourites']['supported'],
                 'recent': detail['ops']['recent']['supported'],
                 'categories': detail['ops']['categories']['supported'],
                 'history': detail['ops']['history']['supported'],
                 'last result': detail['ops']['last_result']['supported'],
                 'duplicate': detail['ops']['duplicate']['supported']}
    supported['run again'] = supported['history'] and supported['last result']
    detail['supported'] = supported
    detail['missing'] = [name for name in RECIPE_SCOPE if not supported.get(name)]
    journey['detail'] = detail
    journey['status'] = 'PASSED' if (entries and not detail['missing']) else 'FAILED'
    if not entries:
        journey['problem'] = 'the recipe library answered with nothing'
    elif detail['missing']:
        journey['problem'] = 'V2-07 scope still missing: %s' % ', '.join(detail['missing'])
    return journey


def journey_network(client, ctx):
    """§27 Security — a real outbound call is refused by a scoped rule, and it is recorded."""
    journey = {'id': 'J-NET', 'name': 'Network rules refuse a real call', 'shell_required': False,
               'requirements': ['Security: network restrictions'], 'detail': {}}
    connections = client.call('/api/connections', {'action': 'list'}) or {}
    items = connections.get('connections') or connections.get('entries') or []
    before = client.call('/api/connections', {'action': 'network', 'op': 'get'})
    journey['detail'] = {'connections': len(items), 'policy_before': before}
    if not items:
        journey['status'] = 'PENDING'
        journey['problem'] = 'no connection exists on this root, so no real call can be refused'
        return journey
    target = items[0].get('id')
    tool = '%s.test' % target
    client.call('/api/connections', {'action': 'network', 'op': 'set_tool', 'tool': tool,
                                     'mode': 'none'})
    try:
        refusal = client.refusal('/api/connections', {'action': 'test', 'id': target})
        history = client.call('/api/connections', {'action': 'network', 'op': 'history'})
    finally:
        client.call('/api/connections', {'action': 'network', 'op': 'clear_tool', 'tool': tool})
    after = client.call('/api/connections', {'action': 'network', 'op': 'get'})
    sentence = (refusal.get('sentence') or '')
    events = history.get('events') or history.get('history') or []
    journey['detail'].update({'connection': target,
                              'refusal': refusal, 'history': len(events),
                              'policy_after': after})
    explicit = (refusal.get('refused')
                and any(word in sentence.lower() for word in ('internet', 'network', 'not allowed',
                                                              'refuse', 'blocked')))
    restored = before.get('modes') == after.get('modes') and before.get('tools') == after.get('tools')
    journey['status'] = 'PASSED' if explicit else 'FAILED'
    if not explicit:
        journey['problem'] = ('the call was not refused by the network rule (sentence: %s)'
                              % sentence[:160])
    journey['detail']['policy_restored'] = restored
    return journey


def journey_connections(client, ctx):
    """§27 Connections — the real choke point, history, and honest labelling of the service."""
    journey = {'id': 'J-CONN', 'name': 'Connection test through the one choke point',
               'shell_required': False,
               'requirements': ['Connections: real personal APIs'], 'detail': {}}
    listed = client.call('/api/connections', {'action': 'list'}) or {}
    items = listed.get('connections') or listed.get('entries') or []
    if not items:
        journey['status'] = 'PENDING'
        journey['problem'] = ('no connection exists on this root; a labelled fixture cannot claim a '
                             'live service')
        return journey
    target = items[0]
    result = client.refusal('/api/connections', {'action': 'test', 'id': target.get('id')})
    after = client.call('/api/connections', {'action': 'get', 'id': target.get('id')})
    journey['detail'] = {'connection': target.get('id'), 'kind': target.get('kind'),
                         'service': target.get('service'), 'answer': result,
                         'base_url': target.get('base_url'),
                         'recorded_state': {k: after.get(k) for k in
                                            ('last_test_state', 'last_test_status', 'last_test_ms',
                                             'last_test_note', 'auth_state')}}
    recorded = any(after.get(k) not in (None, '') for k in ('last_test_state', 'last_test_status'))
    journey['status'] = 'PASSED' if recorded else 'FAILED'
    journey['detail']['labelled'] = ('the call went through the real choke point; the service answer is '
                                     'recorded verbatim and is not claimed as success')
    if not recorded:
        journey['problem'] = 'the test did not leave a recorded result on the connection'
    return journey


def journey_activity(client, ctx):
    """V2-08 — the real activity timeline, its filters, and its plain sentences."""
    journey = {'id': 'J-ACTIVITY', 'name': 'Activity timeline and filters', 'shell_required': False,
               'requirements': ['Activity: timeline, filters, search, results'], 'detail': {}}
    everything = client.call('/api/activity', {'all_projects': True, 'limit': 200})
    entries = everything.get('entries') or []
    work = client.call('/api/activity', {'all_projects': True, 'kind': 'work'})
    failures = client.call('/api/activity', {'all_projects': True, 'failures': True})
    searched = client.call('/api/activity', {'all_projects': True, 'query': 'work'})
    empty = client.call('/api/activity', {'all_projects': True, 'query': 'zzz-no-match-at-all'})
    journey['detail'] = {'entries': len(entries), 'total': everything.get('total'),
                         'counts': everything.get('counts'), 'kinds': everything.get('kinds'),
                         'projects': everything.get('projects'),
                         'work_rows': len(work.get('entries') or []),
                         'failure_rows': len(failures.get('entries') or []),
                         'search_rows': len(searched.get('entries') or []),
                         'sample': entries[:2]}
    ok = (bool(entries) and all(row.get('what') for row in entries)
          and all(row['kind'] == 'work' for row in (work.get('entries') or []))
          and all(row['failed'] for row in (failures.get('entries') or []))
          and not (empty.get('entries') or [])
          and isinstance(everything.get('counts'), dict)
          and everything.get('kinds'))
    journey['status'] = 'PASSED' if ok else 'FAILED'
    if not ok:
        journey['problem'] = 'the timeline or one of its filters did not answer as promised'
    return journey


def journey_transcription(client, ctx):
    """§27 Transcription — the engine path is real; audio capture needs a microphone (labelled)."""
    journey = {'id': 'J-TRANS', 'name': 'Transcription path (labelled fixture)',
               'shell_required': True,
               'requirements': ['Transcription: real Muse recording'], 'detail': {}}
    status = client.call('/api/transcription', {'action': 'status'})
    library = client.call('/api/transcription', {'action': 'library'})
    journey['detail'] = {'status': status, 'library_keys': sorted((library or {}).keys()),
                         'recordings': len(library.get('recordings') or library.get('items') or []),
                         'labelled': 'no audio device and no Muse credential use here: the engine '
                                     'path is exercised, real recording is not claimed'}
    ok = bool(status) and bool(library)
    journey['status'] = 'PASSED' if ok else 'FAILED'
    journey['pending'] = 'real Muse recording (microphone), and the phone surface — Shell/Astra'
    return journey


# --------------------------------------------------------------------- Work / Attention / Recovery
def _engine_imports():
    """Import the engine's own modules (this file lives in `tools/`, so the package needs a path)."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


def _engine_store(root):
    """The engine's own Store, for the raises and settlements no HTTP surface exposes.

    A journey may not invent engine internals: this imports the SAME module the engine runs and
    calls the same public methods its runtime calls (`create`, `claim`, `recover_abandoned`). The
    rows it makes are synthetic inputs; the machinery that reads, fences and resumes them is not.
    """
    _engine_imports()
    from kel.core import Store
    from kel.engine import compile_document
    return Store(Path(root)), compile_document


def _fresh_conversation(client, name):
    """A real Project and conversation on the real root, named so a run can be told apart."""
    project = client.call('/api/project', {'name': '%s-%d' % (name, int(time.time())),
                                           'context': 'V2-18 acceptance journey'})['id']
    return project, client.call('/api/conversation', {'project': project})['id']


def _work_row(client, conversation, job_id):
    """The Work row for one job, as the person's surface answers it."""
    work = (client.call('/api/work?conversation=' + urllib.parse.quote(conversation)) or {}).get('work') or {}
    for entry in work.get('jobs') or []:
        if entry.get('job_id') == job_id:
            return entry, work
    return None, work


def _submissions(client, conversation):
    return _state(client, conversation).get('submissions') or []


def journey_work(client, ctx, wait=600, poll=10):
    """§27 Work — real autonomous execution, and an abandoned run fenced but never replayed."""
    journey = {'id': 'J-WORK', 'name': 'Work settles; an abandoned run is fenced, never replayed',
               'shell_required': False,
               'requirements': ['Work: real autonomous execution', 'Work: recovery of abandoned runs'],
               'claims': {}, 'detail': {}}

    # C1 — a real request on the real root runs and settles with a recorded artifact and an
    # explained verdict. A settled job must never claim more than it can show: when verification
    # cannot be confirmed, the milestone's own check has to say why (and the row offers the retry).
    project, conversation = _fresh_conversation(client, 'acceptance-work')
    client.call('/api/send', {'text': 'Write a short note titled Acceptance Work Note about why a '
                                      'bounded test group beats one long run.',
                              'conversation': conversation})
    job, _ = _wait_for_job(client, conversation, wait, poll)
    entry, work = _work_row(client, conversation, (job or {}).get('id'))
    artifacts, reviewer = [], None
    if job:
        store, _ = _engine_store(ctx['root'])
        record = store.get(job['id'])
        for milestone_id, milestone in (record.get('milestones') or {}).items():
            artifact = milestone.get('artifact') or {}
            if artifact.get('digest') or artifact.get('path'):
                artifacts.append({'milestone': milestone_id, 'bytes': artifact.get('bytes'),
                                  'digest': artifact.get('digest'), 'path': artifact.get('path'),
                                  'lineage': artifact.get('lineage')})
            for check in milestone.get('checks') or []:
                if check.get('kind') == 'manual_review':
                    reviewer = check
    reviewer_explained = bool(reviewer) and bool(reviewer.get('findings'))
    c1 = bool(job) and job.get('state') == 'CLOSED' and bool(entry) and bool(artifacts) \
        and bool(entry.get('reason')) \
        and (job.get('verdict') == 'VERIFIED' or reviewer_explained)
    journey['claims']['real work runs and settles with an explained verdict'] = {
        'status': 'PASSED' if c1 else 'FAILED',
        'detail': {'conversation': conversation, 'project': project,
                   'job': (job or {}).get('id'), 'state': (job or {}).get('state'),
                   'verdict': (job or {}).get('verdict'),
                   'artifacts': artifacts, 'reviewer_check': reviewer,
                   'acceptance_limit': 'work reaches VERIFIED only with a usable reviewer; when the '
                                       'reviewer answers nothing usable the milestone says so '
                                       'instead of claiming a verified build',
                   'row': {'priority': (entry or {}).get('priority'),
                           'needs_you': (entry or {}).get('needs_you'),
                           'accepted': (entry or {}).get('accepted'),
                           'total': (entry or {}).get('total'),
                           'open': (entry or {}).get('open'),
                           'direct': (entry or {}).get('direct'),
                           'reason': (entry or {}).get('reason')}}}

    # C2 — the abandoned run: a real claim, an expired lease, the engine's own runtime recovery.
    store, compile_document = _engine_store(ctx['root'])
    contract = compile_document('Write the fenced note with enough text to pass.', required=[])
    fenced_job = store.create(contract, conversation=conversation)
    milestone_id = next(iter(store.get(fenced_job)['milestones']))
    claim = store.claim(fenced_job, milestone_id, provider='fixture', model='fixture', timeout=30)
    first_fence = store.recover_abandoned(now=time.time() + 600)
    again = store.recover_abandoned(now=time.time() + 600)
    settled = store.get(fenced_job)
    milestone = (settled.get('milestones') or {}).get(milestone_id) or {}
    with contextlib.closing(store.connect()) as db:
        runs = [dict(row) for row in db.execute('SELECT id,state,epoch FROM runs WHERE job_id=?',
                                                (fenced_job,)).fetchall()]
    fenced_entry, _ = _work_row(client, conversation, fenced_job)
    try:
        diagnostics = client.call('/api/diagnostics', {'action': 'snapshot'})
    except PolicyRefusal:
        diagnostics = client.call('/api/diagnostics', {})
    unfenced = (diagnostics.get('runs') or {}).get('expired_unfenced')
    c2 = (claim['id'] in first_fence and not again and len(runs) == 1
          and runs[0]['state'] == 'ORPHANED' and runs[0]['epoch'] != claim.get('epoch')
          and milestone.get('state') == 'UNCERTAIN'
          and 'reconcil' in str(milestone.get('error') or '').lower()
          and settled.get('state') == 'WAITING_RESOURCE' and settled.get('verdict') == 'UNCERTAIN'
          and bool(fenced_entry) and fenced_entry.get('fenced') is True
          and fenced_entry.get('needs_you') is True
          and ((fenced_entry.get('direct') or {}).get('action') == 'resume')
          and ((fenced_entry.get('direct') or {}).get('route') == '/api/send')
          and unfenced == 0)
    journey['claims']['an abandoned run is fenced, never replayed'] = {
        'status': 'PASSED' if c2 else 'FAILED',
        'detail': {'synthetic_input': 'a job and a claim made with the real Store API; the expired '
                                      'lease is the input, the fence is the engine\'s',
                   'job': fenced_job, 'run': claim['id'],
                   'runs_after': runs, 'fenced_by_first_recovery': first_fence,
                   'fenced_by_second_recovery': again,
                   'milestone': {'state': milestone.get('state'), 'error': milestone.get('error')},
                   'job_state': settled.get('state'), 'job_verdict': settled.get('verdict'),
                   'row': {'fenced': (fenced_entry or {}).get('fenced'),
                           'needs_you': (fenced_entry or {}).get('needs_you'),
                           'priority': (fenced_entry or {}).get('priority'),
                           'why': (fenced_entry or {}).get('why'),
                           'next': (fenced_entry or {}).get('next'),
                           'direct': (fenced_entry or {}).get('direct')},
                   'diagnostics_expired_unfenced': unfenced}}
    statuses = [claim_result.get('status') for claim_result in journey['claims'].values()]
    journey['status'] = 'PASSED' if all(value == 'PASSED' for value in statuses) else 'FAILED'
    if journey['status'] == 'FAILED':
        journey['problem'] = '; '.join(name for name, claim_result in journey['claims'].items()
                                       if claim_result.get('status') != 'PASSED')
    return journey


def journey_attention(client, ctx, wait=90):
    """§27 Needs Your Attention — a real ask as one row, answered in one action."""
    journey = {'id': 'J-ATTN', 'name': 'A real interruption, one action, consistent state',
               'shell_required': False,
               'requirements': ['Needs Your Attention: human interruptions',
                                'Needs Your Attention: resolvable in one action'],
               'claims': {}, 'detail': {}}
    project, conversation = _fresh_conversation(client, 'acceptance-attention')
    store, compile_document = _engine_store(ctx['root'])
    _engine_imports()
    from kel.coding import CodingAdapter
    contract = compile_document('Write the approval note with enough text to pass.', required=[])
    job_id = store.create(contract, conversation=conversation)
    milestone_id = next(iter(store.get(job_id)['milestones']))
    run = store.claim(job_id, milestone_id, provider='fixture', model='fixture', timeout=300)
    run_row = dict(run)
    run_row.setdefault('job_id', job_id)

    # The real admission path: the coding adapter's own `approval()` builds the action, records the
    # approval (and its action), announces the card and then waits for the person.
    decided = {}

    def wait_for_the_person():
        try:
            decided['allowed'] = CodingAdapter(store).approval(
                run_row, 'item/commandExecution/requestApproval',
                {'cwd': str(store.root), 'command': ['python', '-c', 'print(1)'],
                 'permissions': [], 'grantRoot': None}, None)
        except Exception as exc:                                   # a wait must never kill the run
            decided['error'] = '%s: %s' % (type(exc).__name__, exc)

    thread = threading.Thread(target=wait_for_the_person, daemon=True)
    thread.start()
    approval_id, entry, items = None, None, []
    deadline = time.time() + min(wait, 120)
    while time.time() < deadline and approval_id is None:
        if decided:
            # The raise itself finished (or failed) without leaving a pending ask: waiting longer
            # would only hide the reason it did.
            break
        time.sleep(1)
        items = (client.call('/api/approvals?conversation=' + urllib.parse.quote(conversation))
                 or {}).get('items') or []
        pending = [item for item in items
                   if item.get('state') == 'pending' and item.get('job_id') == job_id]
        if pending:
            approval_id = pending[0]['id']
        entry, work = _work_row(client, conversation, job_id)
    c1 = bool(approval_id) and bool(entry) and entry.get('needs_you') is True \
        and entry.get('priority') == 'now' and (entry.get('related') or {}).get('approvals') == 1 \
        and ((entry.get('direct') or {}).get('action') == 'answer') \
        and ((entry.get('direct') or {}).get('route') == '/api/approval') \
        and bool(entry.get('reason')) and bool(entry.get('next')) \
        and entry.get('age_seconds') is not None and work.get('grouping') == 'project' \
        and 'needs_you' in (work.get('filters') or {})
    journey['claims']['a real ask becomes one attention row'] = {
        'status': 'PASSED' if c1 else 'FAILED',
        'detail': {'synthetic_input': 'the job and the run are synthetic (real Store API); the ask, '
                                      'the card and the wait are the coding adapter\'s own',
                   'conversation': conversation, 'project': project, 'job': job_id,
                   'approval': approval_id, 'seconds_to_raise': round(wait - (deadline - time.time()), 1),
                   'row': {'priority': (entry or {}).get('priority'),
                           'needs_you': (entry or {}).get('needs_you'),
                           'age_seconds': (entry or {}).get('age_seconds'),
                           'reason': (entry or {}).get('reason'),
                           'next': (entry or {}).get('next'),
                           'related': (entry or {}).get('related'),
                           'direct': (entry or {}).get('direct')},
                   'grouping': work.get('grouping'), 'filters': work.get('filters'),
                   'card': [item for item in items if item.get('id') == approval_id]}}

    # C2 — the person answers once and the waiting work continues (no second ask).
    resolved = client.refusal('/api/approval', {'id': approval_id, 'allow': True,
                                                'conversation': conversation})
    thread.join(timeout=15)
    entry2, _ = _work_row(client, conversation, job_id)
    with contextlib.closing(store.connect()) as db:
        run_state = db.execute('SELECT state FROM runs WHERE id=?', (run['id'],)).fetchone()
    run_after = run_state['state'] if run_state else None
    c2 = resolved.get('refused') is False and (resolved.get('answer') or {}).get('status') == 'APPROVED' \
        and decided.get('allowed') is True and not thread.is_alive() \
        and bool(entry2) and entry2.get('needs_you') is False \
        and (entry2.get('related') or {}).get('approvals') == 0 and run_after == 'RUNNING'
    journey['claims']['one action resolves it and the work continues'] = {
        'status': 'PASSED' if c2 else 'FAILED',
        'detail': {'answer': resolved, 'adapter_allowed': decided.get('allowed'),
                   'adapter_error': decided.get('error'), 'run_state_after': run_after,
                   'row_after': {'needs_you': (entry2 or {}).get('needs_you'),
                                 'priority': (entry2 or {}).get('priority'),
                                 'related': (entry2 or {}).get('related'),
                                 'direct': (entry2 or {}).get('direct'),
                                 'state': (entry2 or {}).get('state')}}}

    # C3 — the same ask cannot be answered twice.
    second = client.refusal('/api/approval', {'id': approval_id, 'allow': True,
                                              'conversation': conversation})
    journey['claims']['the same ask cannot be answered twice'] = {
        'status': 'PASSED' if second.get('refused') else 'FAILED', 'detail': second}
    statuses = [claim_result.get('status') for claim_result in journey['claims'].values()]
    journey['status'] = 'PASSED' if all(value == 'PASSED' for value in statuses) else 'FAILED'
    if journey['status'] == 'FAILED':
        journey['problem'] = '; '.join(name for name, claim_result in journey['claims'].items()
                                       if claim_result.get('status') != 'PASSED')
    return journey


def journey_recovery(client, ctx, wait=120, poll=3):
    """§27 Recovery — a real failure keeps its work and its reason; retry is bounded."""
    journey = {'id': 'J-RECOV', 'name': 'A real failure keeps its work; retry is bounded',
               'shell_required': False,
               'requirements': ['Recovery: failures without lost work',
                                'Recovery: retry without duplicating effects'],
               'claims': {}, 'detail': {}}
    fixture = ensure_fixture(Path(ctx['fixtures']) / 'kibble-repo')
    project = client.call('/api/project', {'name': 'acceptance-recovery-%d' % int(time.time()),
                                           'root': fixture['root'],
                                           'context': 'V2-18 acceptance journey'})['id']
    conversation = client.call('/api/conversation', {'project': project})['id']
    text = 'Change add() in calc.py so it returns the sum of its arguments.'
    client.call('/api/send', {'text': text, 'conversation': conversation})
    submission, seen = None, []
    deadline = time.time() + wait
    while time.time() < deadline:
        rows = [row for row in _submissions(client, conversation) if row.get('text') == text]
        if rows:
            submission = rows[0]
            seen.append(submission.get('state'))
            if submission.get('state') in ('FAILED', 'INTERRUPTED'):
                break
        time.sleep(poll)
    sid = (submission or {}).get('id')
    reason = (submission or {}).get('error')
    c1 = bool(submission) and submission.get('state') in ('FAILED', 'INTERRUPTED') \
        and bool(reason) and submission.get('job_id') in (None, '') \
        and submission.get('text') == text
    journey['claims']['a real failure keeps the request and its reason'] = {
        'status': 'PASSED' if c1 else 'FAILED',
        'detail': {'synthetic_input': 'a coding request for the fixture repository with no test '
                                      'command set: a real refusal on the real path, recorded as an '
                                      'input, not as engine state',
                   'conversation': conversation, 'project': project,
                   'submission': {key: (submission or {}).get(key)
                                  for key in ('id', 'state', 'error', 'job_id', 'text')},
                   'states_seen': seen}}

    # C2 — one bounded retry, on the same stored request, with no duplicate; and the boundary: a
    # request that is not FAILED/INTERRUPTED cannot be retried at all.
    retried = client.refusal('/api/retry', {'id': sid}) if sid else {'refused': False}
    time.sleep(2)
    after = [row for row in _submissions(client, conversation) if row.get('text') == text]
    settled, deadline = None, time.time() + wait
    while time.time() < deadline:
        rows = [row for row in _submissions(client, conversation) if row.get('text') == text]
        if rows and rows[0].get('state') in ('FAILED', 'INTERRUPTED'):
            settled = rows[0]
            break
        time.sleep(poll)
    chat_text = 'V2-18 recovery boundary: answer with the single word ready.'
    client.call('/api/send', {'text': chat_text, 'kind': 'chat', 'conversation': conversation})
    chat, deadline = None, time.time() + wait
    while time.time() < deadline:
        rows = [row for row in _submissions(client, conversation) if row.get('text') == chat_text]
        if rows and rows[0].get('state') != 'PLANNING':
            chat = rows[0]
            break
        time.sleep(poll)
    boundary = client.refusal('/api/retry', {'id': (chat or {}).get('id')}) if chat \
        else {'refused': False}
    c2 = retried.get('refused') is False and (retried.get('answer') or {}).get('id') == sid \
        and len(after) == 1 and settled is not None and settled.get('id') == sid \
        and settled.get('error') == reason \
        and boundary.get('refused') is True and 'not ready for retry' in str(boundary.get('sentence'))
    journey['claims']['retry is bounded and duplicates nothing'] = {
        'status': 'PASSED' if c2 else 'FAILED',
        'detail': {'first_retry': retried,
                   'settled_after_retry': {'state': (settled or {}).get('state'),
                                           'error': (settled or {}).get('error')},
                   'submissions_for_this_request': len(after),
                   'non_retryable_submission': {'id': (chat or {}).get('id'),
                                                'state': (chat or {}).get('state'),
                                                'text': (chat or {}).get('text')},
                   'boundary_refusal': boundary}}
    statuses = [claim_result.get('status') for claim_result in journey['claims'].values()]
    journey['status'] = 'PASSED' if all(value == 'PASSED' for value in statuses) else 'FAILED'
    if journey['status'] == 'FAILED':
        journey['problem'] = '; '.join(name for name, claim_result in journey['claims'].items()
                                       if claim_result.get('status') != 'PASSED')
    return journey


# ------------------------------------------------------------------------------------------ remote
def _plain_get(url, timeout=15):
    """A GET with no Kel session at all: no bearer, no cookie, and redirects not followed."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(urllib.request.Request(url, method='GET'), timeout=timeout) as response:
            return {'status': response.status, 'location': response.headers.get('Location'),
                    'body': response.read(6000).decode(errors='replace')}
    except urllib.error.HTTPError as exc:
        return {'status': exc.code, 'location': exc.headers.get('Location') if exc.headers else None,
                'body': exc.read(6000).decode(errors='replace')}
    except Exception as exc:
        return {'status': None, 'problem': '%s: %s' % (type(exc).__name__, exc)}


def _running_gateway():
    """The web-host process listening right now: pid, port and the command line that names it."""
    script = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'webui' } | "
              "ForEach-Object { $p=$_; $c=Get-NetTCPConnection -State Listen -ErrorAction "
              "SilentlyContinue | Where-Object OwningProcess -eq $p.ProcessId | "
              "Select-Object -First 1; if($c){ Write-Output ($p.ProcessId.ToString() + '|' + "
              "$c.LocalPort.ToString() + '|' + $p.CommandLine) } }")
    out, _, _ = powershell(script, timeout=120)
    for line in out.splitlines():
        parts = line.split('|')
        if len(parts) >= 3:
            try:
                return {'pid': int(parts[0]), 'port': int(parts[1]), 'command_line': '|'.join(parts[2:])}
            except ValueError:
                continue
    return None


def journey_remote(client, ctx, gateway=None):
    """§27 Remote — the gateway refuses an unauthenticated request and carries no credential."""
    journey = {'id': 'J-REMOTE', 'name': 'The gateway gate, and no credential in the client',
               'shell_required': False, 'claims': {},
               'requirements': ['Remote: secure browser use'], 'detail': {}}
    gateway = gateway or ctx.get('gateway')
    found = {'url': gateway} if gateway else _running_gateway()
    if not found:
        journey['status'] = 'PENDING'
        journey['problem'] = ('no web-host gateway is running that this run can prove: start one '
                              'with `bun run webui` and pass --gateway <url>')
        return journey
    pid, port = found.get('pid'), found.get('port')
    if port is None:
        parsed = urllib.parse.urlparse(str(gateway))
        port = parsed.port
    owner = port_owner(port) if port else None
    command_line = found.get('command_line') or (process_command_line(pid) if pid else None)
    problems = []
    if not pid or owner != pid:
        problems.append('port %s is owned by %s, not pid %s' % (port, owner, pid))
    if not command_line or 'webui' not in str(command_line).lower():
        problems.append('pid %s is not a Kel web-host process' % pid)
    if problems:
        journey['status'] = 'PENDING'
        journey['problem'] = ('the running gateway could not be owned by this run: %s'
                              % '; '.join(problems))
        journey['detail'] = {'pid': pid, 'port': port, 'port_owner': owner,
                             'command_line': command_line}
        return journey
    url = str(gateway or 'http://127.0.0.1:%d/' % port)
    root = _plain_get(url)
    state = _plain_get(urllib.parse.urljoin(url, 'api/state'))
    token = client.token
    # The app shell at `/` is served without a session so the sign-in surface can load; the
    # session gate is on the API, which refuses a request that carries no session.
    c1 = state.get('status') in (401, 403) and 'auth' in str(state.get('body') or '').lower()
    leaked = [probe for probe in (root, state) if token and token in str(probe.get('body') or '')]
    c2 = not leaked
    text = str(command_line).replace('\\', '/')
    head = text.split('/desktop/', 1)[0]
    worktree = head.split()[-1].strip('"') if head.split() and '/desktop/' in text else None
    journey['claims']['an unauthenticated API request is refused'] = {
        'status': 'PASSED' if c1 else 'FAILED',
        'detail': {'url': url, 'api_state_status': state.get('status'),
                   'api_state_body': str(state.get('body') or '')[:200],
                   'root_status': root.get('status'),
                   'note': ('/ serves the app shell so the sign-in surface can load; the gate is on '
                            'the API, which refuses a request with no session')}}
    journey['claims']['no credential reaches the client'] = {
        'status': 'PASSED' if c2 else 'FAILED',
        'detail': {'engine_token_in_body': bool(leaked),
                   'searched': ['/', 'api/state']}}
    journey['detail'] = {'gateway': {'pid': pid, 'port': port, 'port_owner': owner,
                                      'url': url, 'worktree': worktree,
                                      'command_line': command_line},
                         'labelled': 'the gateway this run probed is the one listening now; its '
                                     'renderer is Astra\'s (Shell presentation is out of scope here)',
                         'api_state_body_head': str(state.get('body') or '')[:200]}
    statuses = [claim_result.get('status') for claim_result in journey['claims'].values()]
    journey['status'] = 'PASSED' if all(value == 'PASSED' for value in statuses) else 'FAILED'
    if journey['status'] == 'FAILED':
        journey['problem'] = '; '.join(name for name, claim_result in journey['claims'].items()
                                       if claim_result.get('status') != 'PASSED')
    return journey


JOURNEYS = {'J-FIX': journey_fix_capture, 'J-UPGRADE': journey_upgrade,
            'J-SEC': journey_security, 'J-KBU': journey_kibble,
            'J-KBU-NEG': journey_kibble_negatives, 'J-MODEL': journey_model,
            'J-CONV': journey_conversation, 'J-PROJ': journey_projects,
            'J-MEM': journey_memory, 'J-RECIPE': journey_recipes,
            'J-NET': journey_network, 'J-CONN': journey_connections,
            'J-TRANS': journey_transcription, 'J-ACTIVITY': journey_activity,
            'J-WORK': journey_work, 'J-ATTN': journey_attention,
            'J-RECOV': journey_recovery, 'J-REMOTE': journey_remote}


# ----------------------------------------------------------------------------------------------- runner
def main(argv=None):
    parser = argparse.ArgumentParser(description='V2-18 synthetic acceptance journeys')
    parser.add_argument('--root', default=DEFAULT_ROOT, help='the engine data root to attach to')
    parser.add_argument('--fixtures', default=DEFAULT_FIXTURES, help='where synthetic repositories live')
    parser.add_argument('--journeys', default='J-FIX,J-UPGRADE,J-SEC,J-KBU',
                        help='comma-separated journey ids (or ALL)')
    parser.add_argument('--out', default=None, help='evidence JSON path')
    parser.add_argument('--wait', type=int, default=900, help='seconds a dispatched mission may take')
    parser.add_argument('--poll', type=int, default=10)
    parser.add_argument('--no-runtime', action='store_true',
                        help='do not let the real runtime dispatch (claims become PENDING)')
    parser.add_argument('--runtime-negatives', action='store_true',
                        help='also dispatch a mission whose test command really fails')
    parser.add_argument('--gateway', default=None,
                        help='the web-host gateway URL for J-REMOTE (default: the one listening now)')
    args = parser.parse_args(argv)

    client = EngineClient(args.root)
    identity = client.identity()
    print('engine  : %s (pid %s, port %s)' % (identity['url'], identity['pid'], identity['port']))
    print('command : %s' % identity['command_line'])
    if identity['problems']:
        print('IDENTITY PROBLEMS: %s' % '; '.join(identity['problems']))
        return 2

    wanted = list(JOURNEYS) if args.journeys.strip().upper() == 'ALL' else [
        name.strip().upper() for name in args.journeys.split(',') if name.strip()]
    unknown = [name for name in wanted if name not in JOURNEYS]
    if unknown:
        print('unknown journeys: %s' % ', '.join(unknown))
        return 2

    ctx = {'root': args.root, 'fixtures': args.fixtures, 'gateway': args.gateway}
    results = []
    for name in wanted:
        started = time.time()
        try:
            if name == 'J-KBU':
                result = journey_kibble(client, ctx, dispatch=not args.no_runtime, wait=args.wait,
                                        poll=args.poll)
            elif name == 'J-KBU-NEG':
                result = journey_kibble_negatives(client, ctx, dispatch=args.runtime_negatives,
                                                  wait=args.wait, poll=args.poll)
            elif name == 'J-MODEL':
                result = journey_model(client, ctx, wait=args.wait, poll=args.poll)
            elif name == 'J-CONV':
                result = journey_conversation(client, ctx, wait=args.wait, poll=args.poll)
            elif name == 'J-WORK':
                result = journey_work(client, ctx, wait=args.wait, poll=args.poll)
            elif name == 'J-ATTN':
                result = journey_attention(client, ctx, wait=min(args.wait, 120))
            elif name == 'J-RECOV':
                result = journey_recovery(client, ctx, wait=min(args.wait, 180),
                                          poll=max(2, args.poll // 3))
            elif name == 'J-REMOTE':
                result = journey_remote(client, ctx, gateway=args.gateway)
            else:
                result = JOURNEYS[name](client, ctx)
        except (PolicyRefusal, IdentityError) as exc:
            result = {'id': name, 'name': name, 'status': 'FAILED', 'problem': str(exc)}
        except Exception as exc:                                   # a journey must never kill the run
            result = {'id': name, 'name': name, 'status': 'FAILED',
                      'problem': '%s: %s' % (type(exc).__name__, exc)}
        result['seconds'] = round(time.time() - started, 1)
        results.append(result)
        print('%-10s %-8s %5.1fs  %s' % (result.get('id'), result.get('status'),
                                         result['seconds'], result.get('name')))
        for claim, value in (result.get('claims') or {}).items():
            print('    %-36s %s' % (claim, value.get('status')))

    report = {'journeys': results, 'identity': identity, 'root': args.root,
              'fixtures': args.fixtures, 'started': time.strftime('%Y-%m-%d %H:%M:%S'),
              'labelled_fixtures': ['synthetic findings and fixture repositories; the engine, '
                                    'store, HTTP surface, workspaces and runtimes are real']}
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=False), encoding='utf-8')
        print('evidence: %s' % out)
    failed = [result for result in results if result.get('status') == 'FAILED']
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
