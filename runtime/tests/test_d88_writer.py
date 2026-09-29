"""D-88: the Writer role, the Editor (editorial lens), the slop scan and the page plan.

Design: docs/v2/design/WRITER_ANIMATOR_ROLES.md §1-2. No model runs here.
"""
import os
import tempfile
import unittest

from kel import pages, role_models, slop, staff, task_routing
from kel.assurance import lens
from kel.core import Store, validate_contract
from kel.packs import worker_brief
from kel.pod_review import lens_prompt, lenses_for


def writing(request):
    return {'request': request, 'compiler': 'test',
            'milestones': [{'id': 'document', 'objective': request, 'filename': 'result.md', 'depends_on': [],
                            'checks': [{'kind': 'min_chars', 'value': 5},
                                       {'kind': 'manual_review', 'rubric': 'Satisfies the request.'}]}]}


def coding(request, root='C:/nowhere'):
    return validate_contract({
        'request': request, 'kind': 'coding', 'root': root, 'test_command': ['x'],
        'milestones': [{'id': 'code', 'objective': request, 'filename': 'changes.md', 'depends_on': [],
                        'checks': [{'kind': 'min_chars', 'value': 40},
                                   {'kind': 'manual_review', 'rubric': 'Diff satisfies it.'}]}]})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        staff.ensure_schema(self.store)


class RoleRowTests(Base):
    def test_writer_and_animator_rows_start_on_their_d88_models(self):
        writer = role_models.setting(self.store, 'writer')
        animator = role_models.setting(self.store, 'animator')
        self.assertEqual((writer['mode'], writer['model']), ('PREFERRED', 'claude-fable-5-1'))
        self.assertEqual((animator['mode'], animator['model'], animator['reasoning']),
                         ('PREFERRED', 'claude-opus-5-5', 'high'))
        self.assertEqual(role_models.FALLBACKS['writer'], ('claude-opus-5-5',))
        rows = {row['role']: row for row in role_models.listing(self.store, set())['roles']}
        self.assertEqual(rows['writer']['label'], 'Writer')
        self.assertEqual(rows['animator']['purpose'], 'code')

    def test_the_animator_cannot_be_fixed_to_a_model_that_cannot_change_code(self):
        from kel.core import PolicyError
        with self.assertRaises(PolicyError):
            role_models.set_role(self.store, 'animator', 'FIXED', 'deepseek-flash')


class RoutingTests(Base):
    def test_writing_is_the_writers_class_and_motion_the_animators(self):
        self.assertEqual(task_routing.CLASS_ROLE['writing'], 'writer')
        self.assertEqual(task_routing.CLASS_ROLE['motion'], 'animator')
        self.assertEqual(task_routing.class_for_role('writer', 'code'), 'writing')
        self.assertEqual(task_routing.class_for_role('animator', 'code'), 'motion')

    def test_writing_is_staffed_as_the_writer_in_shadow_with_the_editor(self):
        contract = writing('Write a long detailed onboarding guide for new engineers covering accounts, '
                           'tooling, reviews, deployment and on-call, with a two-week checklist')
        contract['classification'] = {'task_class': 'writing'}
        record = staff.plan_job(self.store, contract)
        step = record['steps']['document']
        self.assertEqual((step['role'], step['task_class'], step['status']), ('writer', 'writing', 'shadow'))
        self.assertTrue(any('shadow' in reason for reason in record['reasons']))
        job = {'contract': dict(contract, staffing=record)}
        self.assertEqual(lenses_for(job, 'document'), ['editorial', 'requirements-coverage'])

    def test_a_motion_request_in_a_project_goes_to_the_animator(self):
        contract = coding('Animate the sidebar opening')
        contract['classification'] = {'task_class': 'motion'}
        record = staff.plan_job(self.store, contract)
        self.assertEqual(record['steps']['code']['role'], 'animator')
        self.assertEqual(record['steps']['code']['task_class'], 'motion')

    def test_floors_only_add_page_or_motion(self):
        self.assertEqual(pages.floor_class('build me a landing page for my podcast', 'coding'), 'page')
        self.assertEqual(pages.floor_class('make an html file of my top pitchers', 'writing'), 'page')
        self.assertEqual(pages.floor_class('export this table as html', 'writing'), 'writing')
        self.assertEqual(pages.floor_class('Make my about page feel warmer', 'design'), 'design')
        self.assertEqual(pages.floor_class('animate the sidebar', 'coding'), 'motion')
        self.assertEqual(pages.floor_class('fix the state transitions bug', 'coding'), 'coding')
        self.assertEqual(pages.floor_class('research landing page best practices', 'research'), 'research')


HUMAN = ("The Mets lost again on Tuesday. Kodai Senga threw 94 pitches over five innings and gave up "
         "two runs, both on a single mistake to Riley in the fourth. He looked fine. The bullpen did "
         "not: three walks in the seventh, and the game was gone before the stretch. ") * 4
SLOP = ("In today's fast-paced world, it's important to note that baseball is not just a game, but a "
        "rich tapestry of moments. Experts say pitching plays a crucial role. Let's dive into the "
        "vibrant, dynamic, and multifaceted landscape of the bullpen - a testament to resilience. ") * 4


class SlopTests(unittest.TestCase):
    def test_plain_writing_passes_and_slop_fails(self):
        clean = slop.scan(HUMAN)
        dirty = slop.scan(SLOP)
        self.assertFalse(clean['over'], clean)
        self.assertTrue(dirty['over'], dirty)
        kinds = {hit['kind'] for hit in dirty['hits']}
        self.assertTrue({'phrase', 'word', 'contrast', 'vague attribution'} <= kinds, kinds)
        self.assertIn('Slop score', slop.summary(dirty))

    def test_notes_and_code_are_not_scanned(self):
        text = HUMAN + '\n```\ndelve delve delve\n```\n' + slop.NOTES_MARKER + '\n' + SLOP
        self.assertFalse(slop.scan(text)['over'])

    def test_short_text_is_damped(self):
        self.assertFalse(slop.scan('We delve into it.')['over'])

    def test_nicks_banned_list_counts(self):
        banned = slop.banned_from_style('# Style\n- short\n## Banned words\n- "super excited"\n- synergy\n')
        self.assertEqual(banned, ['super excited', 'synergy'])
        result = slop.scan(HUMAN + ' We are super excited. ' * 20, banned=banned)
        self.assertTrue(any(hit['kind'] == 'banned' for hit in result['hits']))

    def test_the_check_runs_only_on_writer_steps(self):
        job = {'contract': {'milestones': [{'id': 'document', 'filename': 'result.md'}],
                            'staffing': {'schema': 1, 'steps': {'document': {'role': 'writer'}}}}}
        failed = slop.check(None, job, 'document', SLOP)
        self.assertEqual((failed['kind'], failed['verdict'], failed['failure']), ('slop', 'FAILED', 'slop'))
        self.assertEqual(slop.check(None, job, 'document', HUMAN)['verdict'], 'VERIFIED')
        job['contract']['staffing']['steps']['document']['role'] = 'builder'
        self.assertIsNone(slop.check(None, job, 'document', SLOP))


class EditorTests(unittest.TestCase):
    def test_the_editorial_lens_blocks_only_on_the_four_conditions(self):
        self.assertEqual(lens('editorial')['blocking_class'], 'blocker')
        prompt = lens_prompt(['editorial', 'requirements-coverage'])
        for words in ('unsupported factual claim', 'missing required content', 'slop over the limit',
                      'wrong reader or purpose', 'advisory', 'never rewrite'):
            self.assertIn(words, prompt)


COPY = """## meta
meta.title: Pitcher List Weekly
meta.description: The five starters worth a spot this week.
## hero
hero.title: Five arms for Week 12
hero.body: **Senga** is back, and his splitter is the best pitch on the slate.
hero.button: Read the list
hero.image.alt: Kodai Senga mid-delivery
<!-- notes -->
point: five starters
"""


class PageTests(Base):
    def test_a_page_is_copy_then_build_with_designer_only_when_needed(self):
        with tempfile.TemporaryDirectory() as root:
            plain = pages.page_contract(coding('Build a landing page for the podcast', root),
                                        'Build a landing page for the podcast')
            self.assertEqual([m['id'] for m in plain['milestones']], ['copy', 'design', 'code'])
            open(os.path.join(root, 'site.css'), 'w').close()  # an existing look
            styled = pages.page_contract(coding('Build a landing page', root), 'Build a landing page')
            self.assertEqual([m['id'] for m in styled['milestones']], ['copy', 'code'])
            self.assertEqual(styled['milestones'][1]['depends_on'], ['copy'])
            self.assertEqual(styled['milestones'][1]['copy_lock'], 'copy')
            moving = pages.page_contract(coding('Build an animated landing page', root),
                                         'Build an animated landing page')
            self.assertEqual([(m['id'], m['role']) for m in moving['milestones']],
                             [('copy', 'writer'), ('build', 'builder'), ('code', 'animator')])
            asked = pages.page_contract(coding('Design a landing page', root), 'Design a landing page')
            self.assertTrue(asked['page']['designer'])

    def test_the_page_plan_is_staffed_and_the_copy_runs_beside_the_design(self):
        with tempfile.TemporaryDirectory() as root:
            contract = pages.page_contract(coding('Build a landing page', root), 'Build a landing page')
            record = staff.plan_job(self.store, contract)
            roles = {mid: step['role'] for mid, step in record['steps'].items()}
            self.assertEqual(roles, {'copy': 'writer', 'design': 'designer', 'code': 'builder'})
            self.assertEqual(record['steps']['copy']['task_class'], 'writing')
            self.assertEqual(record['tier'], 'D3')
            self.assertEqual([s['name'] for s in record['parallel']['streams']], ['copy', 'design'])
            self.assertFalse(record['serial'])
            job = {'contract': dict(contract, staffing=record)}
            self.assertEqual(lenses_for(job, 'copy')[0], 'editorial')

    def test_the_engine_runs_page_text_steps_on_a_text_model(self):
        from kel.engine import code_step
        with tempfile.TemporaryDirectory() as root:
            contract = pages.page_contract(coding('Build a landing page', root), 'Build a landing page')
        job = {'contract': contract}
        specs = {m['id']: m for m in contract['milestones']}
        self.assertFalse(code_step(job, specs['copy']))
        self.assertTrue(code_step(job, specs['code']))

    def test_copy_fidelity_names_what_changed(self):
        page = ('<html><head><title>Pitcher List Weekly</title><meta name="description" '
                'content="The five starters worth a spot this week."></head><body><h1>Five arms for Week 12</h1>'
                '<p><b>Senga</b> is back, and his splitter is the best pitch on the slate.</p>'
                '<img alt="Kodai Senga mid-delivery"><a>Read the list</a><script>var x="nope"</script></body></html>')
        self.assertEqual(pages.copy_fidelity(COPY, [page])['verdict'], 'VERIFIED')
        changed = pages.copy_fidelity(COPY, [page.replace('Read the list', 'Read more')])
        self.assertEqual(changed['verdict'], 'FAILED')
        self.assertIn('hero.button', changed['summary'])
        self.assertEqual(pages.copy_fidelity(COPY, [])['verdict'], 'FAILED')

    def test_packs_give_each_role_its_brief(self):
        with tempfile.TemporaryDirectory() as root:
            contract = pages.page_contract(coding('Build a landing page', root), 'Build a landing page')
        specs = {m['id']: m for m in contract['milestones']}
        job = {'contract': contract}
        writer = worker_brief(self.store, job, specs['copy'], 'writer')
        self.assertIn("You are Kel's Writer", writer)
        self.assertIn('key: text', writer)
        self.assertIn('This is a revision', worker_brief(self.store, job, specs['copy'], 'writer', 2))
        self.assertIn('The copy is locked', worker_brief(self.store, job, specs['code'], 'builder'))
        self.assertIn('brief.md', worker_brief(self.store, job, specs['design'], 'designer'))
        self.assertEqual(worker_brief(self.store, {'contract': {}}, {'id': 'x'}, 'builder'), '')


if __name__ == '__main__':
    unittest.main()
