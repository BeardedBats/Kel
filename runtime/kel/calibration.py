"""The calibration harness (Routing 2 §5.7, workforce-os doc 10 §7) — advisory only.

A small suite of real-shaped task prompts per task class, each with deterministic checks, run against
chosen models; the harness measures latency, tokens and cost through the same normaliser as live work
(`kel.usage`) and records pass/fail per check, with an optional judge (a callable, e.g. another
model) whose score is kept beside — never instead of — the checks. Results go to `calibration_runs`
and are shown next to the ranking. They never move it: quality floors stay with real, reviewed
outcomes (≥ 3 per task class per model, `routing_evidence`), and no black-box learned routing.

A live run spends Nick's quota or money, so nothing here starts one on its own: `python -m
kel.calibration --data <dir> --fixture` runs the suite on deterministic fixture models (no provider
is called). A live campaign is Nick's call (ROUTING_2.md "Needs Nick").
"""
import argparse
import contextlib
import json
import re
import statistics
import time

from .core import Store, encode, uid

MIGRATION_VERSION = 37  # 36 is the live workforce (staff.MIGRATION_VERSION)
MIGRATION_NAME = 'v2-routing-2'

DDL = (
    'CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, name TEXT NOT NULL, '
    'applied REAL NOT NULL, note TEXT)',
    'CREATE TABLE IF NOT EXISTS calibration_runs(id TEXT PRIMARY KEY, campaign TEXT NOT NULL, at REAL NOT NULL, '
    'task_id TEXT NOT NULL, task_class TEXT NOT NULL, model TEXT NOT NULL, live INTEGER NOT NULL, '
    'passed INTEGER NOT NULL, checks TEXT NOT NULL, wall_ms INTEGER, processed INTEGER, cost_usd REAL, '
    'cost_basis TEXT, judge REAL, error TEXT)',
    'CREATE INDEX IF NOT EXISTS calibration_runs_by_model ON calibration_runs(task_class, model, at)',
    # the budget governor's raised classes (kel.budget) share this migration
    'CREATE TABLE IF NOT EXISTS job_budgets(job_id TEXT PRIMARY KEY, budget_class TEXT NOT NULL, '
    'raised_at REAL NOT NULL, actor TEXT NOT NULL)',
)

# Real-shaped prompts per task class; every check is deterministic and says what it proves.
SUITE = (
    {'id': 'utility-sort', 'task_class': 'utility',
     'prompt': 'Sort these words alphabetically, one per line, nothing else: pear, apple, mango',
     'checks': [{'kind': 'regex', 'value': r'(?s)apple.*mango.*pear'}, {'kind': 'max_chars', 'value': 200}]},
    {'id': 'utility-json', 'task_class': 'utility',
     'prompt': 'Return only JSON: {"name": <the city>, "country": <its country>} for Lisbon.',
     'checks': [{'kind': 'json_keys', 'value': ['name', 'country']}, {'kind': 'contains', 'value': 'Portugal'}]},
    {'id': 'writing-note', 'task_class': 'writing',
     'prompt': 'Write a three-sentence thank-you note to a neighbour who watered my plants. Mention the tomatoes.',
     'checks': [{'kind': 'contains', 'value': 'tomato'}, {'kind': 'min_chars', 'value': 80},
                {'kind': 'max_chars', 'value': 800}]},
    {'id': 'planning-steps', 'task_class': 'planning',
     'prompt': 'List exactly three numbered steps to back up a folder to an external drive. No preamble.',
     'checks': [{'kind': 'regex', 'value': r'(?m)^\s*1[.)]'}, {'kind': 'regex', 'value': r'(?m)^\s*3[.)]'},
                {'kind': 'not_regex', 'value': r'(?m)^\s*4[.)]'}]},
    {'id': 'coding-function', 'task_class': 'coding',
     'prompt': 'Write a Python function multiply(a, b) that returns a * b. Reply with only the code.',
     'checks': [{'kind': 'regex', 'value': r'def\s+multiply\s*\(\s*a\s*,\s*b\s*\)'},
                {'kind': 'contains', 'value': 'return'}]},
    {'id': 'review-find-bug', 'task_class': 'review',
     'prompt': ('Review this function and say VERIFIED or FAILED with one finding: '
                'def add(a, b):\n    return a - b'),
     'checks': [{'kind': 'contains', 'value': 'FAILED'}]},
    {'id': 'design-states', 'task_class': 'design',
     'prompt': 'Name the three states a file upload button needs besides its idle state, one per line.',
     'checks': [{'kind': 'min_lines', 'value': 3}, {'kind': 'regex', 'value': r'(?i)error|fail'}]},
)


def ensure_schema(store):
    with contextlib.closing(store.connect()) as db:
        for statement in DDL:
            db.execute(statement)
        db.execute('INSERT OR IGNORE INTO schema_migrations(version,name,applied,note) VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                    'calibration runs (advisory) and raised budget classes (Routing 2)'))
    return True


def check(text, item):
    """(passed, what it proves) for one deterministic check on one answer."""
    kind, value = item['kind'], item.get('value')
    text = text or ''
    if kind == 'contains':
        return value.lower() in text.lower(), 'mentions %s' % value
    if kind == 'regex':
        return bool(re.search(value, text)), 'has the required shape'
    if kind == 'not_regex':
        return not re.search(value, text), 'has nothing extra'
    if kind == 'min_chars':
        return len(text.strip()) >= value, 'is at least %d characters' % value
    if kind == 'max_chars':
        return len(text.strip()) <= value, 'is at most %d characters' % value
    if kind == 'min_lines':
        return len([l for l in text.splitlines() if l.strip()]) >= value, 'has at least %d lines' % value
    if kind == 'json_keys':
        try:
            start, end = text.find('{'), text.rfind('}')
            data = json.loads(text[start:end + 1])
            return isinstance(data, dict) and all(k in data for k in value), 'is JSON with %s' % ', '.join(value)
        except (ValueError, TypeError):
            return False, 'is JSON with %s' % ', '.join(value)
    raise ValueError('Unknown calibration check: %s' % kind)


def run(store, models, *, suite=SUITE, task_classes=None, judge=None, live=False, campaign=None):
    """Run the suite against `models` ({catalog model id: adapter with execute(prompt)}).

    Returns the campaign id. `live` must be True for real models (recorded, so fixture numbers are
    never mistaken for measurements); a fixture run records `live=0`."""
    from .usage import normalize
    ensure_schema(store)
    campaign = campaign or uid()
    for task in suite:
        if task_classes and task['task_class'] not in task_classes:
            continue
        for model_id, adapter in models.items():
            started = time.monotonic()
            try:
                result = adapter.execute(task['prompt'])
            except Exception as exc:
                result = {'outcome': 'FAILED', 'error': type(exc).__name__}
            wall = int((time.monotonic() - started) * 1000)
            text = result.get('text') if result.get('outcome') == 'SUCCESS' else ''
            outcomes = [dict(zip(('passed', 'proves'), check(text, item)), kind=item['kind'])
                        for item in task['checks']]
            passed = result.get('outcome') == 'SUCCESS' and all(o['passed'] for o in outcomes)
            measured = normalize(result, model=model_id)
            score = None
            if judge is not None and text:
                try:
                    score = float(judge(task, text))
                except Exception:
                    score = None
            with store.transaction() as db:
                db.execute('INSERT INTO calibration_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                           (uid(), campaign, time.time(), task['id'], task['task_class'], model_id,
                            1 if live else 0, 1 if passed else 0, encode(outcomes),
                            result.get('wall_ms') if isinstance(result.get('wall_ms'), int) else wall,
                            measured['processed'], measured['cost_usd'], measured['cost_basis'], score,
                            None if result.get('outcome') == 'SUCCESS' else str(result.get('error') or '')[:300]))
    return campaign


def summary(store, *, live_only=False):
    """{task_class: {model: {runs, passed, pass_rate, median_ms, avg_processed, live, last_at}}}."""
    ensure_schema(store)
    with contextlib.closing(store.connect()) as db:
        rows = [dict(r) for r in db.execute('SELECT * FROM calibration_runs' +
                                            (' WHERE live=1' if live_only else '') + ' ORDER BY at')]
    out = {}
    for row in rows:
        slot = out.setdefault(row['task_class'], {}).setdefault(row['model'], {
            'runs': 0, 'passed': 0, 'walls': [], 'tokens': [], 'live': False, 'last_at': None})
        slot['runs'] += 1
        slot['passed'] += row['passed']
        if row['wall_ms'] is not None:
            slot['walls'].append(row['wall_ms'])
        if row['processed'] is not None:
            slot['tokens'].append(row['processed'])
        slot['live'] = slot['live'] or bool(row['live'])
        slot['last_at'] = row['at']
    for models in out.values():
        for slot in models.values():
            walls, tokens = slot.pop('walls'), slot.pop('tokens')
            slot['pass_rate'] = round(slot['passed'] / slot['runs'], 3) if slot['runs'] else None
            slot['median_ms'] = int(statistics.median(walls)) if walls else None
            slot['avg_processed'] = int(sum(tokens) / len(tokens)) if tokens else None
    return out


class FixtureModel:
    """A deterministic stand-in (never a real model): answers each suite prompt from a table."""

    ANSWERS = {'utility-sort': 'apple\nmango\npear', 'utility-json': '{"name": "Lisbon", "country": "Portugal"}',
               'writing-note': ('Thank you so much for watering my plants while I was away. The tomatoes look '
                                'wonderful. I owe you a basket of them.'),
               'planning-steps': '1. Plug in the drive.\n2. Copy the folder.\n3. Check the copy opens.',
               'coding-function': 'def multiply(a, b):\n    return a * b',
               'review-find-bug': 'FAILED: add subtracts instead of adding.',
               'design-states': 'Uploading\nDone\nError'}

    def __init__(self, name='fixture', wrong=()):
        self.name, self.wrong = name, set(wrong)

    def execute(self, prompt, **kwargs):
        task = next(t for t in SUITE if t['prompt'] == prompt)
        text = 'I cannot help with that.' if task['id'] in self.wrong else self.ANSWERS[task['id']]
        return {'outcome': 'SUCCESS', 'text': text, 'fixture': True,
                'usage': {'input_tokens': len(prompt.split()), 'output_tokens': len(text.split())},
                'wall_ms': 5}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Kel calibration harness (advisory; fixture runs only here).')
    parser.add_argument('--data', required=True)
    parser.add_argument('--fixture', action='store_true', help='run the suite on deterministic fixture models')
    args = parser.parse_args(argv)
    if not args.fixture:
        parser.error('Only --fixture runs start from here; a live campaign spends quota and is Nick\'s call.')
    store = Store(args.data)
    campaign = run(store, {'fixture-good': FixtureModel(), 'fixture-weak': FixtureModel(wrong={'utility-json'})})
    print(json.dumps({'campaign': campaign, 'summary': summary(store)}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
