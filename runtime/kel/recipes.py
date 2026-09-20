"""Reusable workflow recipes (V1.3 migration 004).

Validated declarative JSON templates that compile into the existing CompletionContract
(docs/v1.3/KEL_V1.3_RECIPE_SPEC.md). There is no recipe runtime: the engine still executes,
verifies, reviews, and produces verdicts. Unknown fields are errors; undeclared permissions
are compile errors; UNCERTAIN must always remain possible.
"""
import contextlib
import json
import re
import time

from .core import PolicyError, digest, encode, uid, validate_contract
from .memory import _backup, _is_fresh_database, _table

MIGRATION_VERSION = 4
MIGRATION_NAME = 'v13-recipes'

DDL = """
CREATE TABLE IF NOT EXISTS recipes(
  recipe_id TEXT NOT NULL,
  recipe_version TEXT NOT NULL,
  scope TEXT NOT NULL,
  project_id TEXT NOT NULL DEFAULT '',
  digest TEXT NOT NULL,
  data TEXT NOT NULL,
  source TEXT NOT NULL,
  created REAL NOT NULL,
  updated REAL NOT NULL,
  PRIMARY KEY(recipe_id, recipe_version, scope, project_id));
"""

TOP_FIELDS = {'schema_version', 'recipe_id', 'recipe_version', 'name', 'description', 'source',
              'kind', 'inputs', 'steps', 'permissions', 'verification', 'terminal_states',
              'budget', 'retry_policy'}
INPUT_FIELDS = {'name', 'type', 'required', 'default', 'choices', 'max_chars', 'description'}
STEP_FIELDS = {'id', 'title', 'action', 'kind_override', 'objective', 'depends_on', 'checks',
               'retries'}
CHECK_FIELDS = {'kind', 'value', 'rubric'}
RETRY_FIELDS = {'max_attempts', 'on_fail'}
POLICY_FIELDS = {'max_attempts_per_milestone', 'provider_switch_after'}
PERMISSIONS = ('project:read', 'project:write', 'tests:run', 'web:search', 'files:attach',
               'commands:run')
CHECK_KINDS = ('contains', 'min_chars', 'manual_review')
VERIFICATION_KINDS = ('contains', 'min_chars', 'manual_review', 'repository_evidence',
                      'citation_evidence')
KINDS = ('coding', 'document', 'research', 'mixed')
ACTIONS = ('plan', 'work', 'check', 'review')
ON_FAIL = ('retry', 'escalate', 'block')
INPUT_TYPES = ('text', 'path', 'choice', 'bool')
TERMINAL_STATES = ('VERIFIED', 'FAILED', 'UNCERTAIN')
MAX_STEPS = 5
VERSION_RE = re.compile(r'^\d+\.\d+\.\d+$')
ID_RE = re.compile(r'^[a-z0-9-]{3,64}$')
INPUT_NAME_RE = re.compile(r'^[a-z][a-z0-9_]{0,39}$')
PLACEHOLDER_RE = re.compile(r'\{([a-z0-9_]+)\}')


def ensure_schema(store):
    with contextlib.closing(store.connect()) as db:
        if _table(db, 'schema_migrations') and db.execute(
                'SELECT 1 FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,)).fetchone():
            return
        first = not _table(db, 'schema_migrations')
        if first:
            if not _is_fresh_database(db):
                _backup(store, db)
            db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                       'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL,'
                       ' note TEXT)')
        db.executescript(DDL)
        db.execute('INSERT OR IGNORE INTO schema_migrations VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(), None))


def _fail(path, message):
    raise PolicyError('Recipe invalid at %s: %s' % (path, message))


def _unknown(path, value, allowed):
    extra = set(value) - set(allowed)
    if extra:
        _fail(path, 'unknown field(s) %s — supported fields: %s'
              % (', '.join(sorted(extra)), ', '.join(sorted(allowed))))


def _text(path, value, limit, *, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()) or len(value) > limit:
        _fail(path, 'must be a string of 1 to %d characters' % limit)
    return value


def validate_recipe(data):
    """Strict validation. Returns the recipe unchanged when valid; raises PolicyError."""
    if not isinstance(data, dict):
        _fail('recipe', 'the recipe must be a JSON object')
    _unknown('recipe', data, TOP_FIELDS)
    if data.get('schema_version') != 1 or isinstance(data.get('schema_version'), bool):
        _fail('schema_version', 'must be 1')
    if not isinstance(data.get('recipe_id'), str) or not ID_RE.match(data.get('recipe_id', '')):
        _fail('recipe_id', 'must be a slug like fix-bug (3-64 chars: a-z, 0-9, -)')
    _text('name', data.get('name'), 80)
    _text('description', data.get('description'), 500)
    if not isinstance(data.get('recipe_version'), str) or not VERSION_RE.match(data.get('recipe_version', '')):
        _fail('recipe_version', 'must be MAJOR.MINOR.PATCH')
    source = data.get('source')
    if not (source in ('builtin', 'project') or (isinstance(source, str)
            and source.startswith('from_job:') and len(source) > 9)):
        _fail('source', "must be 'builtin', 'project', or 'from_job:<job_id>'")
    if data.get('kind') not in KINDS:
        _fail('kind', 'must be one of %s' % ', '.join(KINDS))
    inputs = data.get('inputs')
    if not isinstance(inputs, list) or len(inputs) > 12:
        _fail('inputs', 'must be a list of at most 12 inputs')
    input_names = []
    for index, item in enumerate(inputs):
        path = 'inputs[%d]' % index
        if not isinstance(item, dict):
            _fail(path, 'each input must be an object')
        _unknown(path, item, INPUT_FIELDS)
        name = item.get('name')
        if not isinstance(name, str) or not INPUT_NAME_RE.match(name):
            _fail(path + '.name', 'must match [a-z][a-z0-9_]{0,39}')
        if name in input_names:
            _fail(path + '.name', 'duplicate input name')
        if item.get('type') not in INPUT_TYPES:
            _fail(path + '.type', 'must be one of %s' % ', '.join(INPUT_TYPES))
        if not isinstance(item.get('required'), bool):
            _fail(path + '.required', 'must be true or false')
        if 'choices' in item:
            choices = item['choices']
            if item['type'] != 'choice' or not isinstance(choices, list) or not choices \
                    or not all(isinstance(c, str) and c for c in choices):
                _fail(path + '.choices', 'only choice inputs carry a nonempty choices list')
        if 'default' in item:
            default = item['default']
            if item['type'] == 'bool' and not isinstance(default, bool):
                _fail(path + '.default', 'must be true or false for a bool input')
            if item['type'] in ('text', 'path') and not isinstance(default, str):
                _fail(path + '.default', 'must be a string')
            if item['type'] == 'choice' and default not in item.get('choices', []):
                _fail(path + '.default', 'must be one of the declared choices')
        if 'max_chars' in item and (item['type'] != 'text' or type(item['max_chars']) is not int
                                    or not 1 <= item['max_chars'] <= 10000):
            _fail(path + '.max_chars', 'only text inputs carry max_chars (1-10000)')
        if 'description' in item:
            _text(path + '.description', item['description'], 200)
        input_names.append(name)
    steps = data.get('steps')
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        _fail('steps', 'must be a list of 1 to %d steps' % MAX_STEPS)
    step_ids = []
    for index, step in enumerate(steps):
        path = 'steps[%d]' % index
        if not isinstance(step, dict):
            _fail(path, 'each step must be an object')
        _unknown(path, step, STEP_FIELDS)
        sid = step.get('id')
        if not isinstance(sid, str) or not ID_RE.match(sid):
            _fail(path + '.id', 'must be a slug (3-64 chars: a-z, 0-9, -)')
        if sid in step_ids:
            _fail(path + '.id', 'duplicate step id')
        _text(path + '.title', step.get('title'), 80)
        if step.get('action') not in ACTIONS:
            _fail(path + '.action', 'must be one of %s' % ', '.join(ACTIONS))
        override = step.get('kind_override')
        if override is not None and override not in ('coding', 'document', 'research'):
            _fail(path + '.kind_override', 'must be coding, document, research, or omitted')
        if data['kind'] != 'mixed' and override is not None:
            _fail(path + '.kind_override', 'kind_override is only allowed for mixed recipes')
        if data['kind'] == 'mixed' and override is None:
            _fail(path + '.kind_override', 'mixed recipes require an explicit kind_override '
                  'per step (coding, document, or research)')
        _text(path + '.objective', step.get('objective'), 600)
        depends = step.get('depends_on', [])
        if not isinstance(depends, list) or not all(isinstance(d, str) for d in depends):
            _fail(path + '.depends_on', 'must be a list of step ids')
        checks = step.get('checks')
        if not isinstance(checks, list) or not 1 <= len(checks) <= 20:
            _fail(path + '.checks', 'each step needs 1 to 20 checks')
        for cindex, check in enumerate(checks):
            cpath = path + '.checks[%d]' % cindex
            if not isinstance(check, dict):
                _fail(cpath, 'each check must be an object')
            _unknown(cpath, check, CHECK_FIELDS)
            if check.get('kind') not in CHECK_KINDS:
                _fail(cpath + '.kind', 'trusted checks only: %s' % ', '.join(CHECK_KINDS))
            if check['kind'] == 'contains':
                _text(cpath + '.value', check.get('value'), 200)
            if check['kind'] == 'min_chars' and (type(check.get('value')) is not int
                                                 or not 1 <= check['value'] <= 100000):
                _fail(cpath + '.value', 'min_chars needs an integer 1-100000')
            if check['kind'] == 'manual_review':
                _text(cpath + '.rubric', check.get('rubric'), 500)
        retries = step.get('retries')
        if not isinstance(retries, dict):
            _fail(path + '.retries', 'every step needs retries {max_attempts, on_fail}')
        _unknown(path + '.retries', retries, RETRY_FIELDS)
        if type(retries.get('max_attempts')) is not int or not 1 <= retries['max_attempts'] <= 4:
            _fail(path + '.retries.max_attempts', 'must be an integer 1 to 4')
        if retries.get('on_fail') not in ON_FAIL:
            _fail(path + '.retries.on_fail', 'must be one of %s' % ', '.join(ON_FAIL))
        step_ids.append(sid)
    for index, step in enumerate(steps):
        depends = step.get('depends_on', [])
        for ref in depends:
            if ref not in step_ids:
                _fail('steps[%d].depends_on' % index, 'references unknown step %r' % ref)
            if ref == step['id']:
                _fail('steps[%d].depends_on' % index, 'a step cannot depend on itself')
    # acyclic dependency graph
    resolved, pending = set(), {s['id']: set(s.get('depends_on', [])) for s in steps}
    while pending:
        ready = {sid for sid, deps in pending.items() if deps <= resolved}
        if not ready:
            _fail('steps', 'the dependency graph contains a cycle')
        for sid in ready:
            del pending[sid]
        resolved |= ready
    for index, step in enumerate(steps):
        for placeholder in PLACEHOLDER_RE.findall(step['objective']):
            if placeholder not in input_names:
                _fail('steps[%d].objective' % index,
                      'placeholder {%s} references no declared input' % placeholder)
    permissions = data.get('permissions')
    if not isinstance(permissions, list) or len(permissions) != len(set(permissions)) \
            or not all(p in PERMISSIONS for p in permissions):
        _fail('permissions', 'must be a subset of %s' % ', '.join(PERMISSIONS))
    kinds_used = {data['kind']} | {s.get('kind_override') for s in steps
                 if s.get('kind_override')}
    if 'coding' in kinds_used and 'project:read' not in permissions:
        _fail('permissions', 'coding steps require project:read')
    if 'research' in kinds_used and 'web:search' not in permissions:
        _fail('permissions', 'research steps require web:search')
    if 'commands:run' not in permissions and any(
            s['id'] in ('package', 'smoke') or 'package command' in s['objective'].lower()
            or 'smoke command' in s['objective'].lower() for s in steps):
        _fail('permissions', 'steps that run declared package or smoke commands require '
              'commands:run')
    verification = data.get('verification')
    if not isinstance(verification, list) or not verification \
            or not all(v in VERIFICATION_KINDS for v in verification):
        _fail('verification', 'must be a nonempty subset of %s' % ', '.join(VERIFICATION_KINDS))
    terminal = data.get('terminal_states')
    if not isinstance(terminal, list) or not terminal \
            or not all(t in TERMINAL_STATES for t in terminal) or 'UNCERTAIN' not in terminal:
        _fail('terminal_states', 'must include UNCERTAIN (a recipe may not promise certainty)')
    budget = data.get('budget', 8)
    if type(budget) is not int or not 1 <= budget <= 100:
        _fail('budget', 'must be an integer 1 to 100')
    policy = data.get('retry_policy')
    if not isinstance(policy, dict):
        _fail('retry_policy', 'must be {max_attempts_per_milestone, provider_switch_after}')
    _unknown('retry_policy', policy, POLICY_FIELDS)
    if type(policy.get('max_attempts_per_milestone')) is not int \
            or not 1 <= policy['max_attempts_per_milestone'] <= 4:
        _fail('retry_policy.max_attempts_per_milestone', 'must be an integer 1 to 4')
    if policy.get('provider_switch_after') != 2:
        _fail('retry_policy.provider_switch_after', 'must be 2 (engine behavior)')
    return data

FIX_BUG = {
    'schema_version': 1,
    'recipe_id': 'fix-bug',
    'recipe_version': '1.0.0',
    'name': 'Fix Bug',
    'description': 'Reproduce, diagnose, implement, test, and review a bug fix in this project.',
    'source': 'builtin',
    'kind': 'coding',
    'inputs': [
        {'name': 'bug', 'type': 'text', 'required': True, 'max_chars': 2000,
         'description': 'What is broken, and how do we see it?'},
        {'name': 'scope', 'type': 'text', 'required': False, 'max_chars': 500,
         'description': 'Optional area or paths to focus on.'},
    ],
    'steps': [
        {'id': 'reproduce', 'title': 'Reproduce the failure', 'action': 'work',
         'objective': 'Reproduce the reported failure: {bug}. Record the exact command and '
                      'output.',
         'depends_on': [],
         'checks': [
             {'kind': 'min_chars', 'value': 80},
             {'kind': 'manual_review',
              'rubric': 'The reproduction is concrete: exact steps or command, observed versus '
                        'expected.'},
         ],
         'retries': {'max_attempts': 2, 'on_fail': 'escalate'}},
        {'id': 'fix', 'title': 'Implement the fix', 'action': 'work',
         'objective': 'Diagnose and implement the smallest correct fix for the reproduced '
                      'failure. Scope hint: {scope}.',
         'depends_on': ['reproduce'],
         'checks': [
             {'kind': 'manual_review',
              'rubric': 'The change addresses the reproduced failure without unrelated edits.'},
         ],
         'retries': {'max_attempts': 4, 'on_fail': 'escalate'}},
        {'id': 'verify', 'title': 'Tests and independent review', 'action': 'review',
         'objective': 'Run the project test command and have the result independently reviewed.',
         'depends_on': ['fix'],
         'checks': [
             {'kind': 'manual_review',
              'rubric': 'Tests pass on the current tree and the fix matches the reproduction.'},
         ],
         'retries': {'max_attempts': 2, 'on_fail': 'block'}},
    ],
    'permissions': ['project:read', 'project:write', 'tests:run'],
    'verification': ['repository_evidence', 'manual_review'],
    'terminal_states': ['VERIFIED', 'FAILED', 'UNCERTAIN'],
    'budget': 10,
    'retry_policy': {'max_attempts_per_milestone': 4, 'provider_switch_after': 2},
}

AUDIT_AND_REPAIR = {
    'schema_version': 1,
    'recipe_id': 'audit-and-repair',
    'recipe_version': '1.0.0',
    'name': 'Audit and Repair',
    'description': 'Audit an area of this project, repair the approved findings, then verify.',
    'source': 'builtin',
    'kind': 'mixed',
    'inputs': [
        {'name': 'area', 'type': 'text', 'required': False, 'max_chars': 500,
         'description': 'Optional area or paths to audit.'},
        {'name': 'depth', 'type': 'choice', 'required': False, 'default': 'quick',
         'choices': ['quick', 'deep'], 'description': 'How thorough the audit should be.'},
    ],
    'steps': [
        {'id': 'audit', 'title': 'Audit the project', 'action': 'work',
         'kind_override': 'document',
         'objective': 'Audit {area} at {depth} depth. Record concrete findings with file '
                      'references.',
         'depends_on': [],
         'checks': [
             {'kind': 'min_chars', 'value': 200},
             {'kind': 'manual_review',
              'rubric': 'Findings are concrete, correctly scoped, and cite real paths.'},
         ],
         'retries': {'max_attempts': 2, 'on_fail': 'escalate'}},
        {'id': 'repair', 'title': 'Repair approved findings', 'action': 'work',
         'kind_override': 'coding',
         'objective': 'Repair the audited findings for {area} that are approved for this run.',
         'depends_on': ['audit'],
         'checks': [
             {'kind': 'manual_review',
              'rubric': 'The change addresses the audited findings without unrelated edits.'},
         ],
         'retries': {'max_attempts': 4, 'on_fail': 'escalate'}},
        {'id': 'verify', 'title': 'Verify the repair', 'action': 'review',
         'kind_override': 'document',
         'objective': 'Run the project test command and independently confirm the repair.',
         'depends_on': ['repair'],
         'checks': [
             {'kind': 'manual_review',
              'rubric': 'Tests pass and the repair matches the audited findings.'},
         ],
         'retries': {'max_attempts': 2, 'on_fail': 'block'}},
    ],
    'permissions': ['project:read', 'project:write', 'tests:run', 'files:attach'],
    'verification': ['repository_evidence', 'manual_review'],
    'terminal_states': ['VERIFIED', 'FAILED', 'UNCERTAIN'],
    'budget': 12,
    'retry_policy': {'max_attempts_per_milestone': 4, 'provider_switch_after': 2},
}

SHIP_RELEASE = {
    'schema_version': 1,
    'recipe_id': 'ship-release',
    'recipe_version': '1.0.0',
    'name': 'Ship Release',
    'description': 'Baseline, test, package, smoke, and manifest a release of this project.',
    'source': 'builtin',
    'kind': 'mixed',
    'inputs': [
        {'name': 'version', 'type': 'text', 'required': True, 'max_chars': 60,
         'description': 'The release version being prepared.'},
        {'name': 'notes', 'type': 'text', 'required': False, 'max_chars': 1000,
         'description': 'Optional release notes.'},
    ],
    'steps': [
        {'id': 'baseline', 'title': 'Record the release baseline', 'action': 'work',
         'kind_override': 'document',
         'objective': 'Record the release baseline for {version}: tree state, hashes, and the '
                      'declared commands.',
         'depends_on': [],
         'checks': [
             {'kind': 'min_chars', 'value': 100},
             {'kind': 'manual_review',
              'rubric': 'The baseline records real hashes and the current tree state.'},
         ],
         'retries': {'max_attempts': 1, 'on_fail': 'block'}},
        {'id': 'tests', 'title': 'Run the test command', 'action': 'check',
         'kind_override': 'document',
         'objective': 'Run the project test command and record the trusted output for {version}.',
         'depends_on': ['baseline'],
         'checks': [
             {'kind': 'min_chars', 'value': 40},
             {'kind': 'manual_review', 'rubric': 'The trusted test output is recorded.'},
         ],
         'retries': {'max_attempts': 2, 'on_fail': 'block'}},
        {'id': 'package', 'title': 'Run the package command', 'action': 'work',
         'kind_override': 'document',
         'objective': 'Produce the release package for {version} with the declared package '
                      'command.',
         'depends_on': ['tests'],
         'checks': [
             {'kind': 'min_chars', 'value': 40},
             {'kind': 'manual_review',
              'rubric': 'The package command ran from the declared project commands.'},
         ],
         'retries': {'max_attempts': 2, 'on_fail': 'escalate'}},
        {'id': 'smoke', 'title': 'Run the smoke command', 'action': 'check',
         'kind_override': 'document',
         'objective': 'Run the declared smoke command and record its result for {version}.',
         'depends_on': ['package'],
         'checks': [
             {'kind': 'min_chars', 'value': 40},
             {'kind': 'manual_review', 'rubric': 'The smoke result is recorded and plausible.'},
         ],
         'retries': {'max_attempts': 2, 'on_fail': 'block'}},
        {'id': 'manifest', 'title': 'Write the release manifest', 'action': 'work',
         'kind_override': 'document',
         'objective': 'Write the release manifest for {version} including hashes and the freeze '
                      'record. Notes: {notes}.',
         'depends_on': ['smoke'],
         'checks': [
             {'kind': 'min_chars', 'value': 100},
             {'kind': 'manual_review',
              'rubric': 'The manifest includes the version, hashes, and the freeze record.'},
         ],
         'retries': {'max_attempts': 1, 'on_fail': 'block'}},
    ],
    'permissions': ['project:read', 'tests:run', 'commands:run', 'files:attach'],
    'verification': ['min_chars', 'manual_review'],
    'terminal_states': ['VERIFIED', 'FAILED', 'UNCERTAIN'],
    'budget': 14,
    'retry_policy': {'max_attempts_per_milestone': 4, 'provider_switch_after': 2},
}

RESEARCH_THEN_IMPLEMENT = {
    'schema_version': 1,
    'recipe_id': 'research-then-implement',
    'recipe_version': '1.0.0',
    'name': 'Research Then Implement',
    'description': 'Research a question with citations, pick an approach, implement it, verify.',
    'source': 'builtin',
    'kind': 'mixed',
    'inputs': [
        {'name': 'question', 'type': 'text', 'required': True, 'max_chars': 1000,
         'description': 'What should be researched and implemented?'},
        {'name': 'deliverable', 'type': 'text', 'required': False, 'max_chars': 300,
         'description': 'Optional shape of the expected result.'},
    ],
    'steps': [
        {'id': 'research', 'title': 'Research with citations', 'action': 'work',
         'kind_override': 'research',
         'objective': 'Research {question} using fetched sources and record the citation-backed '
                      'evidence.',
         'depends_on': [],
         'checks': [
             {'kind': 'min_chars', 'value': 200},
             {'kind': 'manual_review',
              'rubric': 'Every significant claim is backed by a fetched citation.'},
         ],
         'retries': {'max_attempts': 3, 'on_fail': 'escalate'}},
        {'id': 'approach', 'title': 'Choose the approach', 'action': 'plan',
         'kind_override': 'document',
         'objective': 'Write the chosen approach and its rationale for {question}. Deliverable: '
                      '{deliverable}.',
         'depends_on': ['research'],
         'checks': [
             {'kind': 'min_chars', 'value': 150},
             {'kind': 'manual_review', 'rubric': 'The approach follows from the research.'},
         ],
         'retries': {'max_attempts': 2, 'on_fail': 'escalate'}},
        {'id': 'implement', 'title': 'Implement the approach', 'action': 'work',
         'kind_override': 'coding',
         'objective': 'Implement the chosen approach for {question} in this project.',
         'depends_on': ['approach'],
         'checks': [
             {'kind': 'manual_review',
              'rubric': 'The implementation matches the approach without unrelated edits.'},
         ],
         'retries': {'max_attempts': 4, 'on_fail': 'escalate'}},
        {'id': 'verify', 'title': 'Verify the implementation', 'action': 'review',
         'kind_override': 'document',
         'objective': 'Run the project test command and independently review the implementation '
                      'for {question}.',
         'depends_on': ['implement'],
         'checks': [
             {'kind': 'manual_review',
              'rubric': 'Tests pass and the implementation matches the chosen approach.'},
         ],
         'retries': {'max_attempts': 2, 'on_fail': 'block'}},
    ],
    'permissions': ['project:read', 'project:write', 'tests:run', 'web:search'],
    'verification': ['citation_evidence', 'repository_evidence', 'manual_review'],
    'terminal_states': ['VERIFIED', 'FAILED', 'UNCERTAIN'],
    'budget': 14,
    'retry_policy': {'max_attempts_per_milestone': 4, 'provider_switch_after': 2},
}

CONTINUE_WORK = {
    'schema_version': 1,
    'recipe_id': 'continue-work',
    'recipe_version': '1.0.0',
    'name': 'Continue Work',
    'description': 'Resolve, validate, preserve, and resume the unfinished work in this project. '
                   'Creates no new job.',
    'source': 'builtin',
    'kind': 'document',
    'inputs': [
        {'name': 'hint', 'type': 'text', 'required': False, 'max_chars': 300,
         'description': 'Optional hint about which unfinished work you mean.'},
    ],
    'steps': [
        {'id': 'resolve', 'title': 'Resolve the candidate', 'action': 'plan',
         'objective': 'Resolve the unfinished job for this project from durable state. Hint: '
                      '{hint}.',
         'depends_on': [],
         'checks': [
             {'kind': 'manual_review',
              'rubric': 'A single candidate was resolved, or the no-candidate case was '
                        'explained.'},
         ],
         'retries': {'max_attempts': 1, 'on_fail': 'block'}},
        {'id': 'validate', 'title': 'Validate the current state', 'action': 'check',
         'objective': 'Validate the job state and session, and revalidate digest-affected '
                      'accepted milestones with explicit reasons.',
         'depends_on': ['resolve'],
         'checks': [
             {'kind': 'manual_review',
              'rubric': 'Revalidation decisions cite the changed source or dependency.'},
         ],
         'retries': {'max_attempts': 1, 'on_fail': 'block'}},
        {'id': 'preserve', 'title': 'Preserve accepted milestones', 'action': 'work',
         'objective': 'Preserve accepted milestones; reopen only retryable milestones.',
         'depends_on': ['validate'],
         'checks': [
             {'kind': 'manual_review', 'rubric': 'Accepted milestones remain frozen.'},
         ],
         'retries': {'max_attempts': 1, 'on_fail': 'block'}},
        {'id': 'resume', 'title': 'Resume the remaining work', 'action': 'work',
         'objective': 'Resume the remaining milestones through the standard execution pipeline.',
         'depends_on': ['preserve'],
         'checks': [
             {'kind': 'manual_review',
              'rubric': 'Resumed work runs through the existing engine, not a new job.'},
         ],
         'retries': {'max_attempts': 1, 'on_fail': 'block'}},
        {'id': 'review', 'title': 'Re-verify and publish', 'action': 'review',
         'objective': 'Re-verify and re-review the resumed work, then use standard Kel '
                      'publication.',
         'depends_on': ['resume'],
         'checks': [
             {'kind': 'manual_review',
              'rubric': 'Verification and review follow the standard gates.'},
         ],
         'retries': {'max_attempts': 1, 'on_fail': 'block'}},
    ],
    'permissions': ['project:read'],
    'verification': ['manual_review'],
    'terminal_states': ['VERIFIED', 'FAILED', 'UNCERTAIN'],
    'budget': 8,
    'retry_policy': {'max_attempts_per_milestone': 4, 'provider_switch_after': 2},
}

BUILTINS = (FIX_BUG, AUDIT_AND_REPAIR, SHIP_RELEASE, RESEARCH_THEN_IMPLEMENT, CONTINUE_WORK)
CONTINUE_RECIPE_ID = 'continue-work'
MAX_INPUT_CHARS = 10000


def recipe_digest(recipe):
    """Canonical digest of a validated recipe (drives immutability and pinning)."""
    return digest(recipe)


class RecipeLibrary:
    """Storage and compilation for recipes (migration 004)."""

    def __init__(self, store):
        self.store = store
        ensure_schema(store)

    def _event(self, db, recipe_id, action, detail=None):
        aggregate = 'recipe:' + recipe_id
        revision = db.execute('SELECT COALESCE(MAX(revision),0)+1 FROM events'
                              ' WHERE aggregate_id=?', (aggregate,)).fetchone()[0]
        payload = {'schema_version': 1,
                   'recipe': {'id': recipe_id, 'action': action, 'detail': detail or {}}}
        db.execute('INSERT INTO events(id,aggregate_id,revision,type,at,payload,dedupe)'
                   ' VALUES(?,?,?,?,?,?,NULL)',
                   (uid(), aggregate, revision, 'recipe.' + action, time.time(),
                    encode(payload)))

    def install_builtins(self):
        """Idempotent seeding; changed builtin content without a version bump is an error."""
        installed = 0
        with self.store.transaction() as db:
            for recipe in BUILTINS:
                validate_recipe(recipe)
                stamp = time.time()
                cur = db.execute('INSERT OR IGNORE INTO recipes VALUES(?,?,?,?,?,?,?,?,?)',
                                 (recipe['recipe_id'], recipe['recipe_version'], 'builtin', '',
                                  recipe_digest(recipe), encode(recipe), 'builtin',
                                  stamp, stamp))
                if cur.rowcount:
                    installed += 1
                    continue
                row = db.execute(
                    'SELECT digest FROM recipes WHERE recipe_id=? AND recipe_version=?'
                    " AND scope='builtin' AND project_id=''",
                    (recipe['recipe_id'], recipe['recipe_version'])).fetchone()
                if row['digest'] != recipe_digest(recipe):
                    raise PolicyError('Builtin recipe %s changed without a version bump'
                                      % recipe['recipe_id'])
        return installed

    @staticmethod
    def _version_key(value):
        return tuple(int(part) for part in str(value).split('.'))

    def _latest(self, db, recipe_id, scope, project_id):
        rows = db.execute('SELECT * FROM recipes WHERE recipe_id=? AND scope=? AND project_id=?',
                          (recipe_id, scope, project_id)).fetchall()
        if not rows:
            return None
        return max(rows, key=lambda row: self._version_key(row['recipe_version']))

    def get(self, recipe_id, *, project_id=''):
        """Project recipes shadow builtins; both stay inspectable."""
        with contextlib.closing(self.store.connect()) as db:
            row = self._latest(db, recipe_id, 'project', project_id) if project_id else None
            shadowed = bool(row)
            if row is None:
                row = self._latest(db, recipe_id, 'builtin', '')
        if row is None:
            raise PolicyError('Unknown recipe: %s' % recipe_id)
        return {'recipe': json.loads(row['data']), 'scope': row['scope'],
                'project_id': row['project_id'], 'version': row['recipe_version'],
                'digest': row['digest'], 'source': row['source'], 'shadowed': shadowed}

    def entries(self, *, project_id=''):
        with contextlib.closing(self.store.connect()) as db:
            ids = sorted({row['recipe_id'] for row in
                          db.execute('SELECT DISTINCT recipe_id FROM recipes')})
        out = []
        for recipe_id in ids:
            info = self.get(recipe_id, project_id=project_id)
            recipe = info['recipe']
            out.append({'recipe_id': recipe_id, 'name': recipe['name'],
                        'version': info['version'], 'scope': info['scope'],
                        'kind': recipe['kind'], 'digest': info['digest'],
                        'source': info['source']})
        return out

    def versions(self, recipe_id, *, project_id=''):
        with contextlib.closing(self.store.connect()) as db:
            rows = db.execute(
                'SELECT * FROM recipes WHERE recipe_id=? AND (scope=? OR (scope=? AND'
                " project_id=?)) ORDER BY created",
                (recipe_id, 'builtin', 'project', project_id)).fetchall()
        return [{'version': row['recipe_version'], 'scope': row['scope'],
                 'digest': row['digest'], 'source': row['source'], 'created': row['created']}
                for row in rows]

    def save(self, recipe, *, scope='project', project_id='', confirm=False):
        """Append-only save. Project saves require explicit user confirmation."""
        validate_recipe(recipe)
        if scope != 'project':
            raise PolicyError('Builtin recipes ship with the product; save project recipes '
                              'instead')
        if not project_id:
            raise PolicyError('A project recipe needs a project id')
        with contextlib.closing(self.store.connect()) as db:
            if not db.execute('SELECT 1 FROM projects WHERE id=?', (project_id,)).fetchone():
                raise PolicyError('Project missing')
            if recipe['source'].startswith('from_job:'):
                job_id = recipe['source'].split(':', 1)[1]
                if not db.execute('SELECT 1 FROM jobs WHERE id=?', (job_id,)).fetchone():
                    raise PolicyError('The job referenced by from_job does not exist')
        if not confirm:
            raise PolicyError('Saving a recipe requires explicit user confirmation')
        stamp = recipe_digest(recipe)
        with self.store.transaction() as db:
            row = db.execute('SELECT digest FROM recipes WHERE recipe_id=? AND recipe_version=?'
                             ' AND scope=? AND project_id=?',
                             (recipe['recipe_id'], recipe['recipe_version'], 'project',
                              project_id)).fetchone()
            if row:
                if row['digest'] == stamp:
                    return {'saved': False, 'digest': stamp, 'reason': 'already saved'}
                raise PolicyError('Recipe %s v%s already exists with different content; bump the '
                                  'version' % (recipe['recipe_id'], recipe['recipe_version']))
            db.execute('INSERT INTO recipes VALUES(?,?,?,?,?,?,?,?,?)',
                       (recipe['recipe_id'], recipe['recipe_version'], 'project', project_id,
                        stamp, encode(recipe), recipe['source'], time.time(), time.time()))
            self._event(db, recipe['recipe_id'], 'saved',
                        {'version': recipe['recipe_version'], 'project': project_id,
                         'source': recipe['source']})
        return {'saved': True, 'digest': stamp, 'recipe_id': recipe['recipe_id'],
                'version': recipe['recipe_version']}

    def propose_from_job(self, job_id):
        """Draft a project recipe from a settled job (preview only; saving needs confirmation)."""
        try:
            job = self.store.get(job_id)
        except KeyError:
            raise PolicyError('Job missing')
        contract = job.get('contract') or {}
        specs = contract.get('milestones') or []
        if not 1 <= len(specs) <= MAX_STEPS:
            raise PolicyError('Only jobs with 1 to %d milestones can become recipes' % MAX_STEPS)
        kind = contract.get('kind') if contract.get('kind') in ('coding', 'document', 'research') \
            else 'document'
        # Milestone ids are engine-internal (often short, like 'm1'); recipe step ids must be
        # 3-64 char slugs, so map them and carry the mapping through depends_on.
        slug_for = {}
        used = set()
        for index, spec in enumerate(specs):
            raw = re.sub(r'[^a-z0-9-]+', '-', str(spec.get('id') or '').lower()).strip('-')
            if len(raw) < 3:
                raw = ('step-' + raw).strip('-')
            if not raw:
                raw = 'step-%d' % (index + 1)
            slug = raw
            if slug in used:
                suffix = 2
                base = slug[:60]
                while ('%s-%d' % (base, suffix)) in used:
                    suffix += 1
                slug = '%s-%d' % (base, suffix)
            used.add(slug)
            slug_for[spec['id']] = slug
        steps = []
        for spec in specs:
            checks = [dict(check) for check in spec.get('checks', [])
                      if check.get('kind') in CHECK_KINDS]
            if not checks:
                checks = [{'kind': 'min_chars', 'value': 40}]
            steps.append({'id': slug_for[spec['id']], 'title': str(spec['id'])[:80],
                          'action': 'work',
                          'objective': str(spec.get('objective', spec['id']))[:600],
                          'depends_on': [slug_for.get(dep, dep) for dep in spec.get('depends_on', [])],
                          'checks': checks,
                          'retries': {'max_attempts': 2, 'on_fail': 'escalate'}})
        name = ('Saved run: ' + str(contract.get('request', 'work'))[:60]).strip()[:80]
        recipe = {
            'schema_version': 1,
            'recipe_id': 'job-' + job_id.replace('-', '')[:12],
            'recipe_version': '1.0.0',
            'name': name or 'Saved run',
            'description': ('Draft rebuilt from job %s — review before saving.' % job_id)[:500],
            'source': 'from_job:' + job_id,
            'kind': kind,
            'inputs': [],
            'steps': steps,
            'permissions': ['project:read']
                           + (['project:write', 'tests:run'] if kind == 'coding' else [])
                           + (['web:search'] if kind == 'research' else []),
            'verification': ['manual_review'],
            'terminal_states': ['VERIFIED', 'FAILED', 'UNCERTAIN'],
            'budget': min(100, max(1, len(steps) * 4)),
            'retry_policy': {'max_attempts_per_milestone': 4, 'provider_switch_after': 2},
        }
        validate_recipe(recipe)
        return {'recipe': recipe,
                'preview': {'steps': [step['title'] for step in steps], 'kind': kind,
                            'milestones': len(steps)}}

def _render(template, values):
    def replace(match):
        name = match.group(1)
        value = values.get(name)
        if value is None or value == '':
            return 'unspecified'
        if isinstance(value, bool):
            return 'yes' if value else 'no'
        return str(value)[:500]
    return re.sub(PLACEHOLDER_RE, replace, template)


def _request_text(recipe, values):
    line = 'Run recipe %s v%s (%s).' % (recipe['name'], recipe['recipe_version'],
                                        recipe['recipe_id'])
    parts = []
    for item in recipe['inputs']:
        value = values.get(item['name'])
        if value is None:
            continue
        if isinstance(value, bool):
            value = 'yes' if value else 'no'
        parts.append('%s: %s' % (item['name'], str(value)[:300]))
    return line + ('\nInputs — ' + '; '.join(parts) if parts else '')

def compile_recipe(recipe, inputs=None, project_id='default', *, root=None, tests=None,
                   source_digest=None):
    """Compile a validated recipe into an existing CompletionContract.

    continue-work returns the continuation invocation instead — it creates no new job.
    """
    validate_recipe(recipe)
    values = dict(inputs or {})
    declared = {item['name']: item for item in recipe['inputs']}
    unknown = set(values) - set(declared)
    if unknown:
        raise PolicyError('Unknown recipe input(s): ' + ', '.join(sorted(unknown)))
    for item in recipe['inputs']:
        if item['name'] not in values:
            if 'default' in item:
                values[item['name']] = item['default']
            elif item['required']:
                hint = ' — ' + item['description'] if item.get('description') else ''
                raise PolicyError('Recipe %s needs the "%s" input%s'
                                  % (recipe['recipe_id'], item['name'], hint))
        else:
            value = values[item['name']]
            if item['type'] == 'choice' and value not in item.get('choices', []):
                raise PolicyError('Input "%s" must be one of: %s'
                                  % (item['name'], ', '.join(item.get('choices', []))))
            if item['type'] == 'bool' and not isinstance(value, bool):
                raise PolicyError('Input "%s" must be true or false' % item['name'])
            if item['type'] == 'text' and isinstance(value, str) \
                    and 'max_chars' in item and len(value) > item['max_chars']:
                raise PolicyError('Input "%s" is longer than %d characters'
                                  % (item['name'], item['max_chars']))
    if recipe['recipe_id'] == CONTINUE_RECIPE_ID:
        return {'continuation': True,
                'recipe': {'id': recipe['recipe_id'], 'version': recipe['recipe_version'],
                           'digest': recipe_digest(recipe)},
                'stages': [step['id'] for step in recipe['steps']],
                'request': _request_text(recipe, values)}
    milestones = []
    for step in recipe['steps']:
        milestones.append({
            'id': step['id'],
            'objective': _render(step['objective'], values),
            'filename': step['id'] + '.md',
            'depends_on': list(step.get('depends_on', [])),
            'checks': [dict(check) for check in step['checks']],
            'action': step['action'],
            'title': step['title'],
            'retries': dict(step['retries']),
        })
    contract = {'request': _request_text(recipe, values), 'kind': recipe['kind'],
                'budget': recipe['budget'], 'project_id': project_id,
                'recipe': {'id': recipe['recipe_id'], 'version': recipe['recipe_version'],
                           'digest': recipe_digest(recipe)},
                'non_goals': ['unrequested source checkout changes',
                              'unrequested external publication'],
                'milestones': milestones}
    kinds_used = {recipe['kind']} | {step.get('kind_override') for step in recipe['steps']
                                     if step.get('kind_override')}
    if 'coding' in kinds_used:
        if 'project:write' not in recipe['permissions']:
            raise PolicyError('Undeclared permission: coding work edits files but does not '
                              'declare project:write')
        if 'tests:run' not in recipe['permissions']:
            raise PolicyError('Undeclared permission: this recipe runs tests but does not '
                              'declare tests:run')
        if root is None or not tests:
            raise PolicyError('Coding recipes need the project root and its test command')
        contract.update({'root': str(root), 'test_command': list(tests), 'compiler': 'recipe',
                         'runtime': 'native-host'})
    if source_digest:
        contract['source_digest'] = source_digest
    return validate_contract(contract)
