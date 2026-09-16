"""Design Vetting Sessions — verification matrix (docs/vetting/07_TEST_MATRIX.md).

Covered here (engine level, provider-free): rapid answering without an assistant turn,
out-of-order answers, the ingestion abstraction (typed-chat path through the ACP host and
service vs direct service calls produce identical state), custom answers, recommendation
rationale, explain / more options / challenge, uncertainty, skip, interruption resurfacing,
finish-early spec honesty, greybox pending + combination, pasted natural extraction,
confirmation of low-confidence matches, revisions, contradiction surfacing, restart.
"""
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from kel.core import Store
from kel.service import Service
from kel.vetting_session import Vetting, snapshot

RAPID = '1: C\n2: A\n3: B\n4: D\n5: B\n6: A\n7: A\n8: C\n9: D\n10: B'


class VettingBase(unittest.TestCase):
    def setUp(self):
        sys.stdout.reconfigure(errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        self.v = Vetting(self.store)
        self.sid = self.v.start('default', 'main', 'Basketball dashboard')['session_id']

    def tearDown(self):
        self.tmp.cleanup()

    def chat(self, text, source='chat'):
        return self.v.ingest_chat('main', text, source=source)

    def answered_progress(self, text):
        result = self.chat(text)
        return result, result.get('progress', {})


class RapidAnsweringTests(VettingBase):
    def test_rapid_answering_ten_plus_without_synthesis(self):
        for i, code in enumerate(('C', 'A', 'B', 'D', 'B', 'A', 'A', 'C', 'D', 'B'), start=1):
            result, progress = self.answered_progress('%d: %s' % (i, code))
            self.assertEqual(result['kind'], 'ingested', 'answer %d must ingest silently' % i)
            self.assertNotIn('Synthesis', result['message'])
            self.assertEqual(progress['answered'], i)
        result = self.chat('11: not sure')
        self.assertEqual(result['kind'], 'ingested')
        result = self.chat('12: skip')
        self.assertEqual(result['kind'], 'ingested')
        self.assertIn('12 of 12 recorded', result['message'])
        self.assertIn('process answers', result['message'])

    def test_out_of_order_answers(self):
        for text in ('8: C', '3: B', '11: D', '5: B'):
            result = self.chat(text)
            self.assertEqual(result['kind'], 'ingested')
        state = snapshot(self.store, self.sid)
        self.assertEqual(sorted(state['answers']), ['Q11', 'Q3', 'Q5', 'Q8'])
        self.assertEqual(len(state['unresolved']), 8)

    def test_multi_answer_single_message(self):
        result = self.chat(RAPID)
        self.assertEqual(result['kind'], 'ingested')
        self.assertEqual(result['progress']['answered'], 10)
        self.assertEqual(len(result['applied']), 10)

    def test_custom_answer_none_of_these(self):
        result = self.chat('2: none of these, keep the chart small and honest')
        self.assertEqual(result['kind'], 'ingested')
        state = snapshot(self.store, self.sid)
        answer = state['answers']['Q2']
        self.assertEqual(answer['status'], 'ANSWERED')
        self.assertIn('keep the chart small', answer['custom'])
        decision = next(d for d in state['decisions'] if d[0] == 'Q2')
        self.assertIn('Custom:', decision[1])

    def test_recommendation_tag_has_rationale_and_is_selective(self):
        message = self.v.start('default', 'main2', 'Second topic')['message']
        self.assertIn('Recommended', message)
        self.assertGreaterEqual(message.count('Recommended'), 1)
        option_lines = [line for line in message.splitlines() if line.strip()[:2].rstrip('.').isalpha()
                        and line.strip()[1:2] == '.']
        self.assertLess(message.count('Recommended'), len(option_lines) - 3,
                        'recommendations must be selective, not manufactured for every question')

    def test_unsure_and_skip_keep_state_and_do_not_block(self):
        self.chat('3: I am not sure, show examples')
        self.chat('4: skip for now')
        state = snapshot(self.store, self.sid)
        self.assertEqual(state['answers']['Q3']['status'], 'NEEDS_EXAMPLES')
        self.assertEqual(state['answers']['Q4']['status'], 'SKIPPED')
        self.assertNotIn('Q4', state['unresolved'])
        # progress continues to work after both
        result = self.chat('5: B')
        self.assertEqual(result['kind'], 'ingested')
        self.assertEqual(result['progress']['answered'], 1)  # only Q5 counts as answered

    def test_revision_keeps_history_and_supersedes_decision(self):
        self.chat('4: D')
        self.chat('4: change to A')
        state = snapshot(self.store, self.sid)
        self.assertEqual(state['answers']['Q4']['selected'], ['A'])
        revisions = [r for r in state['revisions'] if r[0] == 'Q4']
        self.assertEqual(len(revisions), 1)
        self.assertEqual(revisions[0][1], 'ANSWERED')
        decisions = [d for d in state['decisions'] if d[0] == 'Q4']
        self.assertEqual([d[2] for d in decisions], ['SUPERSEDED', 'CONFIRMED'])

class ContradictionTests(VettingBase):
    def _cause_conflict(self):
        self.chat('7: A')          # opens on a summary/overview
        self.chat('process answers')
        self.chat('19: B')         # dense command center, later
        panel = self.v.panel(conversation='main')
        self.assertTrue(panel['conflicts'], 'a minimal-vs-dense contradiction must be surfaced')
        return panel['conflicts'][0]['id']

    def test_contradiction_detected_and_surfaced(self):
        self._cause_conflict()
        state = snapshot(self.store, self.sid)
        self.assertEqual(state['conflicts'][0][2], 'OPEN')
        self.assertEqual(state['answers']['Q19']['status'], 'CONFLICTING')
        listing = self.chat('view open questions')['message']
        self.assertIn('CONFLICT', listing)

    def test_use_newer_supersedes_earlier_decision(self):
        conflict_id = self._cause_conflict()
        result = self.v.conflict_action(self.sid, conflict_id, 'use_newer')
        self.assertEqual(result['state'], 'RESOLVED')
        state = snapshot(self.store, self.sid)
        self.assertEqual(state['conflicts'][0][2], 'RESOLVED')
        self.assertEqual(state['answers']['Q19']['status'], 'ANSWERED')
        earlier = [d for d in state['decisions'] if d[0] == 'Q7']
        self.assertEqual([d[2] for d in earlier], ['SUPERSEDED'])

    def test_keep_earlier_parks_the_newer_answer(self):
        conflict_id = self._cause_conflict()
        self.v.conflict_action(self.sid, conflict_id, 'keep_earlier')
        state = snapshot(self.store, self.sid)
        self.assertEqual(state['conflicts'][0][2], 'RESOLVED')
        self.assertEqual(state['answers']['Q19']['status'], 'DEFERRED')
        later = [d for d in state['decisions'] if d[0] == 'Q7']
        self.assertEqual(later[0][2], 'CONFIRMED')

    def test_tradeoff_and_defer_leave_choice_open(self):
        conflict_id = self._cause_conflict()
        message = self.v.conflict_action(self.sid, conflict_id, 'show_tradeoff')['message']
        self.assertIn('Tradeoff', message)
        self.assertEqual(snapshot(self.store, self.sid)['conflicts'][0][2], 'OPEN')
        message = self.v.conflict_action(self.sid, conflict_id, 'resolve_later')['message']
        self.assertIn('stays in Open questions', message)
        self.assertEqual(snapshot(self.store, self.sid)['conflicts'][0][2], 'OPEN')


class InterruptionTests(VettingBase):
    def test_unrelated_question_leaves_state_and_prompts_resurface(self):
        self.chat('1: C')
        self.chat('2: A')
        before = snapshot(self.store, self.sid)
        result = self.chat('Is this technically possible with the Yahoo API?')
        self.assertEqual(result['kind'], 'none')
        self.assertEqual(snapshot(self.store, self.sid), before)
        resumed = self.chat('continue this vetting session')
        self.assertEqual(resumed['kind'], 'control')
        self.assertIn('Still waiting on', resumed['message'])
        self.assertIn('Q3', resumed['message'])


class FinishEarlyTests(VettingBase):
    def test_finish_early_is_honest_about_gaps(self):
        self.chat('1: C')
        result = self.chat('finish spec now')
        self.assertEqual(result['kind'], 'control')
        self.assertTrue(result.get('spec_id'))
        markdown = self.v.preview(self.sid)
        self.assertIn('## Open decisions', markdown)
        self.assertIn('Open — audience not decided yet.', markdown)
        self.assertIn('## Recommended assumptions', markdown)
        self.assertIn('Decide between options', markdown)         # resolved material is kept
        self.assertNotIn('**What is explicitly out of scope for v1?** —', markdown)

    def test_full_spec_after_every_question(self):
        for _ in range(6):
            panel = self.v.panel(conversation='main')
            pending = [q for q in panel['questions'] if not q.get('answer')]
            for question in pending:
                number = question['id'].lstrip('Q')
                if question['open']:
                    self.chat('%s: never hide what changed or why' % number)
                else:
                    self.chat('%s: %s' % (number, question['options'][0]['code']))
            result = self.chat('process answers')
            if 'Every question in this template' in result['message']:
                break
        result = self.chat('finish spec now')
        self.assertEqual(result['kind'], 'control')
        markdown = self.v.preview(self.sid)
        self.assertNotIn('Open — audience not decided yet.', markdown)
        self.assertIn('## Acceptance criteria', markdown)
        self.assertIn('Decision coverage:', markdown)
        self.assertIn('never hide what changed', markdown)        # the open answer is in the spec


class GreyboxTests(VettingBase):
    def _session_with_visual_batch(self):
        self.chat('7: A')
        self.chat('process answers')

    def test_greybox_directions_not_capped_at_three(self):
        self._session_with_visual_batch()
        payload = self.v.greybox(self.sid, 'Q19', action='design')
        self.assertGreaterEqual(len(payload['directions']), 4)
        svgs = {d['svg'] for d in payload['directions']}
        self.assertEqual(len(svgs), len(payload['directions']))

    def test_greybox_request_marks_awaiting_and_does_not_block(self):
        self._session_with_visual_batch()
        result = self.chat('19: make greyboxes, I will decide later')
        self.assertEqual(result['kind'], 'control')
        self.assertIn('greybox', result['message'])
        self.assertEqual(snapshot(self.store, self.sid)['answers']['Q19']['status'],
                         'AWAITING_VISUAL_SELECTION')
        result = self.chat('20: B')
        self.assertEqual(result['kind'], 'ingested')
        self.assertEqual(snapshot(self.store, self.sid)['answers']['Q20']['selected'], ['B'])

    def test_greybox_combination_and_base_choice(self):
        self._session_with_visual_batch()
        payload = self.v.greybox(self.sid, 'Q19', action='design')
        first = payload['directions'][0]['id']
        composite = self.v.greybox(self.sid, 'Q19', action='combine',
                                   note='Direction 4 -> base, Direction 2 -> header')
        self.assertIn('Composite', composite['composite']['name'])
        self.v.greybox(self.sid, 'Q19', action='feedback', feedback_kind='like', greybox_id=first)
        self.v.greybox(self.sid, 'Q19', action='feedback', feedback_kind='choose_base', greybox_id=first)
        state = snapshot(self.store, self.sid)
        self.assertEqual(state['answers']['Q19']['status'], 'ANSWERED')
        self.assertIn('Greybox direction chosen', state['answers']['Q19']['custom'])


class ProposalsTests(VettingBase):
    def test_low_confidence_match_proposes_then_confirms(self):
        result = self.chat('the sidebar keeps me oriented')
        self.assertEqual(result['kind'], 'proposal')
        self.assertIsNone(snapshot(self.store, self.sid)['answers'].get('Q6'))
        proposal = result['proposals'][0]
        self.assertEqual(proposal['question_id'], 'Q6')
        result = self.chat('yes')
        self.assertEqual(result['kind'], 'control')
        state = snapshot(self.store, self.sid)
        self.assertEqual(state['answers']['Q6']['selected'], [proposal['option']])


class RestartTests(VettingBase):
    def test_session_survives_restart(self):
        self.chat('1: C')
        self.chat('2: A')
        before = snapshot(self.store, self.sid)
        v2 = Vetting(self.store)
        panel = v2.panel(conversation='main')
        self.assertEqual(panel['session']['state'], 'ACTIVE')
        self.assertEqual(panel['progress']['handled'], 2)
        self.assertEqual(snapshot(self.store, self.sid), before)
        resumed = v2.ingest_chat('main', 'continue this vetting session')
        self.assertIn('Still waiting on', resumed['message'])


class TemplateTests(VettingBase):
    def test_template_is_varied_and_explained(self):
        bank = self.v.bank()
        self.assertGreaterEqual(len(bank['questions']), 25)
        counts = [len(q['options']) for q in bank['questions'] if not q.get('open')]
        self.assertGreaterEqual(max(counts), 5)
        self.assertTrue(any(count >= 6 for count in counts))
        self.assertTrue(any(q.get('open') for q in bank['questions']))
        self.assertGreaterEqual(len({q['section'] for q in bank['questions']}), 7)
        self.assertTrue(all(q.get('explain') and q.get('rationale')
                            for q in bank['questions'] if not q.get('open')))

def _update_text(event):
    return ((event.get('params') or {}).get('update') or {}).get('content', {}).get('text', '')


class VettingChatPathTests(unittest.TestCase):
    """Path A: the real typed-chat pipeline (ACP host -> engine service). Path B: direct call.

    The abstraction contract: answer understanding is a service, not a composer feature, so
    both paths must produce identical AnswerState, revisions, decisions and unresolved state.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = Service(self.tmp.name)
        self.cid = self.service.action('/api/conversation', {'project': 'default'})['id']
        owner = self
        self.posts = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _reply(self, value):
                raw = json.dumps(value).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _auth(self):
                if self.headers.get('Authorization') == 'Bearer token':
                    return True
                self.send_response(403)
                self.end_headers()
                return False

            def do_GET(self):
                if not self._auth():
                    return
                if urlparse(self.path).path == '/api/state':
                    self._reply(owner.service.state(owner.cid))
                    return
                self.send_response(404)
                self.end_headers()

            def do_POST(self):
                if not self._auth():
                    return
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.posts.append((urlparse(self.path).path, body))
                self._reply(owner.service.action(urlparse(self.path).path, body))

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        root = Path(self.tmp.name)
        (root / 'desktop-session.json').write_text(json.dumps(
            {'url': 'http://127.0.0.1:%d/' % self.server.server_port, 'token': 'token'}), encoding='utf-8')
        from kel.acp_host import ACPHost, ServiceClient
        self.events = []
        self.host = ACPHost(ServiceClient(root), self.events.append, .01)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.service.shutdown()
        self.tmp.cleanup()

    def _prompt(self, text):
        return self.host.dispatch('session/prompt', {'sessionId': 'kel:' + self.cid,
                                                     'prompt': [{'type': 'text', 'text': text}]})

    def test_typed_chat_and_direct_paths_produce_identical_state(self):
        result = self._prompt('start design vetting: Basketball dashboard')
        self.assertEqual(result['stopReason'], 'end_turn')
        batch = next(t for t in (_update_text(e) for e in self.events) if 'Design vetting' in t)
        self.assertIn('Q1', batch)
        self.assertIn('Recommended', batch)
        texts = ['1: C', '2: A', '3: B', '4: D', '5: B', '6: A', '7: A', '8: C', '9: D', '10: B',
                 '11: not sure', '12: skip']
        for text in texts:
            self._prompt(text)
        posted = [path for path, _ in self.posts]
        self.assertNotIn('/api/send', posted)            # no submission, no assistant turn
        recorded = [t for t in (_update_text(e) for e in self.events) if 'Recorded:' in t]
        self.assertEqual(len(recorded), len(texts))      # one acknowledged answer at a time
        assistant = [m['text'] for m in self.service.state(self.cid)['messages'] if m['role'] == 'assistant']
        self.assertTrue(assistant and 'Design vetting' in assistant[0])       # the batch is durable again
        recorded_rows = [text for text in assistant if text.startswith('Recorded:')]
        self.assertEqual(len(recorded_rows), len(texts))                      # one quiet line per answer
        for text in assistant:
            self.assertNotIn('Synthesis', text)                               # never a synthesis turn
        leftovers = [text for text in assistant
                     if not text.startswith('Recorded:') and 'Design vetting' not in text]
        self.assertEqual(leftovers, [])
        store_b = Store(Path(self.tmp.name) / 'b.sqlite3')
        vetting_b = Vetting(store_b)
        sid_b = vetting_b.start('default', 'main', 'Basketball dashboard')['session_id']
        for text in texts:
            vetting_b.ingest(sid_b, text, source='chat')
        panel = self.service.action('/api/vetting', {'action': 'panel', 'conversation': self.cid})
        snap_a = snapshot(self.service.store, panel['session']['id'])
        snap_b = snapshot(store_b, sid_b)
        self.assertEqual(snap_a, snap_b)

    def test_interruption_answers_normally_and_prompts_come_back(self):
        self._prompt('start design vetting: Another dashboard')
        self._prompt('1: C')
        result = self._prompt('What is a center of gravity?')
        self.assertEqual(result['stopReason'], 'end_turn')
        joined = ' '.join(_update_text(e) for e in self.events)
        self.assertIn('Still waiting on', joined)
        state = self.service.state(self.cid)
        answer_rows = [row for row in state['messages'] if row['role'] == 'user']
        self.assertTrue(any('center of gravity' in row['text'] for row in answer_rows))


# @@PART_4@@


class HelpTests(VettingBase):
    def test_explain_translates_and_keeps_question(self):
        message = self.chat('explain 2')['message']
        self.assertIn('In plain words', message)
        self.assertIn('Q2', message)
        self.assertIn('out of scope', message.lower())

    def test_more_options_are_new_directions(self):
        message = self.chat('more options for 2')['message']
        self.assertIn('more directions', message)
        self.assertIn('genuinely new', message)

    def test_challenge_has_three_parts_and_three_actions(self):
        self.chat('2: B')
        message = self.chat('challenge 2')['message']
        self.assertIn('Strongest downside', message)
        self.assertIn('Tradeoff', message)
        self.assertIn('Alternative worth weighing', message)
        self.assertIn('Keep decision', message)
        self.assertIn('Revise', message)
        self.assertIn('Defer', message)


class PanelContinuityTests(VettingBase):
    def test_panel_keeps_a_finished_session_reachable(self):
        self.chat('1: C')
        self.chat('finish spec now')
        panel = self.v.panel(conversation='main')
        self.assertIsNotNone(panel['session'], 'a finished session must stay reachable from the panel')
        self.assertEqual(panel['session']['state'], 'FINISHED')
        self.assertIsNotNone(panel['spec'])
        self.assertTrue(any(d for d in panel['decisions']), 'decisions stay visible after finishing')

    def test_panel_prefers_active_over_finished(self):
        self.chat('1: C')
        self.chat('finish spec now')
        second = self.v.start('default', 'main', 'Second design')['session_id']
        panel = self.v.panel(conversation='main')
        self.assertEqual(panel['session']['id'], second)
        self.assertEqual(panel['session']['state'], 'ACTIVE')


class PanelFallbackTests(VettingBase):
    def test_panel_falls_back_to_the_latest_session_elsewhere(self):
        self.chat('1: C')
        self.chat('finish spec now')
        panel = self.v.panel(conversation='some-other-conversation')
        self.assertIsNotNone(panel['session'])
        self.assertEqual(panel['session']['topic'], 'Basketball dashboard')
        self.assertTrue(panel['cross_conversation'])
        self.assertIsNotNone(panel['spec'])

    def test_panel_prefers_its_own_conversations_session(self):
        self.chat('1: C')
        self.chat('finish spec now')
        self.v.start('default', 'elsewhere', 'Second design')
        panel = self.v.panel(conversation='main')
        self.assertEqual(panel['session']['topic'], 'Basketball dashboard')
        self.assertFalse(panel['cross_conversation'])

    def test_panel_falls_back_to_an_active_session_anywhere(self):
        self.v.start('default', 'elsewhere', 'Second design')
        panel = self.v.panel(conversation='fresh-conversation')
        self.assertEqual(panel['session']['topic'], 'Second design')
        self.assertTrue(panel['cross_conversation'])
