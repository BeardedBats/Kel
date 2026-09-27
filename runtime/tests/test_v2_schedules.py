"""D-57: scheduled tasks are scheduled Recipes in the engine.

A schedule is a trigger: each firing is an ordinary submission → D-53 hand-off → ordinary job, and run
history is folded from events + submissions + jobs. No worker ever runs here (no adapters, supervision
stopped): jobs stay where the test puts them, and time is passed to `Scheduler.tick(now=...)`.
"""
import contextlib
from datetime import datetime, timezone
import json
import os
import tempfile
import time
import unittest

from kel.activity import timeline
from kel.core import PolicyError
from kel.model_prefs import ModelPrefs
from kel.recipes import RecipeLibrary
from kel import schedules as sched
from kel.schedules import (LOCAL_ZONE_LABEL, describe, next_after, normalize_cadence, parse_cron,
                           validate_timezone, zone_label)
from kel.service import Service


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc).timestamp()


def doc_recipe(recipe_id='weekly-note'):
    return {'schema_version': 1, 'recipe_id': recipe_id, 'recipe_version': '1.0.0',
            'name': 'Weekly Note', 'description': 'A short note for the schedule tests.',
            'source': 'project', 'kind': 'document', 'inputs': [],
            'steps': [{'id': 'first', 'title': 'Draft the note', 'action': 'work',
                       'objective': 'Write the note with enough text to pass the check.',
                       'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 40}],
                       'retries': {'max_attempts': 2, 'on_fail': 'retry'}}],
            'permissions': ['project:read'], 'verification': ['min_chars'],
            'terminal_states': ['VERIFIED', 'FAILED', 'UNCERTAIN'], 'budget': 8,
            'retry_policy': {'max_attempts_per_milestone': 4, 'provider_switch_after': 2}}


class CronTests(unittest.TestCase):
    def test_fields_names_lists_ranges_and_steps(self):
        spec = parse_cron('*/15 9-17/4 1,15 JAN-MAR mon-fri')
        self.assertEqual(spec.minutes, [0, 15, 30, 45])
        self.assertEqual(spec.hours, [9, 13, 17])
        self.assertEqual(spec.doms, {1, 15})
        self.assertEqual(spec.months, {1, 2, 3})
        self.assertEqual(spec.dows, {1, 2, 3, 4, 5})
        self.assertEqual(parse_cron('0 0 * * 7').dows, {0})  # 7 is Sunday too
        self.assertEqual(parse_cron('0 0 * * 5-7').dows, {5, 6, 0})
        self.assertEqual(parse_cron('5/20 * * * *').minutes, [5, 25, 45])
        self.assertEqual(parse_cron('@daily').hours, [0])
        for bad in ('', '* * * *', '60 * * * *', '* 24 * * *', '0 0 0 * *', '0 0 * 13 *', '0 0 * * FUN',
                    '5-1 * * * *', '*/0 * * * *', '1,,2 * * * *', '* * * * * *'):
            with self.assertRaises(PolicyError, msg=bad):
                parse_cron(bad)

    def test_vixie_day_of_month_or_day_of_week(self):
        # "the 13th, or any Friday": both restricted → either matches.
        after = utc(2026, 3, 1, 12)
        first = next_after({'kind': 'cron', 'expr': '0 9 13 * FRI'}, 'UTC', after)
        self.assertEqual(first, utc(2026, 3, 6, 9))  # Friday 6 March comes before the 13th
        self.assertEqual(next_after({'kind': 'cron', 'expr': '0 9 13 * FRI'}, 'UTC', first), utc(2026, 3, 13, 9))
        # One side unrestricted (even as */n) → the other decides alone.
        self.assertEqual(next_after({'kind': 'cron', 'expr': '0 9 */1 * FRI'}, 'UTC', after), utc(2026, 3, 6, 9))
        self.assertEqual(next_after({'kind': 'cron', 'expr': '0 9 13 * *'}, 'UTC', after), utc(2026, 3, 13, 9))

    def test_validation_minimum_interval_and_never(self):
        now = utc(2026, 1, 1)
        with self.assertRaisesRegex(PolicyError, 'every 5 minutes'):
            normalize_cadence({'kind': 'interval', 'minutes': 4}, now=now)
        with self.assertRaisesRegex(PolicyError, 'every 5 minutes'):
            normalize_cadence({'kind': 'cron', 'expr': '*/2 * * * *'}, now=now)
        with self.assertRaisesRegex(PolicyError, 'every 5 minutes'):
            normalize_cadence({'kind': 'cron', 'expr': '0,58 9,10 * * *'}, now=now)  # 9:58 then 10:00
        self.assertEqual(normalize_cadence({'kind': 'cron', 'expr': '0,58 9,11 * * *'}, now=now)['expr'],
                         '0,58 9,11 * * *')
        with self.assertRaisesRegex(PolicyError, 'never comes round'):
            normalize_cadence({'kind': 'cron', 'expr': '0 9 31 2 *'}, now=now)
        with self.assertRaisesRegex(PolicyError, 'already passed'):
            normalize_cadence({'kind': 'once', 'at': now - 60}, now=now)
        self.assertEqual(normalize_cadence({'kind': 'once', 'at': '2026-01-02T09:00:00Z'}, now=now)['at'],
                         utc(2026, 1, 2, 9))
        self.assertEqual(normalize_cadence({'kind': 'manual'}), {'kind': 'manual'})
        for bad in (None, {}, {'kind': 'hourly'}, {'kind': 'interval', 'minutes': True},
                    {'kind': 'interval', 'minutes': 7.5}):
            with self.assertRaises(PolicyError):
                normalize_cadence(bad, now=now)

    def test_descriptions_are_plain(self):
        self.assertEqual(describe({'kind': 'cron', 'expr': '0 9 * * 1-5'}), 'Every weekday at 9:00 AM')
        self.assertEqual(describe({'kind': 'cron', 'expr': '30 17 * * *'}), 'Every day at 5:30 PM')
        self.assertEqual(describe({'kind': 'cron', 'expr': '0 8 * * MON,WED,FRI'}),
                         'Every Monday, Wednesday and Friday at 8:00 AM')
        self.assertEqual(describe({'kind': 'cron', 'expr': '0 12 1 * *'}), 'On the 1st of every month at 12:00 PM')
        self.assertEqual(describe({'kind': 'cron', 'expr': '*/30 * * * *'}), 'Every 30 minutes')
        self.assertEqual(describe({'kind': 'cron', 'expr': '0 * * * *'}), 'Every hour, on the hour')
        self.assertEqual(describe({'kind': 'cron', 'expr': '0 */6 * * *'}), 'Every 6 hours')
        self.assertEqual(describe({'kind': 'interval', 'minutes': 90}), 'Every 90 minutes')
        self.assertEqual(describe({'kind': 'interval', 'minutes': 120}), 'Every 2 hours')
        self.assertEqual(describe({'kind': 'manual'}), 'Only when you run it')
        self.assertEqual(describe({'kind': 'once', 'at': utc(2026, 10, 12, 9)}, 'UTC'), 'Once, on Mon 12 Oct at 9:00 AM')
        self.assertEqual(describe({'kind': 'cron', 'expr': '7 3 5 4 *'}), 'On a custom schedule')


class NextAfterTests(unittest.TestCase):
    ny = 'America/New_York'

    def test_dst_gap_runs_at_the_first_valid_minute(self):
        cadence = {'kind': 'cron', 'expr': '30 2 * * *'}
        # 8 March 2026: 2:00 EST jumps to 3:00 EDT, so 2:30 does not exist that day.
        slot = next_after(cadence, self.ny, utc(2026, 3, 7, 17))
        self.assertEqual(slot, utc(2026, 3, 8, 7))  # 3:00 EDT
        self.assertEqual(next_after(cadence, self.ny, slot), utc(2026, 3, 9, 6, 30))  # 2:30 EDT next day

    def test_dst_fold_runs_once(self):
        cadence = {'kind': 'cron', 'expr': '30 1 * * *'}
        # 1 November 2026: 1:00-2:00 happens twice; the task runs at the first 1:30 only.
        slot = next_after(cadence, self.ny, utc(2026, 10, 31, 16))
        self.assertEqual(slot, utc(2026, 11, 1, 5, 30))  # 1:30 EDT
        self.assertEqual(next_after(cadence, self.ny, slot), utc(2026, 11, 2, 6, 30))  # 1:30 EST, next day
        hourly = {'kind': 'cron', 'expr': '0 * * * *'}
        first = next_after(hourly, self.ny, utc(2026, 11, 1, 4, 30))  # 0:30 EDT
        self.assertEqual(first, utc(2026, 11, 1, 5))  # 1:00 EDT
        self.assertEqual(next_after(hourly, self.ny, first), utc(2026, 11, 1, 7))  # 2:00 EST; 1:00 EST once only

    def test_interval_once_manual_and_zone_fallback(self):
        created = utc(2026, 1, 1, 10, 3)
        cadence = {'kind': 'interval', 'minutes': 60}
        self.assertEqual(next_after(cadence, None, created, created), created + 3600)
        self.assertEqual(next_after(cadence, None, created + 5000, created), created + 7200)
        self.assertEqual(next_after(cadence, None, created - 99999, created), created + 3600)
        once = {'kind': 'once', 'at': created + 50}
        self.assertEqual(next_after(once, None, created), created + 50)
        self.assertIsNone(next_after(once, None, created + 50))
        self.assertIsNone(next_after({'kind': 'manual'}, None, created))
        daily = {'kind': 'cron', 'expr': '0 9 * * *'}
        self.assertEqual(next_after(daily, 'Mars/Olympus_Mons', created), next_after(daily, None, created))
        self.assertEqual(zone_label('Mars/Olympus_Mons'), LOCAL_ZONE_LABEL)
        self.assertEqual(zone_label(None), LOCAL_ZONE_LABEL)
        self.assertEqual(zone_label('Europe/London'), 'Europe/London')
        with self.assertRaisesRegex(PolicyError, "doesn't know"):
            validate_timezone('Mars/Olympus_Mons')
        self.assertIsNone(validate_timezone(''))
        # Without a time zone database a named zone cannot be checked: it is kept and runs locally.
        original = sched._zone_database
        sched._zone_database = lambda: False
        try:
            self.assertEqual(validate_timezone('Mars/Olympus_Mons'), 'Mars/Olympus_Mons')
        finally:
            sched._zone_database = original


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        for key in ('ANTHROPIC_API_KEY', 'KEL_INTERNAL_MODEL'):
            os.environ.pop(key, None)
        os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none')
        self.service = Service(self.tmp.name)
        self.service.engine.adapters = {}
        self.service.stop.set()  # no supervision: time moves only through tick(now=...)
        self.scheduler = self.service.schedules
        self.project = self.service.projects.create('Garden')['id']

    def tearDown(self):
        with contextlib.suppress(Exception):
            self.service.shutdown()
        with contextlib.suppress(Exception):
            self.tmp.cleanup()

    def api(self, action, **data):
        return self.service.action('/api/schedules', dict(data, action=action))

    def create(self, **overrides):
        data = {'name': 'Garden note', 'project_id': self.project,
                'target': {'kind': 'instruction', 'text': 'Write a short note about watering the garden'},
                'cadence': {'kind': 'cron', 'expr': '0 9 * * *'}, 'timezone': 'UTC',
                'start_mode': 'new_conversation'}
        data.update(overrides)
        return self.api('create', **data)['schedule']

    def row(self, schedule_id):
        with contextlib.closing(self.service.store.connect()) as db:
            return dict(db.execute('SELECT * FROM schedules WHERE id=?', (schedule_id,)).fetchone())

    def set_due(self, schedule_id, slot):
        with self.service.store.transaction() as db:
            db.execute('UPDATE schedules SET next_due_at=? WHERE id=?', (slot, schedule_id))

    def submissions(self, schedule_id):
        with contextlib.closing(self.service.store.connect()) as db:
            return [dict(r) for r in db.execute('SELECT * FROM submissions WHERE id LIKE ? ORDER BY created',
                                                ('sched-%s-%%' % schedule_id[:8],))]

    def wait_settled(self, sid, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with contextlib.closing(self.service.store.connect()) as db:
                row = db.execute('SELECT state FROM submissions WHERE id=?', (sid,)).fetchone()
            if row and row['state'] != 'PLANNING':
                return row['state']
            time.sleep(.02)
        raise TimeoutError(sid)

    def events(self, schedule_id, kind=None):
        with contextlib.closing(self.service.store.connect()) as db:
            rows = db.execute('SELECT type,payload FROM events WHERE aggregate_id=? ORDER BY seq',
                              ('schedule:' + schedule_id,)).fetchall()
        out = [(r['type'][len('schedule.'):], json.loads(r['payload'])['detail']) for r in rows]
        return [item for item in out if kind is None or item[0] == kind]

    def settle_job(self, job_id, state='CLOSED', verdict='VERIFIED'):
        store = self.service.store
        with store.transaction() as db:
            job = store._get(db, job_id)
            job['state'] = state
            job['verdict'] = verdict
            store._save(db, job, 'test.settled')

    def fire_first(self, schedule):
        slot = next_after(schedule['cadence'], schedule['timezone'], time.time(), self.row(schedule['id'])['created'])
        self.set_due(schedule['id'], slot)
        self.assertEqual(self.scheduler.tick(now=slot + 1), 1)
        sub = self.submissions(schedule['id'])[-1]
        self.wait_settled(sub['id'])
        return slot, self.submissions(schedule['id'])[-1]


class MissedRunTests(Base):
    def test_a_little_late_runs_once(self):
        schedule = self.create()
        slot = self.row(schedule['id'])['next_due_at']
        self.assertEqual(self.scheduler.tick(now=slot + 3600), 1)
        self.assertEqual([k for k, _ in self.events(schedule['id']) if k in ('fired', 'missed')], ['fired'])
        fired = self.events(schedule['id'], 'fired')[0][1]
        self.assertEqual((fired['slot'], fired['late_by']), (slot, 3600))
        self.assertEqual(self.row(schedule['id'])['next_due_at'], slot + 86400)
        self.wait_settled(fired['submission_id'])

    def test_too_late_is_only_recorded_as_missed(self):
        schedule = self.create()
        slot = self.row(schedule['id'])['next_due_at']
        self.assertEqual(self.scheduler.tick(now=slot + 13 * 3600), 0)
        self.assertEqual(self.submissions(schedule['id']), [])
        missed = self.events(schedule['id'], 'missed')
        self.assertEqual(len(missed), 1)
        self.assertEqual(missed[0][1]['count'], 1)
        rows = self.scheduler.history(schedule['id'])
        self.assertEqual((rows[0]['status'], rows[0]['label']), ('missed', 'Missed 1 run while Kel was closed'))

    def test_hourly_after_eight_hours_is_one_run_and_seven_missed(self):
        schedule = self.create(cadence={'kind': 'cron', 'expr': '0 * * * *'})
        slot = self.row(schedule['id'])['next_due_at']
        now = slot + 7 * 3600 + 600
        self.assertEqual(self.scheduler.tick(now=now), 1)
        missed = self.events(schedule['id'], 'missed')
        self.assertEqual(missed[0][1]['count'], 7)
        self.assertEqual((missed[0][1]['first'], missed[0][1]['last']), (slot, slot + 6 * 3600))
        fired = self.events(schedule['id'], 'fired')
        self.assertEqual([f['slot'] for _, f in fired], [slot + 7 * 3600])
        self.assertEqual(self.row(schedule['id'])['next_due_at'], slot + 8 * 3600)
        self.assertEqual({r['status'] for r in self.scheduler.history(schedule['id'])} - {'running'}, {'missed'})
        self.wait_settled(fired[0][1]['submission_id'])

    def test_a_replayed_slot_never_fires_twice(self):
        schedule = self.create()
        slot = self.row(schedule['id'])['next_due_at']
        self.assertEqual(self.scheduler.tick(now=slot + 5), 1)
        self.assertEqual(self.scheduler.tick(now=slot + 6), 0)
        self.set_due(schedule['id'], slot)  # as if the claim were lost and the slot came round again
        self.assertEqual(self.scheduler.tick(now=slot + 7), 0)
        self.assertEqual(len(self.submissions(schedule['id'])), 1)
        self.assertEqual(len(self.events(schedule['id'], 'fired')), 1)
        self.wait_settled(self.submissions(schedule['id'])[0]['id'])

    def test_draining_blocks_firing(self):
        schedule = self.create()
        slot = self.row(schedule['id'])['next_due_at']
        self.service.draining = True
        self.assertEqual(self.scheduler.tick(now=slot + 5), 0)
        self.assertEqual(self.row(schedule['id'])['next_due_at'], slot)
        self.service.draining = False
        self.assertEqual(self.scheduler.tick(now=slot + 5), 1)
        self.wait_settled(self.submissions(schedule['id'])[0]['id'])

    def test_once_fires_at_most_once(self):
        at = time.time() + 3600
        schedule = self.create(cadence={'kind': 'once', 'at': at})
        self.assertEqual(self.scheduler.tick(now=at + 1), 1)
        self.assertIsNone(self.row(schedule['id'])['next_due_at'])
        self.assertEqual(self.scheduler.tick(now=at + 99999), 0)
        self.assertEqual(self.api('get', id=schedule['id'])['schedule']['status'], 'done')
        self.wait_settled(self.submissions(schedule['id'])[0]['id'])


class FiringTests(Base):
    def test_a_run_is_an_ordinary_handoff_job_everywhere(self):
        schedule = self.create()
        slot, sub = self.fire_first(schedule)
        self.assertEqual(sub['state'], 'DISPATCHED')
        cid = sub['conversation_id']
        store = self.service.store
        job = store.get(sub['job_id'])
        self.assertEqual(job['conversation'], cid)
        self.assertEqual(job['contract']['schedule'],
                         {'id': schedule['id'], 'name': 'Garden note', 'slot': slot, 'model': None})
        # A new conversation in the schedule's project, named after the task and its time.
        with contextlib.closing(store.connect()) as db:
            conv = db.execute('SELECT * FROM conversations WHERE id=?', (cid,)).fetchone()
        self.assertEqual(conv['project_id'], self.project)
        self.assertTrue(conv['title'].startswith('Garden note · '))
        state = self.service.state(cid)
        users = [m for m in state['messages'] if m['role'] == 'user']
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['job_id'], job['id'])
        self.assertEqual(users[0]['meta']['kind'], 'scheduled')
        ack = next(s for s in state['submissions'] if s['id'] == sub['id'])
        self.assertEqual(ack['title'], 'Garden note')
        ack_text = next(m['text'] for m in state['messages'] if m['seq'] == ack['ack_seq'])
        self.assertEqual(ack_text, 'Scheduled run of “Garden note” started. '
                                   "I'll post the result here once it has been checked.")
        self.assertIn(job['id'], [j['id'] for j in self.service.state('*')['jobs']])
        self.assertIn(job['id'], [j['job_id'] for j in self.service._work('main', '*')['work']['jobs']])
        self.assertIn(job['id'], [j['job_id'] for j in self.service._work('main', self.project)['work']['jobs']])
        rows = self.service.action('/api/activity', {'project': self.project, 'kind': 'scheduled'})['entries']
        self.assertEqual([r['what'] for r in rows],
                         ['A scheduled run of “Garden note” started.', 'You scheduled “Garden note”.'])
        self.assertTrue(all(r['project_id'] == self.project and r['schedule_id'] == schedule['id'] for r in rows))
        self.assertEqual(timeline(store, project_id='default', kind='scheduled')['entries'], [])
        listed = self.service.conversations()['conversations']
        self.assertEqual(next(c for c in listed if c['id'] == cid)['schedule_id'], schedule['id'])
        view = self.api('get', id=schedule['id'])
        self.assertEqual(view['conversations'], {'created': 1, 'open': 1})
        self.assertTrue(view['schedule']['running'])
        self.assertEqual(view['schedule']['last_run']['job_id'], job['id'])

    def test_the_http_payload_cannot_claim_a_schedule(self):
        cid = self.service.context.conversation(self.project)
        sid = self.service.action('/api/send', {'conversation': cid, 'text': 'Write a note about roses',
                                                'schedule': {'id': 'x', 'name': 'Fake'}, 'origin': {'id': 'x'}})['id']
        self.wait_settled(sid)
        with contextlib.closing(self.service.store.connect()) as db:
            packet = json.loads(db.execute('SELECT packet FROM submission_packets WHERE id=?', (sid,)).fetchone()[0])
        self.assertNotIn('schedule', packet)

    def test_skip_if_still_running(self):
        schedule = self.create(cadence={'kind': 'cron', 'expr': '0 * * * *'})
        slot, sub = self.fire_first(schedule)
        self.assertEqual(self.scheduler.tick(now=slot + 3601), 0)
        self.assertEqual(len(self.submissions(schedule['id'])), 1)
        rows = self.scheduler.history(schedule['id'])
        self.assertEqual((rows[0]['status'], rows[0]['label']),
                         ('skipped', 'Skipped — the last run was still going'))
        # Waiting for the person still counts as running.
        store = self.service.store
        with store.transaction() as db:
            job = store._get(db, sub['job_id'])
            job['state'] = 'AWAITING_USER'
            store._save(db, job, 'test.waiting')
        self.assertEqual(self.scheduler.tick(now=slot + 7201), 0)
        self.settle_job(sub['job_id'])
        self.assertEqual(self.scheduler.tick(now=slot + 10801), 1)
        self.wait_settled(self.submissions(schedule['id'])[-1]['id'])

    def test_otherwise_one_coalesced_run_waits(self):
        schedule = self.create(cadence={'kind': 'cron', 'expr': '0 * * * *'}, skip_if_running=False)
        slot, sub = self.fire_first(schedule)
        self.assertEqual(self.scheduler.tick(now=slot + 3601), 0)
        self.assertEqual(self.row(schedule['id'])['queued_slot'], slot + 3600)
        self.assertEqual(self.scheduler.tick(now=slot + 7201), 0)
        self.assertEqual(self.row(schedule['id'])['queued_slot'], slot + 7200)
        statuses = [r['status'] for r in self.scheduler.history(schedule['id'])]
        self.assertEqual(statuses[:2], ['queued', 'coalesced'])
        self.settle_job(sub['job_id'])
        self.assertEqual(self.scheduler.tick(now=slot + 7300), 1)
        self.assertIsNone(self.row(schedule['id'])['queued_slot'])
        fired = self.events(schedule['id'], 'fired')
        self.assertEqual([f['slot'] for _, f in fired], [slot, slot + 7200])
        self.wait_settled(fired[-1][1]['submission_id'])
        statuses = [r['status'] for r in self.scheduler.history(schedule['id'])]
        self.assertNotIn('queued', statuses)
        self.assertEqual(statuses.count('coalesced'), 1)

    def test_existing_conversation_and_model_preference(self):
        cid = self.service.context.conversation(self.project, title='Garden chat')
        prefs = ModelPrefs(self.service.store)
        prefs.set_conversation(cid, 'codex', None)
        schedule = self.create(start_mode='existing', conversation_id=cid,
                               model={'provider': 'claude-code', 'model': 'claude-native'})
        self.assertEqual(schedule['model_label'], 'Claude (built-in)')
        self.assertEqual(schedule['conversation_title'], 'Garden chat')
        _, sub = self.fire_first(schedule)
        self.assertEqual(sub['conversation_id'], cid)
        self.assertEqual(ModelPrefs.resolve_for_job(self.service.store, sub['job_id']),
                         {'provider': 'claude-code', 'model': 'claude-native'})
        self.assertEqual(prefs.conversation(cid), {'provider': 'codex', 'model': None})
        # An ordinary message in the same chat still follows the chat's own choice.
        other = self.service.submit({'conversation': cid, 'text': 'Write a note about compost'})
        self.wait_settled(other)
        with contextlib.closing(self.service.store.connect()) as db:
            job_id = db.execute('SELECT job_id FROM submissions WHERE id=?', (other,)).fetchone()[0]
        self.assertEqual(ModelPrefs.resolve_for_job(self.service.store, job_id), {'provider': 'codex', 'model': None})
        with self.assertRaises(PolicyError):
            self.create(model={'provider': 'nobody'})


class RecipeScheduleTests(Base):
    def setUp(self):
        super().setUp()
        RecipeLibrary(self.service.store).save(doc_recipe(), project_id=self.project, confirm=True)

    def test_a_recipe_schedule_runs_the_recipe(self):
        schedule = self.create(target={'kind': 'recipe', 'recipe_id': 'weekly-note', 'inputs': {}})
        self.assertEqual(schedule['target']['recipe_name'], 'Weekly Note')
        _, sub = self.fire_first(schedule)
        self.assertEqual(sub['state'], 'DISPATCHED')
        job = self.service.store.get(sub['job_id'])
        self.assertEqual(job['contract']['recipe']['id'], 'weekly-note')
        self.assertEqual(job['contract']['schedule']['id'], schedule['id'])
        self.assertEqual(job['contract']['handoff']['title'], 'Garden note')
        library = RecipeLibrary(self.service.store)
        self.assertEqual([h['job_id'] for h in library.history(self.project, 'weekly-note')], [job['id']])
        mark = next(e for e in library.entries(project_id=self.project) if e['recipe_id'] == 'weekly-note')
        self.assertEqual(mark['runs'], 1)

    def test_continue_work_starts_no_job(self):
        schedule = self.create(target={'kind': 'recipe', 'recipe_id': 'continue-work', 'inputs': {}})
        _, sub = self.fire_first(schedule)
        self.assertEqual(sub['state'], 'SETTLED')
        self.assertIsNone(sub['job_id'])
        messages = self.service.state(sub['conversation_id'])['messages']
        self.assertIn('There is no unfinished work in this project to continue. New requests start fresh work.',
                      [m['text'] for m in messages])
        self.assertEqual(self.scheduler.history(schedule['id'])[0]['status'], 'settled')

    def test_a_deleted_recipe_pauses_with_a_problem(self):
        schedule = self.create(target={'kind': 'recipe', 'recipe_id': 'weekly-note', 'inputs': {}})
        with self.service.store.transaction() as db:
            db.execute("DELETE FROM recipes WHERE recipe_id='weekly-note'")
        slot = self.row(schedule['id'])['next_due_at']
        self.assertEqual(self.scheduler.tick(now=slot + 5), 0)
        view = self.api('get', id=schedule['id'])['schedule']
        self.assertEqual(view['status'], 'needs_attention')
        self.assertFalse(view['enabled'])
        self.assertEqual(view['problem'], 'The recipe this task runs is no longer available in this project.')
        self.assertEqual(self.api('list')['needs_attention'], 1)
        rows = self.scheduler.history(schedule['id'])
        self.assertEqual((rows[0]['status'], rows[0]['label'], rows[0]['cause']),
                         ('not_started', "Didn't start", view['problem']))
        with self.assertRaisesRegex(PolicyError, 'no longer available'):
            self.api('resume', id=schedule['id'])
        paused = [d for k, d in self.events(schedule['id']) if k == 'paused']
        self.assertEqual(paused[-1]['problem'], view['problem'])
        activity = self.service.action('/api/activity', {'project': self.project, 'kind': 'scheduled'})['entries']
        self.assertTrue(any(r['what'].startswith('Kel paused') for r in activity))
        self.assertTrue(any(r['failed'] for r in activity))


class GuardTests(Base):
    def test_code_changes_need_the_project_folder(self):
        with self.assertRaisesRegex(PolicyError, 'has no folder yet'):
            self.create(target={'kind': 'instruction', 'text': 'Fix the failing tests in the garden app'})
        with self.assertRaisesRegex(PolicyError, 'has no folder yet'):
            self.create(target={'kind': 'recipe', 'recipe_id': 'fix-bug', 'inputs': {'bug': 'the crash'}})

    def test_a_scheduled_run_never_creates_a_project(self):
        schedule = self.create(target={'kind': 'instruction', 'text': 'Create an app that tracks my watering'})
        before = {p['id'] for p in self.service.projects.list(include_archived=True)}
        _, sub = self.fire_first(schedule)
        self.assertEqual({p['id'] for p in self.service.projects.list(include_archived=True)}, before)
        job = self.service.store.get(sub['job_id'])
        self.assertNotEqual(job['contract'].get('kind'), 'coding')

    def test_a_folder_removed_after_scheduling_is_refused_at_run_time(self):
        schedule = self.create(target={'kind': 'instruction', 'text': 'Write a garden note'})
        with self.service.store.transaction() as db:
            db.execute('UPDATE schedules SET target=? WHERE id=?',
                       (json.dumps({'kind': 'instruction', 'text': 'Fix the watering bug'}), schedule['id']))
        _, sub = self.fire_first(schedule)
        self.assertEqual(sub['state'], 'FAILED')
        self.assertIn('has no folder yet', sub['error'])
        rows = self.scheduler.history(schedule['id'])
        self.assertEqual(rows[0]['status'], 'not_started')

    def test_deleted_project_and_conversation_pause_with_a_problem(self):
        cid = self.service.context.conversation(self.project, title='Garden chat')
        schedule = self.create(start_mode='existing', conversation_id=cid)
        with self.service.store.transaction() as db:
            db.execute('DELETE FROM conversations WHERE id=?', (cid,))
        slot = self.row(schedule['id'])['next_due_at']
        self.assertEqual(self.scheduler.tick(now=slot + 5), 0)
        self.assertEqual(self.row(schedule['id'])['problem'], 'The conversation this task posts to no longer exists.')
        self.assertEqual(self.row(schedule['id'])['enabled'], 0)
        # Fixing it (a new conversation) clears the problem and turns it back on.
        fixed = self.api('update', id=schedule['id'], start_mode='new_conversation')['schedule']
        self.assertEqual((fixed['problem'], fixed['enabled'], fixed['status']), (None, True, 'active'))
        other = self.create(name='Other note')
        self.service.projects.archive(self.project)
        slot = self.row(other['id'])['next_due_at']
        self.scheduler.tick(now=slot + 5)
        self.assertIn('archived', self.row(other['id'])['problem'])
        with self.assertRaisesRegex(PolicyError, 'archived'):
            self.create(name='Third')
        with self.assertRaisesRegex(PolicyError, 'no longer exists'):
            self.create(project_id='no-such-project')

    def test_an_existing_conversation_must_be_in_the_same_project(self):
        elsewhere = self.service.context.conversation('default')
        with self.assertRaisesRegex(PolicyError, 'different project'):
            self.create(start_mode='existing', conversation_id=elsewhere)
        with self.assertRaisesRegex(PolicyError, 'no longer exists'):
            self.create(start_mode='existing', conversation_id='missing')


class HistoryAndApiTests(Base):
    def test_history_labels(self):
        schedule = self.create(cadence={'kind': 'cron', 'expr': '0 * * * *'})
        labels = []
        for index, (state, verdict) in enumerate((('CLOSED', 'VERIFIED'), ('CLOSED', 'FAILED'),
                                                  ('CANCELLED', 'UNCERTAIN'))):
            row = self.row(schedule['id'])
            self.assertEqual(self.scheduler.tick(now=row['next_due_at'] + 1), 1)
            sub = self.submissions(schedule['id'])[-1]
            self.wait_settled(sub['id'])
            self.settle_job(self.submissions(schedule['id'])[-1]['job_id'], state, verdict)
        rows = self.scheduler.history(schedule['id'])
        labels = [(r['status'], r['label']) for r in rows[:3]]
        self.assertEqual(sorted(labels), sorted([('success', 'Success'),
                                                 ('needs_look', 'Finished — needs a look'),
                                                 ('stopped', 'Stopped')]))
        self.assertTrue(all(r['job_id'] and r['conversation'] and r['submission_id'] for r in rows[:3]))
        for key in ('at', 'slot', 'late_by', 'conversation', 'job_id', 'submission_id', 'status', 'label', 'cause'):
            self.assertIn(key, rows[0])

    def test_actions(self):
        schedule = self.create()
        self.assertEqual(schedule['description'], 'Every day at 9:00 AM')
        self.assertEqual(schedule['timezone_label'], 'UTC')
        self.assertEqual(schedule['model_label'], 'Automatic')
        self.assertEqual(schedule['project_name'], 'Garden')
        listed = self.api('list')
        self.assertEqual([s['id'] for s in listed['schedules']], [schedule['id']])
        self.assertEqual(self.api('list', project='default')['schedules'], [])
        updated = self.api('update', id=schedule['id'], name='Morning note',
                           cadence={'kind': 'cron', 'expr': '30 7 * * 1-5'})['schedule']
        self.assertEqual((updated['name'], updated['description']), ('Morning note', 'Every weekday at 7:30 AM'))
        self.assertEqual(self.api('pause', id=schedule['id'])['schedule']['status'], 'paused')
        self.assertIsNone(self.api('get', id=schedule['id'])['schedule']['next_due_at'])
        resumed = self.api('resume', id=schedule['id'])['schedule']
        self.assertEqual(resumed['status'], 'active')
        self.assertGreater(resumed['next_due_at'], time.time())
        out = self.api('run_now', id=schedule['id'])
        self.assertTrue(out['submission'].startswith('sched-'))
        self.wait_settled(out['submission'])
        rows = self.api('history', id=schedule['id'])['rows']
        self.assertEqual(rows[0]['submission_id'], out['submission'])
        preview = self.api('preview', cadence={'kind': 'cron', 'expr': '0 9 * * 1-5'}, timezone='UTC')
        self.assertEqual((preview['valid'], preview['description'], len(preview['next'])),
                         (True, 'Every weekday at 9:00 AM', 3))
        self.assertTrue(all(datetime.fromtimestamp(t, timezone.utc).weekday() < 5 for t in preview['next']))
        bad = self.api('preview', cadence={'kind': 'interval', 'minutes': 1})
        self.assertEqual((bad['valid'], bad['next']), (False, []))
        self.assertIn('every 5 minutes', bad['message'])
        with self.assertRaises(PolicyError):
            self.api('create', name='', project_id=self.project,
                     target={'kind': 'instruction', 'text': 'x'}, cadence={'kind': 'manual'})
        with self.assertRaises(PolicyError):
            self.api('nonsense')
        manual = self.create(name='By hand', cadence={'kind': 'manual'})
        self.assertEqual((manual['status'], manual['next_due_at'], manual['description']),
                         ('manual', None, 'Only when you run it'))

    def test_delete_hides_finished_run_chats_and_keeps_open_ones(self):
        schedule = self.create(cadence={'kind': 'cron', 'expr': '0 * * * *'}, skip_if_running=False)
        slot, first = self.fire_first(schedule)
        self.settle_job(first['job_id'])
        self.assertEqual(self.scheduler.tick(now=slot + 3601), 1)
        second = self.submissions(schedule['id'])[-1]
        self.wait_settled(second['id'])
        self.assertEqual(self.api('get', id=schedule['id'])['conversations'], {'created': 2, 'open': 1})
        out = self.api('delete', id=schedule['id'], conversations='delete')
        self.assertEqual(out['hidden'], [first['conversation_id']])
        self.assertEqual(out['kept_open'], [second['conversation_id']])
        visible = [c['id'] for c in self.service.state('main')['conversations']]
        self.assertNotIn(first['conversation_id'], visible)
        self.assertIn(second['conversation_id'], visible)
        self.assertNotIn(first['conversation_id'], [c['id'] for c in self.service.conversations()['conversations']])
        self.assertEqual(self.api('list')['schedules'], [])
        with self.assertRaisesRegex(PolicyError, 'no longer exists'):
            self.api('get', id=schedule['id'])
        self.assertEqual(self.scheduler.tick(now=slot + 99999), 0)
        with self.assertRaises(PolicyError):
            self.api('delete', id=schedule['id'])


class ImportTests(Base):
    def items(self):
        cid = self.service.context.conversation(self.project, title='Old cron chat')
        return [
            {'origin': 'cron:good', 'name': 'Daily digest', 'project_id': self.project,
             'target': {'kind': 'instruction', 'text': 'Write a digest of the garden notes'},
             'cadence': {'kind': 'cron', 'expr': '0 8 * * *'}, 'timezone': 'Europe/London',
             'start_mode': 'existing', 'conversation_id': cid, 'skip_if_running': False, 'enabled': True,
             'runs': [{'conversation_id': cid, 'at': time.time() - 86400 * (n + 1)} for n in range(25)]},
            {'origin': 'cron:too-often', 'name': 'Every minute', 'project_id': self.project,
             'target': {'kind': 'instruction', 'text': 'Write a ping'},
             'cadence': {'kind': 'interval', 'minutes': 1}, 'start_mode': 'new_conversation', 'enabled': True},
            {'origin': 'cron:past', 'name': 'Old one-off', 'project_id': self.project,
             'target': {'kind': 'instruction', 'text': 'Write a reminder'},
             'cadence': {'kind': 'once', 'at': time.time() - 3600}, 'start_mode': 'new_conversation'},
            {'origin': 'cron:flagged', 'name': 'Model gone', 'project_id': self.project,
             'target': {'kind': 'instruction', 'text': 'Write a summary'}, 'cadence': {'kind': 'manual'},
             'start_mode': 'new_conversation', 'problem': 'The model this task used is not available.'},
            {'origin': 'cron:empty', 'name': 'Nothing', 'target': {}, 'cadence': {'kind': 'manual'}},
            {'name': 'No origin'},
        ]

    def test_import_is_idempotent_and_never_replays(self):
        self.assertEqual(self.api('migration_status'), {'done': False, 'at': None, 'summary': None})
        items = self.items()
        results = self.api('import', items=items)['results']
        status = {r['origin']: r['status'] for r in results}
        self.assertEqual(status, {'cron:good': 'imported', 'cron:too-often': 'imported_paused',
                                  'cron:past': 'imported_paused', 'cron:flagged': 'imported_paused',
                                  'cron:empty': 'refused', None: 'refused'})
        by_origin = {r['origin']: r for r in results}
        good = self.api('get', origin='cron:good')['schedule']
        self.assertEqual((good['skip_if_running'], good['timezone'], good['start_mode']),
                         (False, 'Europe/London', 'existing'))
        self.assertGreater(good['next_due_at'], time.time())  # counted from now: never a replay
        self.assertEqual(self.scheduler.tick(now=time.time()), 0)
        imported_runs = [r for r in self.scheduler.history(good['id'], 100) if r['status'] == 'imported']
        self.assertEqual(len(imported_runs), 20)
        self.assertEqual(imported_runs[0]['label'], 'Ran before this update')
        often = self.api('get', id=by_origin['cron:too-often']['id'])['schedule']
        self.assertEqual((often['enabled'], often['status']), (False, 'needs_attention'))
        self.assertIn('every 5 minutes', often['problem'])
        self.assertEqual(often['cadence'], {'kind': 'interval', 'minutes': 5})
        flagged = self.api('get', id=by_origin['cron:flagged']['id'])['schedule']
        self.assertEqual(flagged['problem'], 'The model this task used is not available.')
        again = self.api('import', items=items)['results']
        self.assertEqual({r['origin']: r['status'] for r in again if r['origin']},
                         {'cron:good': 'exists', 'cron:too-often': 'exists', 'cron:past': 'exists',
                          'cron:flagged': 'exists', 'cron:empty': 'refused'})
        self.assertEqual(len(self.api('list')['schedules']), 4)
        recorded = self.api('migration_status', record={'imported': 4, 'refused': 2})
        self.assertTrue(recorded['done'])
        self.assertEqual(self.api('migration_status')['summary'], {'imported': 4, 'refused': 2})
        # A deleted import is not brought back by a rerun.
        self.api('delete', id=good['id'])
        self.assertEqual(self.api('import', items=items[:1])['results'][0]['status'], 'exists')
        with self.assertRaisesRegex(PolicyError, 'was deleted'):
            self.api('get', origin='cron:good')
        activity = self.service.action('/api/activity', {'project': self.project, 'kind': 'scheduled'})['entries']
        self.assertIn('Kel brought “Daily digest” over from your earlier scheduled tasks.',
                      [r['what'] for r in activity])


class RestartTests(Base):
    def test_a_run_lost_to_a_crash_says_it_did_not_start(self):
        schedule = self.create()
        slot = self.row(schedule['id'])['next_due_at']
        original = self.service.submit

        def crash(*args, **kwargs):
            raise KeyboardInterrupt  # the process died between the claim and the submission
        self.service.submit = crash
        with contextlib.suppress(KeyboardInterrupt):
            self.scheduler._fire(self.scheduler._loads(self.row(schedule['id'])), slot, 0.0)
        self.service.submit = original
        rows = self.scheduler.history(schedule['id'])
        self.assertEqual(rows[0]['status'], 'running')  # just fired: still starting
        stale = time.time() + 60
        rows = [self.scheduler._run_status(None, rows[0]['at'], stale, set(), None)]
        self.assertEqual((rows[0]['status'], rows[0]['cause']),
                         ('not_started', 'Kel closed before this run began.'))
        self.assertIsNone(self.scheduler._fire(self.scheduler._loads(self.row(schedule['id'])), slot, 0.0))

    def test_the_schema_is_migration_33_once(self):
        with contextlib.closing(self.service.store.connect()) as db:
            rows = db.execute("SELECT version,name FROM schema_migrations WHERE version=33").fetchall()
        self.assertEqual([tuple(r) for r in rows], [(33, 'v2-schedules')])
        self.assertFalse(sched.ensure_schema(self.service.store))


if __name__ == '__main__':
    unittest.main()
