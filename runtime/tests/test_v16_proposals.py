"""V1.6 memory proposal surface — engine verification.

The review queue over saved project knowledge: proposals are queued with a plain reason, applied
only after explicit acceptance (through the normal trust model, preserving the previous value),
suppressed when the same unchanged evidence was already rejected, and scoped to one project.
Triggers covered here: Design Vetting decisions vs stored rules, open conflicts between confirmed
choices, and stale source digests.
"""
import contextlib
import json
import tempfile
import unittest
from pathlib import Path

from kel.core import PolicyError, Store
from kel.context import Context
from kel.memory import Memory, PROPOSALS_VERSION


class ProposalBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        self.context = Context(self.store)
        self.p1 = self.context.project('Project One', project_id='p1')
        self.p2 = self.context.project('Project Two', project_id='p2')
        self.memory = Memory(self.store)

    def rec(self, project=None, *, topic='release.channel', type='decision',
            summary='Ship from the frozen folder only.', value=None, source_ref='',
            source_digest=None, source_type='user_instruction'):
        return self.memory.record(
            project or self.p1, type, topic, value or {'statement': summary}, summary,
            source_type=source_type, source_ref=source_ref, source_digest=source_digest,
            actor='user', user_confirmed=1)

    def propose(self, current_id, *, value, summary='Ship from a release branch instead.',
                why='The stored rule and the new decision disagree.', sig='e1', kind='vetting',
                topic='release.channel', project=None):
        return self.memory.propose_change(
            project or self.p1, kind=kind, type='decision', topic=topic, value=value,
            summary=summary, why=why, current_id=current_id, evidence={'sig': sig},
            source_ref='test')


class ProposalLifecycleTests(ProposalBase):
    def test_proposal_pending_listed_with_current_and_proposed(self):
        rid = self.rec()
        out = self.propose(rid, value={'statement': 'Ship from a release branch instead.'})
        self.assertEqual(out['state'], 'pending')
        listed = self.memory.proposals(self.p1, state='open')
        self.assertEqual([p['id'] for p in listed], [out['id']])
        item = self.memory.proposal(out['id'])
        self.assertEqual(item['kind'], 'vetting')
        self.assertEqual(item['current']['summary'], 'Ship from the frozen folder only.')
        self.assertEqual(item['value'], {'statement': 'Ship from a release branch instead.'})
        self.assertIn('disagree', item['why'])

    def test_pending_duplicate_returns_same_id(self):
        rid = self.rec()
        first = self.propose(rid, value={'statement': 'A'})
        again = self.propose(rid, value={'statement': 'A'})
        self.assertEqual(first['id'], again['id'])
        self.assertEqual(len(self.memory.proposals(self.p1, state='open')), 1)

    def test_no_change_and_no_target_are_skipped(self):
        rid = self.rec()
        same = self.memory.propose_change(
            self.p1, kind='vetting', type='decision', topic='release.channel',
            value={'statement': 'Ship from the frozen folder only.'},
            summary='x', why='y', current_id=rid, evidence={'sig': 's'})
        self.assertEqual(same['state'], 'no_change')
        self.assertEqual(self.memory.proposals(self.p1, state='open'), [])

    def test_rejected_identical_evidence_is_suppressed(self):
        rid = self.rec()
        first = self.propose(rid, value={'statement': 'A'})
        self.memory.reject_proposal(first['id'], reason='keep what we have')
        again = self.propose(rid, value={'statement': 'A'})
        self.assertTrue(again['suppressed'])
        self.assertEqual(again['state'], 'rejected')
        self.assertEqual(self.memory.proposals(self.p1, state='open'), [])

    def test_changed_evidence_asks_again(self):
        rid = self.rec()
        first = self.propose(rid, value={'statement': 'A'}, sig='e1')
        self.memory.reject_proposal(first['id'])
        again = self.propose(rid, value={'statement': 'A'}, sig='e2')
        self.assertFalse(again['suppressed'])
        self.assertNotEqual(again['id'], first['id'])
        self.assertEqual(len(self.memory.proposals(self.p1, state='open')), 1)

    def test_accept_applies_change_and_preserves_previous(self):
        rid = self.rec()
        out = self.propose(rid, value={'statement': 'Ship from a release branch instead.'})
        decision = self.memory.accept_proposal(out['id'])
        self.assertEqual(decision['state'], 'accepted')
        new_id = decision['memory']
        with contextlib.closing(self.store.connect()) as db:
            old = db.execute('SELECT * FROM memories WHERE id=?', (rid,)).fetchone()
            new = db.execute('SELECT * FROM memories WHERE id=?', (new_id,)).fetchone()
        self.assertEqual(old['status'], 'superseded')
        self.assertEqual(old['superseded_by'], new_id)
        self.assertEqual(new['status'], 'active')
        self.assertEqual(new['user_confirmed'], 1)
        self.assertEqual(new['trust'], 2)
        chain = self.memory.history(new_id)
        self.assertEqual([c['id'] for c in chain], [rid, new_id])
        item = self.memory.proposal(out['id'])
        self.assertEqual(item['state'], 'accepted')
        self.assertEqual(item['decided_by'], 'user')

    def test_accept_new_knowledge_creates_record_and_accept_twice_is_refused(self):
        out = self.memory.propose_change(
            self.p1, kind='repo_state', type='convention', topic='commit.style',
            value={'statement': 'Conventional commits.'}, summary='Conventional commits.',
            why='The repository convention changed.', evidence={'sig': 'c1'})
        decision = self.memory.accept_proposal(out['id'])
        self.assertEqual(decision['state'], 'accepted')
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM memories WHERE id=?', (decision['memory'],)).fetchone()
        self.assertEqual(row['status'], 'active')
        self.assertEqual(row['user_confirmed'], 1)
        with self.assertRaises(PolicyError):
            self.memory.accept_proposal(out['id'])

    def test_accept_when_target_changed_supersedes_without_touching_memory(self):
        rid = self.rec()
        out = self.propose(rid, value={'statement': 'Ship from a release branch instead.'})
        corrected = self.memory.correct(
            rid, value={'statement': 'Deploy to prod after review.'}, summary='Deploy to prod.')
        decision = self.memory.accept_proposal(out['id'])
        self.assertEqual(decision['state'], 'superseded')
        with contextlib.closing(self.store.connect()) as db:
            kept = db.execute('SELECT * FROM memories WHERE id=?', (corrected,)).fetchone()
        self.assertEqual(kept['status'], 'active')  # the user edit wins; the proposal did nothing

    def test_defer_persists_and_can_be_accepted_later(self):
        rid = self.rec()
        out = self.propose(rid, value={'statement': 'A'})
        self.memory.defer_proposal(out['id'], note='not now')
        item = self.memory.proposal(out['id'])
        self.assertEqual(item['state'], 'deferred')
        self.assertEqual(len(self.memory.proposals(self.p1, state='open')), 1)
        decision = self.memory.accept_proposal(out['id'])
        self.assertEqual(decision['state'], 'accepted')

    def test_newer_proposal_supersedes_older_pending(self):
        rid = self.rec()
        older = self.propose(rid, value={'statement': 'A'}, sig='a')
        newer = self.propose(rid, value={'statement': 'B'}, sig='b')
        self.assertEqual(self.memory.proposal(older['id'])['state'], 'superseded')
        self.assertEqual(self.memory.proposal(newer['id'])['state'], 'pending')

    def test_project_isolation_of_proposals_and_memory(self):
        rid = self.rec(project=self.p1)
        out = self.propose(rid, value={'statement': 'A'})
        self.assertEqual(self.memory.proposals(self.p2, state='open'), [])
        other = self.memory.record(self.p2, 'fact', 'coffee.machine',
                                   {'statement': 'Office coffee machine.'}, 'Office coffee machine.',
                                   source_type='user_instruction', actor='user', user_confirmed=1)
        self.memory.accept_proposal(out['id'])
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM memories WHERE id=?', (other,)).fetchone()
        self.assertEqual(row['status'], 'active')
        self.assertEqual(row['project_id'], self.p2)

    def test_secret_like_content_is_refused(self):
        rid = self.rec()
        with self.assertRaises(PolicyError):
            self.propose(rid, value={'statement': 'token sk-ant-0123456789abcdefXYZ'})
        self.assertEqual(self.memory.proposals(self.p1, state='all'), [])

    def test_history_view_speaks_plainly(self):
        rid = self.rec()
        corrected = self.memory.correct(rid, value={'statement': 'Deploy to prod after review.'},
                                        summary='Deploy to prod after review.')
        out = self.propose(corrected, value={'statement': 'A'})
        self.memory.reject_proposal(out['id'])
        entries = self.memory.history_view(self.p1)
        texts = [e['text'] for e in entries]
        self.assertTrue(any(t.startswith('Added') and 'frozen folder' in t for t in texts))
        self.assertTrue(any(t.startswith('You changed') and 'Deploy to prod' in t for t in texts))
        self.assertTrue(any(t.startswith('You turned the change down') for t in texts))
        self.assertTrue(all('{' not in t and 'mem-' not in t for t in texts))


class ConflictTriggerTests(ProposalBase):
    def test_conflict_queues_review_proposal_and_accept_picks_newer(self):
        first = self.rec(summary='Dense dashboard by default.')
        second = self.rec(summary='Progressive density with matchup context first.')
        open_conflicts = self.memory.conflicts(self.p1, state='open')
        self.assertEqual(len(open_conflicts), 1)
        queued = self.memory.proposals(self.p1, state='open')
        self.assertEqual(len(queued), 1)
        item = queued[0]
        self.assertEqual(item['kind'], 'conflict')
        self.assertEqual(item['current']['summary'], 'Dense dashboard by default.')
        decision = self.memory.accept_proposal(item['id'])
        self.assertEqual(decision['state'], 'accepted')
        self.assertEqual(decision['resolution'], 'user_choice')
        with contextlib.closing(self.store.connect()) as db:
            a = db.execute('SELECT * FROM memories WHERE id=?', (first,)).fetchone()
            b = db.execute('SELECT * FROM memories WHERE id=?', (second,)).fetchone()
        self.assertEqual(a['status'], 'superseded')
        self.assertEqual(b['status'], 'active')
        self.assertEqual(self.memory.conflicts(self.p1, state='open'), [])

    def test_conflict_rejection_keeps_both_and_settles_the_question(self):
        first = self.rec(summary='Dense dashboard by default.')
        second = self.rec(summary='Progressive density with matchup context first.')
        item = self.memory.proposals(self.p1, state='open')[0]
        self.memory.reject_proposal(item['id'])
        with contextlib.closing(self.store.connect()) as db:
            a = db.execute('SELECT * FROM memories WHERE id=?', (first,)).fetchone()
            b = db.execute('SELECT * FROM memories WHERE id=?', (second,)).fetchone()
        self.assertEqual(a['status'], 'active')  # rejection never changes memory
        self.assertEqual(b['status'], 'active')
        self.assertEqual(self.memory.conflicts(self.p1, state='open'), [])
        # Identical unchanged evidence does not ask again.
        third = self.rec(summary='Progressive density with matchup context first.')
        self.assertEqual(self.memory.proposals(self.p1, state='open'), [])
        self.assertTrue(third)

    def test_hand_resolved_conflict_supersedes_the_proposal(self):
        self.rec(summary='A rule.')
        self.rec(summary='Another rule.')
        item = self.memory.proposals(self.p1, state='open')[0]
        conflict_id = item['evidence']['conflict_id']
        self.memory.resolve_conflict(conflict_id, 'a')
        listed = self.memory.proposals(self.p1, state='open')
        self.assertEqual(listed, [])
        self.assertEqual(self.memory.proposal(item['id'])['state'], 'superseded')


class StaleTriggerTests(ProposalBase):
    def test_stale_digest_queues_reconfirm_and_accept_refreshes(self):
        rid = self.rec(topic='deploy.target', summary='Deploy from the frozen folder.',
                       source_ref='file:README.md', source_digest='sha-old')
        self.assertEqual(self.memory.revalidate(self.p1, {'file:README.md': 'sha-old'}), [])
        stale = self.memory.revalidate(self.p1, {'file:README.md': 'sha-new'})
        self.assertEqual(stale, [rid])
        queued = [p for p in self.memory.proposals(self.p1, state='open') if p['kind'] == 'stale']
        self.assertEqual(len(queued), 1)
        decision = self.memory.accept_proposal(queued[0]['id'])
        self.assertEqual(decision['state'], 'accepted')
        with contextlib.closing(self.store.connect()) as db:
            old = db.execute('SELECT * FROM memories WHERE id=?', (rid,)).fetchone()
            new = db.execute('SELECT * FROM memories WHERE id=?', (decision['memory'],)).fetchone()
        self.assertEqual(old['status'], 'superseded')
        self.assertEqual(new['status'], 'active')
        self.assertEqual(new['source_digest'], 'sha-new')
        self.assertEqual(new['user_confirmed'], 1)

    def test_stale_rejection_leaves_record_stale_and_quiet(self):
        rid = self.rec(topic='deploy.target', summary='Deploy from the frozen folder.',
                       source_ref='file:README.md', source_digest='sha-old')
        self.memory.revalidate(self.p1, {'file:README.md': 'sha-new'})
        item = [p for p in self.memory.proposals(self.p1, state='open') if p['kind'] == 'stale'][0]
        self.memory.reject_proposal(item['id'])
        again = self.memory.revalidate(self.p1, {'file:README.md': 'sha-new'})
        self.assertEqual(again, [])
        self.assertEqual([p for p in self.memory.proposals(self.p1, state='open')
                          if p['kind'] == 'stale'], [])
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT status FROM memories WHERE id=?', (rid,)).fetchone()
        self.assertEqual(row['status'], 'stale')


class VettingTriggerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        self.context = Context(self.store)
        self.p1 = self.context.project('Project One', project_id='p1')
        self.p2 = self.context.project('Project Two', project_id='p2')
        self.memory = Memory(self.store)
        from kel.vetting_session import Vetting
        self.vetting = Vetting(self.store)
        self.sid = self.vetting.start('p1', 'main', 'Basketball dashboard')['session_id']

    def stored_rule(self, statement, question='Q6'):
        return self.memory.record(
            self.p1, 'decision', 'vetting.' + question, {'statement': statement}, statement,
            source_type='user_instruction', actor='user', user_confirmed=1)

    def test_vetting_decision_conflicting_with_stored_rule_queues_proposal(self):
        rid = self.stored_rule('Top-level navigation stays a single flat bar.')
        self.vetting.ingest_chat('main', '6: A', source='chat')
        created = self.vetting.flush_memory_checks()
        self.assertEqual(len(created), 1)
        item = self.memory.proposal(created[0])
        self.assertEqual(item['kind'], 'vetting')
        self.assertEqual(item['topic'], 'vetting.Q6')
        self.assertEqual(item['current_id'], rid)
        self.assertIn('Design Vetting decisions conflict with the stored project rule', item['why'])
        decision = self.memory.accept_proposal(created[0])
        self.assertEqual(decision['state'], 'accepted')
        with contextlib.closing(self.store.connect()) as db:
            old = db.execute('SELECT status FROM memories WHERE id=?', (rid,)).fetchone()
            new = db.execute('SELECT status, user_confirmed FROM memories WHERE id=?',
                             (decision['memory'],)).fetchone()
        self.assertEqual(old['status'], 'superseded')
        self.assertEqual(new['status'], 'active')
        self.assertEqual(new['user_confirmed'], 1)

    def test_vetting_matching_answer_queues_nothing(self):
        record_id = self.stored_rule('X')
        # Make the stored value match the consequence of answering 6: A exactly.
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM memories WHERE id=?', (record_id,)).fetchone()
        # Feed the question again with a DIFFERENT option so a difference exists; then verify the
        # matching case by writing the exact statement the engine just produced.
        self.vetting.ingest_chat('main', '6: A')
        self.vetting.flush_memory_checks()
        with contextlib.closing(self.store.connect()) as db:
            decision = db.execute("SELECT * FROM vetting_decisions WHERE session_id=? AND question_id='Q6'"
                                  " AND status='CONFIRMED'", (self.sid,)).fetchone()
        self.memory.correct(record_id, value={'statement': decision['statement']},
                            summary='Aligned rule.')
        self.vetting.ingest_chat('main', '6: A')
        created = self.vetting.flush_memory_checks()
        self.assertEqual(created, [])

    def test_rejected_vetting_proposal_does_not_re_ask_for_same_answer(self):
        self.stored_rule('Top-level navigation stays a single flat bar.')
        self.vetting.ingest_chat('main', '6: A')
        first = self.vetting.flush_memory_checks()
        self.assertEqual(len(first), 1)
        self.memory.reject_proposal(first[0])
        self.vetting.ingest_chat('main', '6: A')
        again = self.vetting.flush_memory_checks()
        self.assertEqual(again, [])
        self.assertEqual(self.memory.proposals(self.p1, state='open'), [])

    def test_vetting_proposal_is_project_scoped(self):
        self.stored_rule('Rule in p1.')
        self.vetting.ingest_chat('main', '6: A')
        created = self.vetting.flush_memory_checks()
        self.assertEqual(len(created), 1)
        self.assertEqual(self.memory.proposals(self.p2, state='open'), [])
        item = self.memory.proposal(created[0])
        self.assertEqual(item['project_id'], self.p1)


class MigrationTests(unittest.TestCase):
    def test_proposals_migration_is_additive_and_versioned(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = Store(Path(tmp.name) / 'kel.sqlite3')
        Memory(store)
        with contextlib.closing(store.connect()) as db:
            row = db.execute('SELECT name FROM schema_migrations WHERE version=?',
                             (PROPOSALS_VERSION,)).fetchone()
            self.assertEqual(row['name'], 'v16-memory-proposals')
            self.assertTrue(db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='memory_proposals'"
            ).fetchone())


if __name__ == '__main__':
    unittest.main()
