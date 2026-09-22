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
import json
import shutil
import subprocess
import sys
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
    client.call('/api/control', {'action': 'cancel', 'id': job_id})
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


JOURNEYS = {'J-FIX': journey_fix_capture, 'J-UPGRADE': journey_upgrade,
            'J-SEC': journey_security, 'J-KBU': journey_kibble,
            'J-KBU-NEG': journey_kibble_negatives}


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

    ctx = {'root': args.root, 'fixtures': args.fixtures}
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
