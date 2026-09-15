"""Measure representative context packets: V1.2 legacy handoff vs V1.3 composer (C4 evidence).

Run from runtime/:  python tools/measure_context.py
Records, per fixture: legacy handoff packet size (chars) and the V1.3 composer packet size,
its estimated tokens, the source mix, and recorded omissions. No claims without measurements.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kel.composer import Composer        # noqa: E402
from kel.context import Context          # noqa: E402
from kel.core import Store               # noqa: E402
from kel.memory import Memory            # noqa: E402
from kel.projectmap import ProjectMap    # noqa: E402

FIXTURES = ('document', 'coding', 'research')


def build_fixture(root, kind):
    store = Store(str(root / 'data'))
    context = Context(store)
    project = root / 'proj'
    project.mkdir()
    (project / 'main.py').write_text('print(1)\n', encoding='utf-8')
    (project / 'tests').mkdir()
    (project / 'tests' / 'test_smoke.py').write_text(
        'def test_ok():\n    assert True\n', encoding='utf-8')
    pid = context.project('Fixture', root=str(project), project_id='fix')
    cid = context.conversation('fix')
    memory = Memory(store)
    memory.record(pid, 'decision', 'release.channel',
                  dict(statement='Ship from the frozen release folder only.'),
                  'Releases ship from the frozen folder only.',
                  source_type='user_instruction', actor='user', user_confirmed=1)
    memory.record(pid, 'fact', 'test.command', dict(command='python -m pytest tests/ -q'),
                  'Tests run with pytest.', source_type='repo_inspection', source_ref='tests/')
    for i in range(12):
        store.add_message('turn %d: earlier discussion about the %s work.' % (i, kind),
                          role='user' if i % 2 else 'assistant', conversation=cid)
    maps = ProjectMap(store)
    maps.refresh(pid, reason='measure')
    return store, context, pid, cid, Composer(store, memory, maps)


def main():
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for kind in FIXTURES:
            root = Path(tmp) / kind
            root.mkdir()
            store, context, pid, cid, composer = build_fixture(root, kind)
            request = 'Continue the %s work using the recorded decisions.' % kind
            legacy = context.handoff(cid, request)
            packet = composer.build(pid, request, conversation_id=cid, purpose=kind)
            results.append({
                'fixture': kind,
                'legacy_handoff_chars': len(json.dumps(legacy)),
                'packet_chars': packet['size']['chars'],
                'packet_tokens_est': packet['size']['tokens_est'],
                'sources': [{'kind': s['kind'], 'chars': s['chars']} for s in packet['sources']],
                'omitted': packet['omitted'],
            })
    print(json.dumps({'schema': 1, 'measurements': results}, indent=2))


if __name__ == '__main__':
    main()
