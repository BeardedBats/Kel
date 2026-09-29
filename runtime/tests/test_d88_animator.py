"""D-88: the Animator's taste library, retrieval, rule proposals, and the motion capture checks.

Design: docs/v2/design/WRITER_ANIMATOR_ROLES.md §3. Every test works in a scratch Memory folder
(KEL_MEMORY_ROOT); nothing touches Nick's. No model runs. One test drives headless Chromium on a
tiny page when Playwright is installed here, and is skipped otherwise.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from kel import motion_capture, motion_checks, taste
from kel.packs import worker_brief


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ['KEL_MEMORY_ROOT'] = str(self.root / 'Memory')
        sheets = self.root / 'keyframes'
        sheets.mkdir()
        (sheets / '13-toasts.png').write_bytes(b'\x89PNG fake')
        os.environ['KEL_MOTION_KEYFRAMES'] = str(sheets)
        self.engine = self.root / 'Data' / 'engine'
        self.motion = self.root / 'Memory' / 'Taste' / 'Motion'


class LibraryTests(Base):
    def test_the_library_is_scaffolded_and_seeded_with_kels_15_moments(self):
        taste.ensure(self.engine)
        refs = sorted(p.name for p in (self.motion / 'refs').iterdir())
        self.assertEqual(len(refs), 15)
        self.assertTrue(all(name.startswith('kel-ui-') for name in refs))
        meta, note = taste.read_ref(self.motion / 'refs' / 'kel-ui-toasts' / 'ref.md')
        self.assertTrue(meta['loved'])
        self.assertEqual(meta['kind'], 'kel-ui')
        self.assertEqual(meta['measured']['overshoot_pct'], 1.1)
        self.assertIn('MOTION.md', note)
        self.assertTrue((self.motion / 'refs' / 'kel-ui-toasts' / 'strip.png').exists())
        for name in ('inbox', 'anti', 'proposals', 'rules.md', 'index.json', 'CHANGELOG.md', 'kit/kel-motion.js'):
            self.assertTrue((self.motion / name).exists(), name)
        self.assertIn('window.__motion', (self.motion / 'kit' / 'kel-motion.js').read_text(encoding='utf-8'))
        writing = self.root / 'Memory' / 'Taste' / 'Writing'
        self.assertTrue(writing.is_dir())
        self.assertEqual(list(writing.iterdir()), [])  # D-88.3: empty, and Kel never asks for samples
        self.assertIsNone(taste.writing_voice(self.engine))
        taste.ensure(self.engine)  # idempotent
        self.assertEqual(len(list((self.motion / 'refs').iterdir())), 15)

    def test_telling_kel_files_a_reference_with_the_note_verbatim(self):
        note = 'I like how the panel lands with no bounce, and the content arrives just after.'
        reply = taste.chat_intent(self.engine, 'Save to motion taste: https://linear.app/features/sheet ' + note)
        self.assertTrue(reply.startswith('Saved "'), reply)
        self.assertIn('to your motion taste', reply)
        entry = next(e for e in taste._entries(self.engine) if e['kind'] == 'link')
        self.assertEqual(entry['note'], note)
        self.assertEqual(entry['source'], 'https://linear.app/features/sheet')
        self.assertIn('sheet', entry['moments'])
        anti = taste.chat_intent(self.engine, "Save to motion taste as one I don't like: https://x.test/bouncy too bouncy")
        self.assertIn("as a motion you don't like", anti)
        self.assertTrue(any(e['anti'] for e in taste._entries(self.engine)))
        self.assertIsNone(taste.chat_intent(self.engine, 'add motion to the sidebar: make it slide'))
        self.assertIsNone(taste.chat_intent(self.engine, 'write a post about motion'))
        gone = taste.chat_intent(self.engine, 'Forget the linear one from my motion taste')
        self.assertIn('Removed', gone)
        self.assertFalse(any(e['source'] == 'https://linear.app/features/sheet' for e in taste._entries(self.engine)))

    def test_private_references_never_offer_their_media(self):
        clip = self.root / 'screen.gif'
        clip.write_bytes(b'GIF89a')
        taste.chat_intent(self.engine, 'Save to motion taste: keep this one private. the list reorders softly',
                          {'files': [{'path': str(clip)}]})
        entry = next(e for e in taste._entries(self.engine) if e['kind'] == 'gif')
        self.assertTrue(entry['local_only'])
        context = taste.motion_context(self.engine, 'reorder the list softly')
        self.assertNotIn(str(Path(entry['folder']) / 'strip.png'), context)

    def test_the_inbox_is_filed_with_its_same_name_note(self):
        taste.ensure(self.engine)
        inbox = self.motion / 'inbox'
        (inbox / 'stripe-checkout.url').write_text('[InternetShortcut]\nURL=https://stripe.com/checkout\n')
        (inbox / 'stripe-checkout.txt').write_text('The button press is tiny and crisp.')
        (inbox / 'idea.md').write_text('Toasts should rise, never drop. https://example.test/toast')
        done = taste.scan_inbox(self.engine)
        self.assertEqual(len(done), 2)
        self.assertEqual(list(inbox.iterdir()), [])
        stripe = next(e for e in done if e['source'] == 'https://stripe.com/checkout')
        self.assertEqual(stripe['note'], 'The button press is tiny and crisp.')
        self.assertIn('crisp', stripe['feel'])

    def test_retrieval_prefers_moment_type_then_feel_then_loved(self):
        taste.add_reference(self.engine, note='Cards arrive one after another, 30 ms apart, calm.',
                            title='Pricing cards stagger', moments=['stagger', 'enter'], loved=True)
        taste.add_reference(self.engine, note='A spinner that never stops.', title='Busy spinner',
                            moments=['loader'], anti=True)
        taste.add_reference(self.engine, note='Cards bounce in hard.', title='Bouncy cards',
                            moments=['stagger'], anti=True)
        refs, anti = taste.retrieve(self.engine, 'make the pricing cards arrive with a stagger')
        self.assertEqual(refs[0]['title'], 'Pricing cards stagger')
        self.assertLessEqual(len(refs), 5)
        self.assertEqual(anti[0]['title'], 'Bouncy cards')
        context = taste.motion_context(self.engine, 'make the pricing cards arrive with a stagger')
        self.assertIn("Nick's motion rules", context)
        self.assertIn('Pricing cards stagger', context)
        self.assertIn('Not this:', context)
        self.assertIn('kel-motion.js', context)

    def test_quoted_rules_are_added_and_contradictions_wait_for_nick(self):
        taste.ensure(self.engine)
        for i in range(4):
            taste.add_reference(self.engine, note='Reference %d is nice.' % i, title='Ref %d' % i)
        taste.add_reference(self.engine, note='Never loop the logo. The panel is great.', title='Ref 4')
        rules = (self.motion / 'rules.md').read_text(encoding='utf-8')
        self.assertIn('"Never loop the logo." (ref: ', rules)
        self.assertIn('added to your motion rules', (self.motion / 'CHANGELOG.md').read_text(encoding='utf-8'))
        result = taste.add_reference(self.engine, note='Always blur the entrance a lot.', title='Blurry')
        forced = taste.rules_from_notes(self.engine, force=True)
        self.assertEqual(forced['added'], ['Always blur the entrance a lot.'])  # no clash: blur rule is not negative
        taste.add_reference(self.engine, note='Always loop the hero animation.', title='Looping hero')
        forced = taste.rules_from_notes(self.engine, force=True)
        self.assertEqual(forced['proposed'], ['Always loop the hero animation.'])
        self.assertEqual(len(taste.pending_proposals(self.engine)), 1)
        self.assertTrue(result)

    def test_writing_voice_is_saved_only_when_nick_brings_it(self):
        reply = taste.chat_intent(self.engine, 'Save to my writing voice: Short sentences. The point first.')
        self.assertEqual(reply, 'Saved to your writing voice.')
        voice = taste.writing_voice(self.engine)
        self.assertIn('The point first.', voice['samples'][0]['text'])

    def test_the_animator_prompt_carries_the_craft_and_the_taste(self):
        job = {'contract': {'request': 'Animate the pricing cards', 'kind': 'coding'}}
        store = type('S', (), {'root': self.engine})()
        brief = worker_brief(store, job, {'id': 'code'}, 'animator')
        self.assertIn("You are Kel's Animator", brief)
        self.assertIn("Nick's motion taste", brief)
        self.assertIn('window.__motion', brief)


def spring_frames(overshoot=0.6, settle=450, extra=None, window=900):
    """A box travelling 100 px on x with a small overshoot, settling at `settle` ms."""
    frames = []
    t = 0.0
    while t <= window:
        if t >= settle:
            x = 100.0
        else:
            p = t / settle
            x = 100.0 * min(1.0 + overshoot / 100.0, p * 1.6) if p < 0.7 else 100.0 + overshoot * (1 - p) / 0.3
        frame = {'t': round(t, 1), 'boxes': {'card': {'x': x, 'y': 10, 'w': 50, 'h': 20}}, 'text': {'card': 'Pro'},
                 'style': {'card': {'opacity': min(1.0, t / 200.0), 'transform': 'm', 'filter': 'none',
                                    'clipPath': 'none', 'layout': {'width': '50px'}}}}
        if extra:
            extra(frame)
        frames.append(frame)
        t += 1000.0 / 60
    return frames


class MotionCheckTests(unittest.TestCase):
    def test_a_good_spring_passes_every_hard_check(self):
        result = motion_checks.check_moment(spring_frames(), spring_frames(overshoot=0, settle=0))
        self.assertEqual(result['failures'], [], result['checks'])
        self.assertLessEqual(result['metrics']['overshoot_pct'], 1.0)
        self.assertGreater(result['metrics']['overshoot_pct'], 0.1)
        self.assertIn('opacity', result['metrics']['properties'])

    def test_each_hard_rule_catches_its_problem(self):
        def shift(frame):
            if frame['t'] > 700:
                frame['boxes']['card']['y'] = 14
        self.assertIn('H1', ' '.join(motion_checks.check_moment(spring_frames(extra=shift))['failures']))

        def swap(frame):
            frame['style']['card']['opacity'] = 0.0 if frame['t'] < 100 else 1.0
        self.assertIn('H2', ' '.join(motion_checks.check_moment(spring_frames(extra=swap))['failures']))
        self.assertIn('H3', ' '.join(motion_checks.check_moment(spring_frames(overshoot=8))['failures']))

        def width(frame):
            frame['style']['card']['layout'] = {'width': '%dpx' % int(frame['t'] // 100)}
        self.assertIn('H6', ' '.join(motion_checks.check_moment(spring_frames(extra=width))['failures']))

        def loop(frame):
            frame['style']['card']['transform'] = 'rotate(%d)' % int(frame['t'])
        looped = motion_checks.check_moment(spring_frames(extra=loop, window=3000))
        self.assertIn('H7', ' '.join(looped['failures']))
        moving = motion_checks.check_moment(spring_frames(), reduced_frames=spring_frames())
        self.assertIn('H5', ' '.join(moving['failures']))
        self.assertIsNone(moving['checks']['H8']['ok'])

    def test_the_step_check_reads_the_cached_capture(self):
        store = type('S', (), {'root': Path(tempfile.mkdtemp())})()
        job = {'id': 'j1', 'milestones': {'code': {'artifact': {'sha256': 'ab' * 32}}},
               'contract': {'kind': 'coding', 'milestones': [{'id': 'code'}],
                            'staffing': {'schema': 1, 'steps': {'code': {'role': 'animator'}}}}}
        self.assertEqual(motion_capture.check(store, job, 'code')['verdict'], 'VERIFIED')  # not captured: advisory
        cache = motion_capture._cache(store, 'j1', 'code', 'ab' * 32)
        cache.parent.mkdir(parents=True)
        bad = motion_checks.check_moment(spring_frames(overshoot=8))
        cache.write_text(json.dumps({'status': 'captured', 'pages': [{'page': 'index.html', 'moments': {
            'cards-enter': {'metrics': bad['metrics'], 'checks': bad['checks'], 'failures': bad['failures']}}}]}))
        failed = motion_capture.check(store, job, 'code')
        self.assertEqual((failed['verdict'], failed['failure']), ('FAILED', 'motion'))
        self.assertIn('cards-enter: H3', failed['findings'][0])
        job['contract']['staffing']['steps']['code']['role'] = 'builder'
        self.assertIsNone(motion_capture.check(store, job, 'code'))
        self.assertFalse(motion_capture.capture_pending(store, job, 'code'))


PAGE = """<!doctype html><html><head><style>.card{width:120px;height:60px;background:#345;opacity:0}</style></head>
<body><div class="card">Pro</div><script>%s</script><script>
const card = document.querySelector('.card');
window.__motion.moments['card-enter'] = {targets: ['.card'], run: () => {
  KelMotion.tween(0, 1, 200, 'out', (v) => { card.style.opacity = v; });
  if (KelMotion.reduced) return;
  return KelMotion.spring(24, 0, 'snappy', (v) => { card.style.transform = 'translateY(' + v + 'px)'; });
}};
</script></body></html>"""


@unittest.skipUnless(motion_capture.available()[0], 'Playwright is not installed here')
class LiveCaptureTests(unittest.TestCase):
    def test_a_real_page_is_captured_and_checked(self):
        kit = (Path(taste.__file__).parent / 'motion_kit' / 'kel-motion.js').read_text(encoding='utf-8')
        with tempfile.TemporaryDirectory() as scratch:
            page = Path(scratch) / 'index.html'
            page.write_text(PAGE % kit, encoding='utf-8')
            self.assertEqual(motion_capture.motion_pages(scratch), [page])
            result = motion_capture.capture_page(page, Path(scratch) / 'strips')
            if result.get('error'):
                self.skipTest(result['error'])
            moment = result['moments']['card-enter']
            self.assertEqual(moment['failures'], [], moment['checks'])
            self.assertTrue(moment['checks']['H5']['ok'])
            self.assertGreater(moment['metrics']['settle_ms'], 150)
            self.assertLessEqual(moment['metrics']['overshoot_pct'], 1.5)


if __name__ == '__main__':
    unittest.main()
