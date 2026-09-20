"""V1.4 Gate 3: team model — roles, versions, overrides, assignments, activity (TEAM-*)."""
import contextlib
import json
import tempfile
import unittest

from kel.core import PolicyError, Store, uid
from kel.context import Context
from kel.solution import SolutionBriefs
from kel.team import (ASSIGNMENT_STATES, DEPARTMENTS, EVENT_KINDS, SEED_ROLES, Team, derive_state)


def contract():
    return {'request': 'Do the work',
            'milestones': [{'id': 'm1', 'objective': 'Draft the thing', 'filename': 'out.md',
                            'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 40}]},
                           {'id': 'm2', 'objective': 'Second step', 'filename': 'two.md',
                            'depends_on': ['m1'], 'checks': [{'kind': 'min_chars', 'value': 40}]}]}


def role_fields(**overrides):
    fields = {'goal': 'Produce the artifact.', 'outputs': 'out.md',
              'quality_bar': 'Checks pass.', 'tool_policy': {'allow': ['read', 'write'],
                                                             'deny': ['shell']},
              'budget': 8}
    fields.update(overrides)
    return fields


class TeamCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.context = Context(self.store)
        self.team = Team(self.store)
        self.conversation = self.context.conversation('default', title='Team tests')

    def make_job(self):
        return self.store.create(contract(), conversation=self.conversation)


class RosterSelfSeedingTests(TeamCase):
    def test_a_shipped_role_is_seeded_on_first_use(self):
        # Kel manages its own roster: resolving a role that ships with the product seeds the
        # defaults first, so a person never has to manage rosters.
        resolved = self.team.resolve_role('independent-reviewer')
        self.assertEqual(resolved['template_id'], 'independent-reviewer')
        self.assertGreaterEqual(resolved['role_version'], 1)

    def test_unknown_roles_still_fail_closed(self):
        with self.assertRaises(PolicyError):
            self.team.resolve_role('not-a-real-role')


class RoleTests(TeamCase):
    def test_define_role_and_version(self):
        self.team.define_role('impl', 'Implementation Engineer', 'Engineering', role_fields())
        version, fields = self.team.current_version('impl')
        self.assertEqual(version, 1)
        self.assertEqual(fields['budget'], 8)

    def test_locked_section_cannot_be_edited(self):
        fields = role_fields()
        fields['locked'] = {'guardrails': 'off'}
        with self.assertRaises(PolicyError):
            self.team.define_role('impl', 'Implementation Engineer', 'Engineering', fields)

    def test_unknown_and_missing_fields_refused(self):
        with self.assertRaises(PolicyError):
            self.team.define_role('impl', 'Implementation Engineer', 'Engineering',
                                  role_fields(mystery='x'))
        with self.assertRaises(PolicyError):
            self.team.define_role('impl', 'Implementation Engineer', 'Engineering', {'goal': 'x'})
        with self.assertRaises(PolicyError):
            self.team.define_role('impl', 'Implementation Engineer', 'Nope', role_fields())
        with self.assertRaises(PolicyError):
            self.team.define_role('impl', 'Implementation Engineer', 'Engineering',
                                  role_fields(tool_policy={'allow': ['telepathy']}))
        with self.assertRaises(PolicyError):
            self.team.define_role('impl', 'Implementation Engineer', 'Engineering',
                                  role_fields(budget=0))

    def test_edit_is_append_only_and_diffable(self):
        self.team.define_role('impl', 'Implementation Engineer', 'Engineering', role_fields())
        self.team.edit_role('impl', {'budget': 16})
        version, fields = self.team.current_version('impl')
        self.assertEqual((version, fields['budget']), (2, 16))
        diff = self.team.role_diff('impl', 1, 2)
        self.assertEqual(diff['budget'], {'from': 8, 'to': 16})
        with contextlib.closing(self.store.connect()) as db:
            versions = [r['version'] for r in db.execute(
                'SELECT version FROM role_versions WHERE template_id=? ORDER BY version', ('impl',))]
        self.assertEqual(versions, [1, 2])

    def test_rollback_creates_new_version(self):
        self.team.define_role('impl', 'Implementation Engineer', 'Engineering', role_fields())
        self.team.edit_role('impl', {'budget': 16})
        self.team.rollback_role('impl', 1)
        version, fields = self.team.current_version('impl')
        self.assertEqual((version, fields['budget']), (3, 8))

    def test_override_precedence(self):
        self.team.define_role('impl', 'Implementation Engineer', 'Engineering', role_fields())
        self.team.set_override('impl', 'project', {'budget': 20}, project_id='p1')
        self.team.set_override('impl', 'project', {'quality_bar': 'Ours.'}, project_id='p2')
        self.team.set_override('impl', 'task', {'budget': 30}, project_id='p1', task_id='t1')
        default = self.team.resolve_role('impl')
        self.assertEqual(default['fields']['budget'], 8)
        project = self.team.resolve_role('impl', project_id='p1')
        self.assertEqual(project['fields']['budget'], 20)
        self.assertTrue(any(s.startswith('project:p1') for s in project['sources']))
        other = self.team.resolve_role('impl', project_id='p2')
        self.assertEqual(other['fields']['quality_bar'], 'Ours.')
        self.assertEqual(other['fields']['budget'], 8)
        task = self.team.resolve_role('impl', project_id='p1', task_id='t1')
        self.assertEqual(task['fields']['budget'], 30)
        self.assertTrue(any(s.startswith('task:t1') for s in task['sources']))

    def test_override_scope_validation(self):
        self.team.define_role('impl', 'Implementation Engineer', 'Engineering', role_fields())
        with self.assertRaises(PolicyError):
            self.team.set_override('impl', 'global', {'budget': 9})
        with self.assertRaises(PolicyError):
            self.team.set_override('impl', 'project', {'budget': 9})
        with self.assertRaises(PolicyError):
            self.team.set_override('impl', 'task', {'budget': 9}, project_id='p1')

    def test_locked_block_is_read_only(self):
        self.team.define_role('impl', 'Implementation Engineer', 'Engineering', role_fields())
        resolved = self.team.resolve_role('impl')
        self.assertTrue(resolved['locked_block'])
        self.assertTrue(all(entry['test'].startswith('AUTO-') for entry in resolved['locked_block']))

    def test_tool_policy_fails_closed(self):
        self.team.define_role('impl', 'Implementation Engineer', 'Engineering', role_fields())
        self.assertTrue(self.team.tool_allowed('impl', 'read'))
        self.assertFalse(self.team.tool_allowed('impl', 'shell'))
        self.assertFalse(self.team.tool_allowed('impl', 'browser'))
        with self.assertRaises(PolicyError):
            self.team.tool_allowed('impl', 'telepathy')


class AssignmentTests(TeamCase):
    def setUp(self):
        super().setUp()
        self.team.define_role('impl', 'Implementation Engineer', 'Engineering', role_fields())

    def test_assignment_snapshot_is_frozen(self):
        job = self.make_job()
        created = self.team.create_assignment(job, 'm1', 'impl', project_id='p1')
        before = created['snapshot']['instructions_digest']
        self.team.edit_role('impl', {'quality_bar': 'Different now.'})
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT snapshot FROM team_assignments WHERE assignment_id=?',
                             (created['assignment_id'],)).fetchone()
        self.assertEqual(json.loads(row['snapshot'])['instructions_digest'], before)
        self.assertEqual(json.loads(row['snapshot'])['role_version'], 1)

    def test_no_recursive_delegation(self):
        job = self.make_job()
        with self.assertRaises(PolicyError):
            self.team.create_assignment(job, 'm1', 'impl', actor='specialist')

    def test_assignment_needs_real_milestone(self):
        job = self.make_job()
        with self.assertRaises(PolicyError):
            self.team.create_assignment(job, 'nope', 'impl')
        with self.assertRaises(KeyError):
            self.team.create_assignment(uid(), 'm1', 'impl')

    def test_activity_contract(self):
        job = self.make_job()
        created = self.team.create_assignment(job, 'm1', 'impl')
        assignment = created['assignment_id']
        self.team.attach_run(assignment, 'run-1', provider='fixture', model='m')
        self.team.record_activity(assignment, 'step.started', {'step': 1})
        self.team.add_artifact(assignment, 'digest-1', 'out.md', 'artifact')
        self.team.set_state(assignment, 'DONE')
        events = self.team.activity(assignment)
        kinds = [event['kind'] for event in events]
        self.assertEqual(kinds[0], 'assignment.created')
        for kind in ('assignment.started', 'step.started', 'artifact.produced',
                     'assignment.finished'):
            self.assertIn(kind, kinds)
        self.assertTrue(all(kind in EVENT_KINDS for kind in kinds))
        with self.assertRaises(PolicyError):
            self.team.record_activity(assignment, 'chain.of.thought')
        with self.assertRaises(PolicyError):
            self.team.record_activity(assignment, 'decision.made', {'chain_of_thought': 'secret'})
        with self.assertRaises(PolicyError):
            self.team.add_artifact(assignment, 'digest-2', 'C:/escape.md', 'artifact')
        with self.assertRaises(PolicyError):
            self.team.set_state(assignment, 'CONFUSED')

    def test_office_derives_state_and_hides_orphans(self):
        job = self.make_job()
        self.team.create_assignment(job, 'm1', 'impl')
        derived = derive_state(self.store.get(job))
        self.assertEqual(derived, 'QUEUED')
        with self.store.transaction() as db:
            db.execute("UPDATE jobs SET data=? WHERE id=?",
                       (json.dumps(dict(self.store.get(job), state='PAUSED')), job))
        row = self.team.assignments()[0]
        self.assertEqual(row['derived_state'], 'WAITING')
        with self.store.transaction() as db:
            db.execute('DELETE FROM jobs WHERE id=?', (job,))
        self.assertEqual(self.team.assignments(), [])

    def test_seed_defaults_idempotent(self):
        created = self.team.seed_defaults()
        self.assertEqual(len(created), len(SEED_ROLES))
        self.assertEqual(self.team.seed_defaults(), [])
        roster = self.team.roster()
        ids = {row['template_id'] for row in roster}
        self.assertTrue({seed[0] for seed in SEED_ROLES} <= ids)
        self.assertTrue(all(row['department'] in DEPARTMENTS for row in roster))
        self.assertTrue(all(ASSIGNMENT_STATES) )  # enum is stable

    def test_staffing_reasons_recorded_in_brief(self):
        briefs = SolutionBriefs(self.store)
        brief = briefs.open_brief('p1', 'Ship the feature')
        with self.assertRaises(PolicyError):
            self.team.staffing(brief, [{'milestone': 'm1', 'role': 'impl'}])
        result = self.team.staffing(brief, [{'milestone': 'm1', 'role': 'impl',
                                             'reasons': ['capability: code change',
                                                         'budget: 8 units']}])
        self.assertEqual(result['data']['staffing'][0]['role'], 'impl')


class MigrationTests(TeamCase):
    def test_migrations_recorded_and_idempotent(self):
        Team(self.store)
        SolutionBriefs(self.store)
        with contextlib.closing(self.store.connect()) as db:
            versions = [r['version'] for r in db.execute(
                'SELECT version FROM schema_migrations ORDER BY version')]
        self.assertIn(5, versions)
        self.assertIn(6, versions)
        Team(self.store)
        SolutionBriefs(self.store)


if __name__ == '__main__':
    unittest.main()
