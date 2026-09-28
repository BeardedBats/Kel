"""D-65: Full access applies a verified coding change on its own; everything else still waits."""
import contextlib
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from kel import authority
from kel.activity import sentence_for
from kel.apply_changes import application, apply_checked, recover_prepared, undo_applied
from kel.auto_apply import decision, describe, settle
from kel.coding import CodingAdapter, compile_coding, file_manifest, git, snapshot
from kel.core import PolicyError, Store, digest, encode


class Crash(BaseException):
    """A process death: nothing in Kel catches it, so the journal is left exactly as it was."""


class AutoApplyBase(unittest.TestCase):
    review = 'VERIFIED'
    exit_code = 0

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.root = base / 'source'
        self.root.mkdir()
        git(self.root, 'init')
        (self.root / 'app.txt').write_text('old')
        (self.root / 'remove.txt').write_text('remove')
        git(self.root, 'add', '-A')
        git(self.root, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost', 'commit', '-m', 'base')
        self.s = Store(base / 'data')
        CodingAdapter(self.s)
        self.j = self.s.create(compile_coding('Change app.txt, remove remove.txt, add new.txt.', self.root,
                                              ['python', '-m', 'unittest']))
        self.w = base / 'copy'
        revision = snapshot(self.root, self.w)
        baseline = file_manifest(self.w)
        (self.w / 'app.txt').write_text('new')
        (self.w / 'new.txt').write_text('added')
        (self.w / 'remove.txt').unlink()
        git(self.w, 'add', '-A')
        diff = git(self.w, 'diff', '--cached', '--binary', revision).decode()
        run = self.s.claim(self.j, 'code', provider='codex-code')
        tests = {'exit_code': self.exit_code, 'existing_tests_preserved': True, 'source_stable_during_tests': True}
        with self.s.transaction() as db:
            db.execute('INSERT INTO code_workspaces VALUES(?,?,?,?)', (self.j, str(self.w), revision, encode(baseline)))
            db.execute('INSERT INTO code_evidence VALUES(?,?,?,?,?,?,?,?)',
                       (run['id'], str(self.w), encode(file_manifest(self.w)), diff, digest(diff.encode()),
                        encode(tests), '{}', time.time()))
        self.s.enqueue_result('result', run['id'], run['epoch'],
                              {'outcome': 'SUCCESS', 'text': 'Verified fixture change with complete trusted evidence.'})
        self.s.consume()
        self.s.verify(self.j, 'code')
        artifact = self.s.get(self.j)['milestones']['code']['artifact']
        self.s.record_review(self.j, 'code', artifact['sha256'], 'reviewer', self.review, ['Fixture review.'])
        self.verdict = self.s.assess(self.j)  # what the engine does before it settles a job

    def tearDown(self):
        self.tmp.cleanup()

    def events(self, kind):
        found = [e for e in self.s.events() if e.get('type') == kind and e.get('aggregate_id') == self.j]
        for event in found:
            if isinstance(event.get('payload'), str):
                event['payload'] = json.loads(event['payload'])
        return found

    def messages(self):
        with contextlib.closing(self.s.connect()) as db:
            return [r['text'] for r in db.execute('SELECT text FROM messages ORDER BY seq')]

    def untouched(self):
        self.assertEqual((self.root / 'app.txt').read_text(), 'old')
        self.assertTrue((self.root / 'remove.txt').exists())
        self.assertFalse((self.root / 'new.txt').exists())

    def applied(self):
        self.assertEqual((self.root / 'app.txt').read_text(), 'new')
        self.assertFalse((self.root / 'remove.txt').exists())
        self.assertEqual((self.root / 'new.txt').read_text(), 'added')


class FullAccessTests(AutoApplyBase):
    def test_full_access_applies_a_verified_change_with_one_activity_line(self):
        self.assertEqual(authority.mode(self.s), 'full')
        self.assertEqual(self.s.assess(self.j), 'VERIFIED')
        self.assertEqual(settle(self.s, self.j), 'applied')
        self.applied()
        self.assertEqual(decision(self.s, self.j)['decision'], 'applied')
        self.assertEqual(application(self.s, self.j)['state'], 'APPLIED')
        lines = self.events('changes.auto_applied')
        self.assertEqual(len(lines), 1)
        self.assertEqual(self.events('changes.applied'), [])
        sentence = sentence_for('changes.auto_applied', lines[0]['payload'])
        self.assertEqual(sentence, 'Full access: Kel went ahead to apply the checked change to source (3 files).')
        # No separate "Applied" chat line: the result message says it.
        self.assertFalse(any('Applied the checked changes' in text for text in self.messages()))

    def test_result_message_says_what_where_and_how_it_was_checked(self):
        settle(self.s, self.j)
        text, fresh = self.s.publish(self.j)
        self.assertTrue(fresh)
        # The folder's name, once — never the full path (it stays behind "Open folder").
        self.assertIn('Applied to source: ', text)
        self.assertNotIn(str(self.root), text)
        self.assertIn('changed app.txt', text)
        self.assertIn('added new.txt', text)
        self.assertIn('removed remove.txt', text)
        self.assertIn('(3 files)', text)
        self.assertIn('your tests (python -m unittest) passed', text)
        self.assertIn('a separate review approved the change', text)
        self.assertIn('Undo', text)
        self.assertNotIn('Apply checked changes', text)

    def test_a_named_project_says_its_name_and_folder_once(self):
        from kel.auto_apply import describe, place
        with self.s.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,root TEXT,'
                       'context TEXT,updated REAL)')
            db.execute('INSERT INTO projects(id,name,root,updated) VALUES(?,?,?,?)',
                       ('calc', 'Calc demo', str(self.root), time.time()))
        self.assertEqual(place(self.s, str(self.root))['words'], 'Calc demo (folder source)')
        settle(self.s, self.j)
        text, _fresh = self.s.publish(self.j)
        self.assertIn('Applied to Calc demo (folder source): changed app.txt', text)
        self.assertEqual(text.count('source'), 1)
        entry = describe(self.s, [self.j])[self.j]
        self.assertEqual((entry['project_name'], entry['folder']), ('Calc demo', 'source'))
        self.assertEqual(entry['root'], str(self.root), 'the full path stays for Open folder')

    def test_engine_applies_before_it_publishes(self):
        from kel.engine import Engine
        engine = Engine(self.s, {})
        try:
            engine.tick()
        finally:
            engine.close()
        self.applied()
        with contextlib.closing(self.s.connect()) as db:
            published = db.execute('SELECT text FROM publications WHERE job_id=?', (self.j,)).fetchall()
        self.assertEqual(len(published), 1)
        self.assertIn('Applied to', published[0]['text'])

    def test_settling_again_never_applies_twice(self):
        self.assertEqual(settle(self.s, self.j), 'applied')
        (self.root / 'app.txt').write_text('your later edit')
        self.assertEqual(settle(Store(self.s.root), self.j), 'applied')
        self.assertEqual((self.root / 'app.txt').read_text(), 'your later edit')
        self.assertEqual(len(self.events('changes.auto_applied')), 1)

    def test_work_card_state_names_the_automatic_apply(self):
        settle(self.s, self.j)
        card = describe(self.s, [self.j])[self.j]
        self.assertEqual(card['state'], 'APPLIED')
        self.assertTrue(card['auto'])
        self.assertEqual(card['files'], 3)
        self.assertEqual(card['root'], str(self.root.resolve()))
        self.assertIsNone(card['waiting_reason'])


class AskFirstTests(AutoApplyBase):
    def test_ask_first_waits_and_the_card_asks_apply_or_leave_it(self):
        from kel import needs_answer
        authority.set_mode(self.s, 'ask')
        self.assertEqual(settle(self.s, self.j), 'waiting')
        self.untouched()
        self.assertIsNone(application(self.s, self.j))
        text, _ = self.s.publish(self.j)
        # The result names the control Nick really has (D-70), never the retired Work-panel button.
        self.assertIn('Ask first is on, so Kel has not changed source yet.', text)
        self.assertIn('Choose Apply on its work card at the top of this chat', text)
        self.assertIn('python -m unittest', text)  # how it was checked
        for gone in ('Apply checked changes', 'change report', str(self.root)):
            self.assertNotIn(gone, text)
        card = describe(self.s, [self.j])[self.j]
        self.assertIsNone(card['state'])
        self.assertFalse(card['auto'])
        self.assertTrue(card['ask_first'])
        self.assertEqual(card['waiting_reason'], 'Ask first is on')
        question = needs_answer.question(self.s, self.s.get(self.j))
        self.assertEqual(question['kind'], 'apply')
        self.assertEqual(question['text'], 'The change passed its checks. Apply it to source?')
        self.assertEqual(question['options'], [{'id': 'apply_anyway', 'label': 'Apply'},
                                               {'id': 'leave', 'label': 'Leave it'}])
        self.assertIn('Ask first is on, so Kel waits for you', question['detail'])
        # "Apply" is the existing apply path with Nick as the actor.
        out = needs_answer.answer_apply(self.s, self.j, 'apply_anyway', actor='user')
        self.assertEqual(out['application']['state'], 'APPLIED')
        self.applied()
        self.assertEqual(decision(self.s, self.j)['decision'], 'manual')
        self.assertEqual(len(self.events('changes.applied')), 1)
        self.assertEqual(self.events('changes.auto_applied'), [])
        card = describe(self.s, [self.j])[self.j]
        self.assertEqual((card['state'], card['waiting_reason'], card['ask_first']), ('APPLIED', None, False))
        answered = self.events('needs_you.answered')
        self.assertEqual(answered[0]['payload']['detail']['wait'], 'ask_first')
        self.assertEqual(sentence_for('needs_you.answered', answered[0]['payload']), 'You applied the checked change.')
        self.assertEqual(undo_applied(self.s, self.j, actor='user')['state'], 'UNDONE')  # Undo keeps working
        self.untouched()

    def test_the_plain_apply_route_still_works_under_ask_first(self):
        authority.set_mode(self.s, 'ask')
        settle(self.s, self.j)
        self.assertEqual(apply_checked(self.s, self.j, actor='user')['state'], 'APPLIED')
        self.applied()
        self.assertEqual(decision(self.s, self.j)['decision'], 'manual')
        self.assertIsNone(describe(self.s, [self.j])[self.j]['waiting_reason'])

    def test_leave_it_changes_nothing_and_the_card_stops_asking(self):
        from kel import needs_answer
        authority.set_mode(self.s, 'ask')
        settle(self.s, self.j)
        self.s.publish(self.j)
        out = needs_answer.answer_apply(self.s, self.j, 'leave', actor='user')
        self.assertEqual((out['choice'], out['already']), ('leave', False))
        self.untouched()
        card = describe(self.s, [self.j])[self.j]
        self.assertEqual((card['waiting_reason'], card['ask_first']), (None, False))
        self.assertEqual(needs_answer.settled_line(self.s, self.s.get(self.j)),
                         ('done', 'Checked; you chose to leave it unapplied.'))
        with self.assertRaisesRegex(PolicyError, 'Only you'):
            needs_answer.answer_apply(self.s, self.j, 'apply_anyway', actor='kel')

    def test_the_handoff_view_keeps_the_line_live_while_the_change_waits(self):
        from kel import handoff, needs_answer
        from kel.service import Service
        authority.set_mode(self.s, 'ask')
        settle(self.s, self.j)
        self.s.publish(self.j)
        handoff.ensure_schema(self.s)
        conversation = self.s.get(self.j)['conversation']
        with self.s.transaction() as db:
            db.execute('INSERT INTO submissions VALUES(?,?,?,?,?,?,?)',
                       ('sub', conversation, 'Change app.txt', 'DISPATCHED', None, self.j, time.time()))
        service = Service.__new__(Service)  # handoff_view reads only the store
        service.store = self.s
        view = service.handoff_view(conversation, 'sub')
        self.assertEqual(view['phase'], 'needs_you')  # not terminal: the in-thread line keeps polling
        self.assertIn('Ask first is on, so it waits for you to apply it', view['why'])
        self.assertTrue(view['application']['ask_first'])
        needs_answer.answer_apply(self.s, self.j, 'apply_anyway', actor='user')
        self.assertEqual(service.handoff_view(conversation, 'sub')['phase'], 'done')

    def test_after_switching_to_full_access_the_card_says_ask_first_was_on(self):
        from kel import needs_answer
        authority.set_mode(self.s, 'ask')
        settle(self.s, self.j)
        authority.set_mode(self.s, 'full')
        self.assertEqual(settle(self.s, self.j), 'waiting')  # never re-decided on its own
        self.untouched()
        self.assertEqual(describe(self.s, [self.j])[self.j]['waiting_reason'], 'Ask first was on when it finished')
        self.assertIn('Ask first was on when it finished, so Kel waits',
                      needs_answer.question(self.s, self.s.get(self.j))['detail'])

    def test_a_waiting_change_stays_waiting_after_a_restart_and_a_mode_change(self):
        authority.set_mode(self.s, 'ask')
        self.assertEqual(settle(self.s, self.j), 'waiting')
        authority.set_mode(self.s, 'full')
        self.assertEqual(settle(Store(self.s.root), self.j), 'waiting')
        self.untouched()


class FailedReviewTests(AutoApplyBase):
    review = 'FAILED'

    def test_a_change_that_failed_its_review_is_never_applied(self):
        self.assertNotEqual(self.s.assess(self.j), 'VERIFIED')
        self.assertIsNone(settle(self.s, self.j))
        self.untouched()
        self.assertIsNone(decision(self.s, self.j))


class FailedTestsTests(AutoApplyBase):
    exit_code = 1

    def test_a_change_whose_tests_failed_is_never_applied(self):
        self.assertNotEqual(self.s.assess(self.j), 'VERIFIED')
        self.assertIsNone(settle(self.s, self.j))
        self.untouched()


class SkippedReviewTests(AutoApplyBase):
    def test_a_review_without_a_recorded_reviewer_counts_as_skipped(self):
        from kel.auto_apply import verification_complete
        job = self.s.get(self.j)
        self.assertTrue(verification_complete(self.s, job))
        for check in job['milestones']['code']['checks']:
            if check['kind'] == 'manual_review':
                check.pop('reviewer_id')
        self.assertFalse(verification_complete(self.s, job))


class ProtectedPlaceTests(AutoApplyBase):
    def test_a_change_touching_a_protected_place_waits_with_its_reason(self):
        real = __import__('kel.containment', fromlist=['sensitive_reason']).sensitive_reason

        def flag(path, store=None):
            return 'your credentials folder' if str(path).endswith('new.txt') else real(path, store=store)

        with patch('kel.containment.sensitive_reason', side_effect=flag):
            self.assertEqual(settle(self.s, self.j), 'waiting')
        self.untouched()
        self.assertEqual(decision(self.s, self.j)['reason'], 'it would change your credentials folder')
        self.assertEqual(describe(self.s, [self.j])[self.j]['waiting_reason'],
                         'it would change your credentials folder')
        text, _ = self.s.publish(self.j)
        self.assertIn('Kel did not apply it on its own: it would change your credentials folder', text)
        # It names the control the person actually has: Apply anyway on the work card (D-70).
        self.assertIn('Choose Apply anyway on its work card at the top of this chat', text)
        self.assertNotIn('Work context', text)
        # Full access keeps its own words: "Apply anyway", and the reason it held the change.
        from kel import needs_answer
        self.assertFalse(describe(self.s, [self.j])[self.j]['ask_first'])
        question = needs_answer.question(self.s, self.s.get(self.j))
        self.assertEqual([o['label'] for o in question['options']], ['Apply anyway', 'Leave it'])
        self.assertEqual(question['detail'], 'Kel waited because it would change your credentials folder.')
        self.assertEqual(self.events('changes.auto_applied'), [])

    def test_a_refused_apply_waits_instead_of_retrying(self):
        (self.root / 'app.txt').write_text('your edit while Kel worked')
        self.assertEqual(settle(self.s, self.j), 'waiting')
        self.assertIn('your project changed since coding started', decision(self.s, self.j)['reason'])
        self.assertEqual((self.root / 'app.txt').read_text(), 'your edit while Kel worked')
        self.assertFalse((self.root / 'new.txt').exists())
        self.assertEqual(settle(self.s, self.j), 'waiting')


class RestartTests(AutoApplyBase):
    def crash_after_first_replacement(self):
        replace = os.replace
        calls = []

        def interrupt(a, b):
            calls.append(str(b))
            replace(a, b)
            if len(calls) == 1:
                raise Crash('process died after the first file')

        with patch('kel.apply_changes.os.replace', side_effect=interrupt):
            with self.assertRaises(Crash):
                settle(self.s, self.j)
        self.assertEqual(decision(self.s, self.j)['decision'], 'applying')
        self.assertEqual(application(self.s, self.j)['state'], 'PREPARED')
        return calls, replace

    def test_start_up_recovery_finishes_an_interrupted_automatic_apply_once(self):
        calls, replace = self.crash_after_first_replacement()
        restarted = Store(self.s.root)
        with patch('kel.apply_changes.os.replace', wraps=replace) as resumed:
            recover_prepared(restarted)
            self.assertNotIn(calls[0], [str(c.args[1]) for c in resumed.call_args_list])
        self.applied()
        self.assertEqual(decision(restarted, self.j)['decision'], 'applied')
        self.assertEqual(len(self.events('changes.auto_applied')), 1)
        self.assertEqual(self.events('changes.applied'), [])
        self.assertEqual(settle(restarted, self.j), 'applied')
        self.assertEqual(len(self.events('changes.auto_applied')), 1)

    def test_the_engine_settle_also_resumes_an_interrupted_apply_once(self):
        self.crash_after_first_replacement()
        restarted = Store(self.s.root)
        self.assertEqual(settle(restarted, self.j), 'applied')
        self.assertEqual(settle(restarted, self.j), 'applied')
        self.applied()
        self.assertEqual(len(self.events('changes.auto_applied')), 1)
        recover_prepared(restarted)  # nothing left to recover
        self.assertEqual(len(self.events('changes.auto_applied')), 1)


class UndoTests(AutoApplyBase):
    def test_undo_after_an_automatic_apply_puts_the_earlier_files_back(self):
        self.assertEqual(settle(self.s, self.j), 'applied')
        result = undo_applied(self.s, self.j)
        self.assertEqual(result, {'state': 'UNDONE', 'files': 3})
        self.untouched()
        self.assertEqual((self.root / 'remove.txt').read_text(), 'remove')
        self.assertEqual(application(self.s, self.j)['state'], 'UNDONE')
        lines = self.events('changes.undone')
        self.assertEqual(len(lines), 1)
        self.assertEqual(sentence_for('changes.undone', lines[0]['payload']),
                         'The applied change was undone; the earlier files are back.')
        self.assertTrue(any(text.startswith('Undid the change in ') for text in self.messages()))
        self.assertTrue(undo_applied(self.s, self.j)['already_undone'])
        self.assertEqual(describe(self.s, [self.j])[self.j]['state'], 'UNDONE')

    def test_undo_never_overwrites_a_later_edit(self):
        settle(self.s, self.j)
        (self.root / 'app.txt').write_text('your later edit')
        with self.assertRaises(PolicyError) as caught:
            undo_applied(self.s, self.j)
        self.assertIn('app.txt changed after Kel applied it', str(caught.exception))
        self.assertEqual((self.root / 'app.txt').read_text(), 'your later edit')
        self.assertTrue((self.root / 'new.txt').exists())
        self.assertEqual(application(self.s, self.j)['state'], 'APPLIED')

    def test_an_interrupted_undo_resumes_at_start_up(self):
        settle(self.s, self.j)
        replace = os.replace
        calls = []

        def interrupt(a, b):
            calls.append(str(b))
            replace(a, b)
            raise Crash('process died during undo')

        with patch('kel.apply_changes.os.replace', side_effect=interrupt):
            with self.assertRaises(Crash):
                undo_applied(self.s, self.j)
        self.assertEqual(application(self.s, self.j)['state'], 'UNDOING')
        recover_prepared(Store(self.s.root))
        self.untouched()
        self.assertEqual(application(self.s, self.j)['state'], 'UNDONE')

    def test_nothing_to_undo_before_an_apply(self):
        with self.assertRaises(PolicyError):
            undo_applied(self.s, self.j)

    def test_apply_again_after_undo_is_a_manual_apply(self):
        settle(self.s, self.j)
        undo_applied(self.s, self.j)
        self.assertEqual(apply_checked(self.s, self.j, actor='user')['state'], 'APPLIED')
        self.applied()
        self.assertEqual(decision(self.s, self.j)['decision'], 'manual')
        self.assertFalse(describe(self.s, [self.j])[self.j]['auto'])


if __name__ == '__main__':
    unittest.main()
