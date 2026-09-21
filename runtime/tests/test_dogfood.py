"""Fix Capture (V2.0 preflight): the durable fix store, its statuses, and the fix-prompt contract.

The point of these pins is that Fix Capture stays a capture tool: exactly four statuses, no
tracking fields, screenshots that either belong to a saved fix or are swept, and a prompt that is
written before anything is marked BATCHED.
"""
import contextlib
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from kel.context import Context
from kel.core import PolicyError, Store
from kel.dogfood import STATUSES, Dogfood, ensure_schema

EXPECTED_COLUMNS = {
    'id', 'created', 'updated', 'status', 'transcript', 'screenshot', 'route', 'page_title',
    'element', 'window', 'diagnostics', 'project_id', 'conversation', 'version', 'prompt_id',
}


def craft_temp_screenshot(dogfood, name='pending.png'):
    dogfood.tmp.mkdir(parents=True, exist_ok=True)
    target = dogfood.tmp / name
    target.write_bytes(b'\x89PNG\r\n\x1a\n not-a-real-png-but-a-real-file')
    return target


class DogfoodCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.context = Context(self.store)
        self.p1 = self.context.project('One', project_id='p1')
        self.c1 = self.context.conversation('p1', title='First')
        self.dogfood = Dogfood(self.store)

    def save(self, transcript='The Work page said waiting but nothing happened.', **extra):
        return self.dogfood.save(transcript, **extra)

    # -- schema / shape --------------------------------------------------------------------------
    def test_schema_has_no_tracking_fields(self):
        with contextlib.closing(self.store.connect()) as db:
            columns = {row[1] for row in db.execute('PRAGMA table_info(dogfood_fixes)')}
        self.assertEqual(columns, EXPECTED_COLUMNS)
        self.assertEqual(STATUSES, ('OPEN', 'BATCHED', 'FIXED', 'DISMISSED'))
        for banned in ('assignee', 'priority', 'labels', 'due', 'sprint', 'board', 'comments'):
            self.assertNotIn(banned, columns)

    def test_ensure_schema_is_idempotent(self):
        self.assertFalse(ensure_schema(self.store))
        self.assertTrue(self.dogfood.prompts.is_dir())
        self.assertTrue(self.dogfood.screenshots.is_dir())

    # -- save ------------------------------------------------------------------------------------
    def test_save_requires_a_transcript(self):
        with self.assertRaises(PolicyError) as ctx:
            self.save('   ')
        self.assertIn('what went wrong', str(ctx.exception))

    def test_save_allocates_sequential_ids_and_opens(self):
        first = self.save('First finding')
        second = self.save('Second finding')
        self.assertEqual(first['id'], 'FIX-0001')
        self.assertEqual(second['id'], 'FIX-0002')
        self.assertEqual(first['status'], 'OPEN')
        self.assertEqual(self.dogfood.list()['counts']['OPEN'], 2)

    def test_save_keeps_the_captured_context(self):
        item = self.save(
            'The toast covered the button',
            route='/work',
            page_title='Kel — Work',
            version='1.7.0-dev',
            element={'tag': 'button', 'text': 'Save + Verify', 'selector': 'div.kel-card > button'},
            window={'width': 1440, 'height': 900, 'scale': 1},
            diagnostics={'engine': 'ok'},
        )
        self.assertEqual(item['route'], '/work')
        self.assertEqual(item['element']['tag'], 'button')
        self.assertEqual(item['window']['width'], 1440)
        self.assertEqual(item['diagnostics'], {'engine': 'ok'})

    def test_screenshot_is_committed_under_the_fix_id(self):
        pending = craft_temp_screenshot(self.dogfood)
        item = self.save('Button label is wrong', screenshot=str(pending))
        committed = self.dogfood.screenshots / 'FIX-0001.png'
        self.assertEqual(item['screenshot'], 'dogfood/screenshots/FIX-0001.png')
        self.assertTrue(item['has_screenshot'])
        self.assertTrue(committed.is_file())
        self.assertFalse(pending.exists())

    def test_relative_temp_path_is_accepted(self):
        craft_temp_screenshot(self.dogfood, 'from-main.png')
        item = self.save('Relative capture', screenshot='dogfood/tmp/from-main.png')
        self.assertEqual(item['screenshot'], 'dogfood/screenshots/FIX-0001.png')

    def test_discard_removes_only_in_flight_captures(self):
        # A cancelled capture must not leave its screenshot behind.
        capture = craft_temp_screenshot(self.dogfood, 'cancelled.png')
        self.assertTrue(self.dogfood.discard_tmp('dogfood/tmp/cancelled.png')['discarded'])
        self.assertFalse(capture.exists())
        # Discarding something already gone (or already committed under a fix) is a quiet no-op.
        self.assertFalse(self.dogfood.discard_tmp('dogfood/tmp/cancelled.png')['discarded'])
        item = self.save('Committed', screenshot=str(craft_temp_screenshot(self.dogfood, 'kept.png')))
        self.assertTrue(item['has_screenshot'])
        # A committed screenshot is out of reach by design: cancelling can never delete one.
        with self.assertRaises(PolicyError):
            self.dogfood.discard_tmp(item['screenshot'])
        self.assertTrue((Path(self.temp.name) / 'dogfood/screenshots/FIX-0001.png').is_file())
        # And nothing outside dogfood/tmp can be reached this way.
        with self.assertRaises(PolicyError):
            self.dogfood.discard_tmp('dogfood/screenshots/FIX-0001.png')
        with self.assertRaises(PolicyError):
            self.dogfood.discard_tmp('../kel.sqlite3')

    def test_screenshot_outside_the_dogfood_folder_is_refused(self):
        outside = Path(self.temp.name) / 'outside.png'
        outside.write_bytes(b'not ours')
        for bad in (str(outside), '../outside.png', 'transcription/audio/x.wav'):
            with self.assertRaises(PolicyError) as ctx:
                self.save('Sneaky path', screenshot=bad)
            self.assertIn('inside Kel data', str(ctx.exception))

    def test_missing_screenshot_still_saves_honestly(self):
        item = self.save('Capture vanished', screenshot='dogfood/tmp/never-existed.png')
        self.assertIsNone(item['screenshot'])
        self.assertFalse(item['has_screenshot'])

    def test_project_is_resolved_from_the_conversation(self):
        in_project = self.save('In a conversation', conversation=self.c1)
        unknown = self.save('No conversation', conversation='does-not-exist')
        self.assertEqual(in_project['project_id'], 'p1')
        self.assertIsNone(unknown['project_id'])

    def test_long_transcripts_are_bounded_not_lost(self):
        item = self.save('x' * 9000)
        self.assertEqual(len(item['transcript']), 8000)

    # -- statuses --------------------------------------------------------------------------------
    def test_set_status_validates_and_persists(self):
        item = self.save('Status me')
        with self.assertRaises(PolicyError):
            self.dogfood.set_status(item['id'], 'IN_REVIEW')
        with self.assertRaises(PolicyError):
            self.dogfood.set_status('FIX-9999', 'FIXED')
        moved = self.dogfood.set_status(item['id'], 'FIXED')
        self.assertEqual(moved['status'], 'FIXED')
        self.assertGreaterEqual(moved['updated'], moved['created'])
        reopened = self.dogfood.set_status(item['id'], 'OPEN')
        self.assertEqual(reopened['status'], 'OPEN')

    def test_list_filters_by_status(self):
        first = self.save('One')
        self.save('Two')
        self.dogfood.set_status(first['id'], 'DISMISSED')
        listing = self.dogfood.list('OPEN')
        self.assertEqual([item['id'] for item in listing['fixes']], ['FIX-0002'])
        self.assertEqual(listing['counts'], {'OPEN': 1, 'BATCHED': 0, 'FIXED': 0, 'DISMISSED': 1})
        with self.assertRaises(PolicyError):
            self.dogfood.list('NOPE')

    # -- prompts ---------------------------------------------------------------------------------
    def test_prepare_prompt_includes_open_fixes_and_marks_them_batched(self):
        self.save('The first thing broke', route='/work', version='1.7.0-dev',
                  element={'tag': 'button', 'text': 'Retry', 'rect': {'x': 10, 'y': 20, 'width': 80, 'height': 24}})
        self.save('The second thing broke', route='/providers')
        result = self.dogfood.prepare_prompt()
        self.assertEqual(result['fix_ids'], ['FIX-0001', 'FIX-0002'])
        self.assertEqual(result['marked'], 'BATCHED')
        self.assertIn('The first thing broke', result['prompt'])
        self.assertIn('The second thing broke', result['prompt'])
        self.assertIn('FIX-0001', result['prompt'])
        self.assertIn('/work', result['prompt'])
        self.assertIn('x=10 y=20 w=80 h=24', result['prompt'])
        self.assertEqual(self.dogfood.get('FIX-0001')['status'], 'BATCHED')
        self.assertEqual(self.dogfood.get('FIX-0002')['status'], 'BATCHED')
        written = Path(self.store.root) / result['path']
        self.assertTrue(written.is_file())
        self.assertEqual(written.read_text(encoding='utf-8'), result['prompt'])

    def test_prepare_prompt_without_open_fixes_says_so(self):
        with self.assertRaises(PolicyError) as ctx:
            self.dogfood.prepare_prompt()
        self.assertIn('No open fixes', str(ctx.exception))

    def test_prepare_prompt_selection_leaves_the_rest_alone(self):
        self.save('One')
        self.save('Two')
        self.save('Three')
        result = self.dogfood.prepare_prompt(['FIX-0001', 'FIX-0003'])
        self.assertEqual(result['fix_ids'], ['FIX-0001', 'FIX-0003'])
        self.assertIn('## Findings (2)', result['prompt'])
        self.assertEqual(self.dogfood.get('FIX-0002')['status'], 'OPEN')
        self.assertEqual(result['fix_ids'], [item['id'] for item in self.dogfood.list('BATCHED')['fixes']][::-1])

    def test_prompt_is_deterministic_and_carries_the_ten_instructions(self):
        self.save('Alpha', route='/a')
        self.save('Beta', route='/b')
        first = self.dogfood.prepare_prompt()['prompt']
        for instruction in ('1. Reconcile git', '2. Reproduce each finding',
                            '3. Group findings that share a root cause',
                            '4. Do not treat duplicate symptoms',
                            '5. Implement the smallest coherent fixes',
                            "6. Preserve Kel's product north star",
                            '7. Add or update regression coverage',
                            '8. Verify the affected UI directly',
                            '9. Do not mark a fix resolved merely because code changed',
                            '10. Return the exact Fix ids you verified as repaired'):
            self.assertIn(instruction, first)
        # Id order, and re-running over the same content produces the same body.
        self.assertLess(first.index('FIX-0001'), first.index('FIX-0002'))
        self.save('Gamma')
        second = self.dogfood.prepare_prompt()['prompt']
        self.assertIn('## Findings (1)', second)
        self.assertIn('Gamma', second)

    def test_a_failed_prompt_write_leaves_statuses_untouched(self):
        item = self.save('Cannot write prompts')
        locked = self.dogfood.prompts / 'PROMPT-locked.md'
        locked.parent.mkdir(parents=True, exist_ok=True)
        real_write = Path.write_text

        def explode(self_path, *args, **kwargs):
            raise OSError('disk full')

        Path.write_text = explode
        try:
            with self.assertRaises(PolicyError) as ctx:
                self.dogfood.prepare_prompt()
            self.assertIn('could not write the fix prompt', str(ctx.exception))
        finally:
            Path.write_text = real_write
        self.assertEqual(self.dogfood.get(item['id'])['status'], 'OPEN')

    # -- housekeeping / durability ---------------------------------------------------------------
    def test_stale_temporary_screenshots_are_swept(self):
        stale = craft_temp_screenshot(self.dogfood, 'stale.png')
        old = time.time() - 3 * 24 * 60 * 60
        os.utime(stale, (old, old))
        fresh = craft_temp_screenshot(self.dogfood, 'fresh.png')
        self.dogfood.list()
        self.assertFalse(stale.exists())
        self.assertTrue(fresh.exists())

    def test_fixes_survive_a_reopen(self):
        item = self.save('Persist me', route='/dogfood')
        reopened = Dogfood(Store(self.temp.name))
        self.assertEqual(reopened.get(item['id'])['transcript'], 'Persist me')
        self.assertEqual(reopened.list()['counts']['OPEN'], 1)

    def test_migration_row_is_recorded_once(self):
        with contextlib.closing(self.store.connect()) as db:
            rows = [dict(row) for row in db.execute('SELECT * FROM schema_migrations WHERE version=22')]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['name'], 'v20-fix-capture')


class PracticeTextGuardCase(unittest.TestCase):
    """Canned practice text is never stored as Nick's feedback unless practice mode was asked for.

    Production logic: explicit fixture requested → FixtureProvider; otherwise a real key → Muse;
    otherwise an honest error. The store enforces the same rule from the other side, so a debug build
    that leaves practice mode on by accident still cannot file canned text as a real finding.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        self.dogfood = Dogfood(self.store)
        self._previous = {name: os.environ.get(name) for name in ('KEL_TRANSCRIPTION_PROVIDER', 'KEL_TRANSCRIPTION_MODE')}
        self.addCleanup(self._restore_env)
        for name in self._previous:
            os.environ.pop(name, None)  # production default: practice mode is off unless asked for

    def _restore_env(self):
        for name, value in self._previous.items():
            os.environ.pop(name, None)
            if value is not None:
                os.environ[name] = value

    def practice_sentence(self):
        from kel.transcription import FIXTURE_SENTENCES

        return FIXTURE_SENTENCES[0]

    def test_production_refuses_the_archived_practice_text(self):
        with self.assertRaises(PolicyError) as ctx:
            self.dogfood.save(self.practice_sentence())
        self.assertIn('practice text', str(ctx.exception))
        self.assertEqual(self.dogfood.list()['counts']['OPEN'], 0)

    def test_production_refuses_practice_text_hidden_inside_longer_feedback(self):
        hidden = 'Right, so — ' + self.practice_sentence() + ' — and that is what keeps happening.'
        with self.assertRaises(PolicyError):
            self.dogfood.save(hidden)
        self.assertEqual(self.dogfood.list()['counts']['OPEN'], 0)

    def test_a_real_transcript_saves_even_when_it_mentions_practice(self):
        item = self.dogfood.save('The practice screen shows a stale banner after I change the key.')
        self.assertEqual(item['status'], 'OPEN')
        self.assertIn('stale banner', item['transcript'])

    def test_explicit_practice_mode_still_saves_so_automation_can_exercise_the_flow(self):
        os.environ['KEL_TRANSCRIPTION_PROVIDER'] = 'fixture'
        item = self.dogfood.save(self.practice_sentence())
        self.assertEqual(item['status'], 'OPEN')
        self.assertTrue(item['transcript'])

    def test_the_practice_setting_also_allows_it(self):
        # The engine-side practice switch (used by development builds) behaves like the env var.
        from kel.transcription import Transcription

        Transcription(self.store)._set_setting('transcription_mode', 'fixture')
        item = self.dogfood.save(self.practice_sentence())
        self.assertEqual(item['status'], 'OPEN')


if __name__ == '__main__':
    unittest.main()
