"""CP-10a stage 0 (D-77): a read-only inventory of every chat across the two chat stores.

    python -m kel.chatstore inventory --data <Data or engine folder> [--store <donor store folder>]
                                      [--json <file>] [--markdown <file>] [--show-text]

Both databases are opened read-only (SQLite `mode=ro`); nothing is written anywhere except the
report files asked for. Run it on a copy of Data.

For every app chat (a row in the donor host's `conversations`) it records every link (D the ACP
host's session record, C the desktop's map, E the donor row's `extra.kel_conversation_id`, and the
project binding), the donor row counts, the engine message count, one class, and a per-row plan:
`same` (matched by the desktop's reconcile rule: role, then the text or a text prefix followed by a
blank line, each segment consumed once in order), `donor-only` (to import), `partial` (a donor row
some of whose words have no engine twin), or `engine-only`. Message text is left out unless
`--show-text` is given. The command exits 2 when a chat does not fit a known class.

The link a chat uses for its class is the first of D, C, E — where Kel answers. A chat whose links
disagree is also listed as a conflict, with the outcome the stage 1 rule gives it.
"""
import argparse
import contextlib
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys

from .chat_links import legacy_map, resolve, session_records


CLASSES = {
    'linked': 'Linked, and both stores have messages',
    'linked-engine-only': "Linked; only Kel's store has messages",
    'linked-donor-only': "Linked; only the app's store has messages",
    'linked-empty': 'Linked; both sides are empty',
    'dead-empty': "Linked to a Kel conversation that no longer exists; the chat is empty",
    'dead-donor-words': "Linked to a Kel conversation that no longer exists; the chat has words only the app's store holds",
    'unlinked-donor-words': "Not linked; the chat has words only the app's store holds",
    'unlinked-empty': 'Not linked; the chat is empty',
}


def _open(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)


def _paths(data, store=None):
    data = Path(data)
    engine = data if (data / 'kel.sqlite3').exists() else data / 'engine'
    donor = Path(store) if store else (engine.parent / 'store')
    donor_db = donor if donor.suffix == '.db' else donor / 'aionui-backend.db'
    if not (engine / 'kel.sqlite3').exists():
        raise SystemExit('No engine database (kel.sqlite3) under ' + str(data))
    if not donor_db.exists():
        raise SystemExit('No donor database (aionui-backend.db) at ' + str(donor_db))
    return engine, donor_db


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _text(content):
    try:
        value = json.loads(content) if isinstance(content, str) else content
    except ValueError:
        return str(content or '')
    if isinstance(value, dict):
        return str(value.get('content') or '')
    return str(value or '')


def plan_rows(engine_messages, donor_rows):
    """The per-row plan, using the desktop's reconcile rule (`reconcileHistory.recoverHistory`)."""
    available = []
    for row in donor_rows:
        if row['type'] != 'text':
            continue
        text = _text(row['content']).strip()
        available.append({'row': row, 'position': row['position'], 'text': text, 'matched': 0})
    plans = []
    for message in engine_messages:
        position = 'right' if message['role'] == 'user' else 'left'
        text = (message['text'] or '').strip()
        match = next((entry for entry in available if entry['position'] == position and
                      (entry['text'] == text or entry['text'].startswith(text + '\n\n'))), None)
        if match:
            match['text'] = match['text'][len(text):].lstrip()
            match['matched'] += 1
            plans.append({'store': 'engine', 'seq': message['seq'], 'role': message['role'], 'plan': 'same',
                          'donor_msg_id': match['row']['id'], '_text': message['text']})
        else:
            plans.append({'store': 'engine', 'seq': message['seq'], 'role': message['role'],
                          'plan': 'engine-only', '_text': message['text']})
    for entry in available:
        row = entry['row']
        if entry['matched'] and not entry['text']:
            continue  # every word of this row has an engine twin
        plans.append({'store': 'donor', 'donor_msg_id': row['id'], 'role': 'user' if row['position'] == 'right' else 'assistant',
                      'plan': 'partial' if entry['matched'] else 'donor-only', '_text': _text(row['content'])})
    for row in donor_rows:
        if row['type'] != 'text':
            plans.append({'store': 'donor', 'donor_msg_id': row['id'], 'kind': row['type'],
                          'plan': 'donor-tool' if row['type'] == 'acp_tool_call' else 'donor-' + str(row['type'])})
    return plans


def _when(ms):
    if not ms:
        return None
    try:
        return datetime.fromtimestamp(float(ms) / (1000 if float(ms) > 10 ** 11 else 1)).strftime('%Y-%m-%d %H:%M')
    except (OverflowError, OSError, ValueError):
        return None


def inventory(data, store=None, show_text=False, effective_links=None):
    """`effective_links` {donor: conversation or None}: the link each chat it names uses (the one store's
    `chat_links`, D-80) instead of the first of D, C, E; None means unlinked. A chat it does not name
    keeps the first of D, C, E (it was never folded into the table)."""
    engine_root, donor_db = _paths(data, store)
    session_map = session_records(engine_root)
    legacy = legacy_map(engine_root)
    with contextlib.closing(_open(engine_root / 'kel.sqlite3')) as kel, contextlib.closing(_open(donor_db)) as donor:
        kel.row_factory = sqlite3.Row
        donor.row_factory = sqlite3.Row
        conversations = {r['id']: dict(r) for r in kel.execute('SELECT id,project_id,title,created FROM conversations')}
        counts = dict(kel.execute('SELECT conversation_id,COUNT(*) FROM messages GROUP BY conversation_id').fetchall())
        visible = ('seq NOT IN (SELECT seq FROM rewound_messages)' if _table(kel, 'rewound_messages') else '1=1')
        bindings = ({r['donor_id']: r['project_id'] for r in kel.execute('SELECT donor_id,project_id FROM project_bindings')}
                    if _table(kel, 'project_bindings') else {})
        utility = ({r[0] for r in kel.execute('SELECT utility_conversation FROM project_meta WHERE utility_conversation IS NOT NULL')}
                   if _table(kel, 'project_meta') else set())

        def weigh(cid):
            return cid in conversations, counts.get(cid, 0)

        def engine_messages(cid):
            return [dict(r) for r in kel.execute('SELECT seq,role,text FROM messages WHERE conversation_id=? AND '
                                                 + visible + ' ORDER BY seq', (cid,))]

        chats, referenced = [], set()
        rows_total = {'text': 0, 'acp_tool_call': 0, 'tips': 0, 'other': 0}
        for conv in donor.execute('SELECT * FROM conversations ORDER BY created_at'):
            conv = dict(conv)
            donor_id = conv['id']
            known = True
            try:
                extra = json.loads(conv.get('extra') or '{}')
                if not isinstance(extra, dict):
                    raise ValueError
            except ValueError:
                extra, known = {}, False
            extra_link = extra.get('kel_conversation_id')
            if extra_link is not None and not isinstance(extra_link, str):
                known, extra_link = False, None
            links = {'session_map': session_map.get(donor_id), 'legacy_map': legacy.get(donor_id),
                     'donor_extra': extra_link or None, 'project_binding': bindings.get(donor_id)}
            candidates = [(links[key], source) for key, source in (('session_map', 'session-map'),
                                                                   ('legacy_map', 'legacy-map'),
                                                                   ('donor_extra', 'donor-extra')) if links[key]]
            referenced.update(cid for cid, _ in candidates)
            effective = candidates[0] if candidates else None
            if effective_links is not None and donor_id in effective_links:
                chosen = effective_links[donor_id]
                effective = (chosen, 'chat-links') if chosen else None
                if chosen:
                    referenced.add(chosen)
            rows = [dict(r) for r in donor.execute('SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at, id',
                                                   (donor_id,))]
            by_type = {'text': 0, 'acp_tool_call': 0, 'tips': 0, 'other': 0}
            for row in rows:
                by_type[row['type'] if row['type'] in by_type else 'other'] += 1
            for key, value in by_type.items():
                rows_total[key] += value
            exists, messages = weigh(effective[0]) if effective else (False, 0)
            if not known:
                klass = 'unknown'
            elif not effective:
                klass = 'unlinked-donor-words' if rows else 'unlinked-empty'
            elif not exists:
                klass = 'dead-donor-words' if rows else 'dead-empty'
            elif messages and rows:
                klass = 'linked'
            elif messages:
                klass = 'linked-engine-only'
            elif rows:
                klass = 'linked-donor-only'
            else:
                klass = 'linked-empty'
            conflict = None
            if len({cid for cid, _ in candidates}) > 1:
                winner, rule = resolve(candidates, weigh)
                sides = []
                for cid, source in candidates:
                    if cid not in [side['conversation'] for side in sides]:
                        sides.append({'conversation': cid, 'source': source, 'exists': weigh(cid)[0],
                                      'messages': weigh(cid)[1]})
                conflict = {'sides': sides, 'stage1_winner': winner, 'rule': rule}
            plan = plan_rows(engine_messages(effective[0]) if exists else [], rows)
            for item in plan:
                text = item.pop('_text', None)
                if show_text and text is not None:
                    item['text'] = text
            summary = {}
            for item in plan:
                summary[item['plan']] = summary.get(item['plan'], 0) + 1
            chats.append({
                'donor_id': donor_id, 'title': conv.get('name'), 'created': _when(conv.get('created_at')),
                'updated': _when(conv.get('updated_at')), 'archived': bool(conv.get('archived_at')),
                'pinned': bool(conv.get('pinned')), 'links': links,
                'effective': ({'conversation': effective[0], 'source': effective[1], 'exists': exists,
                               'messages': messages} if effective else None),
                'donor_rows': by_type, 'hidden_donor_rows': sum(1 for r in rows if r.get('hidden')),
                'class': klass, 'conflict': conflict, 'plan_summary': summary, 'plan': plan})
        unlinked = [{'conversation': cid, 'title': c.get('title'), 'created': _when(c.get('created')),
                     'messages': counts.get(cid, 0), 'utility': cid in utility}
                    for cid, c in conversations.items() if cid not in referenced]
        by_class = {name: 0 for name in CLASSES}
        for chat in chats:
            by_class[chat['class']] = by_class.get(chat['class'], 0) + 1
        return {
            'generated': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'engine': str(engine_root), 'donor_db': str(donor_db), 'text_included': bool(show_text),
            'totals': {
                'donor_chats': len(chats),
                'donor_archived': sum(1 for c in chats if c['archived']),
                'donor_with_extra_link': sum(1 for c in chats if c['links']['donor_extra']),
                'donor_rows': rows_total,
                'engine_conversations': len(conversations),
                'engine_messages': sum(counts.values()),
                'mapped_by_legacy_or_session_map': sum(1 for c in chats if c['links']['session_map'] or c['links']['legacy_map']),
                'engine_conversations_not_linked': len(unlinked),
                'conflicts': sum(1 for c in chats if c['conflict']),
                'donor_only_rows': sum(c['plan_summary'].get('donor-only', 0) + c['plan_summary'].get('partial', 0)
                                       for c in chats),
            },
            'classes': by_class,
            'chats': chats,
            'engine_conversations_not_linked': unlinked,
        }


def _short(value):
    return (value or '')[:8]


def markdown(report):
    """The same inventory in plain words, for Nick to review. No message text."""
    t = report['totals']
    chats = report['chats']
    lines = ['# Chat store report', '',
             'Made ' + report['generated'] + ' by `python -m kel.chatstore inventory` (CP-10a stage 0, D-77), from '
             'read-only copies of your Data. Nothing in Data was changed. This report holds chat titles and dates, '
             'never what was said.', '',
             '## In short', '',
             '- The app keeps **%d chats** (%d archived). Kel\'s own store keeps **%d conversations** with **%d messages**.'
             % (t['donor_chats'], t['donor_archived'], t['engine_conversations'], t['engine_messages']),
             "- The app's store holds %d rows: %d text, %d work updates, %d notes."
             % (sum(t['donor_rows'].values()), t['donor_rows']['text'], t['donor_rows']['acp_tool_call'],
                t['donor_rows']['tips']),
             '- %d chats carry a link on the app\'s side; %d are linked by Kel\'s files.'
             % (t['donor_with_extra_link'], t['mapped_by_legacy_or_session_map']),
             '- Kel conversations that no app chat links to: %d.' % t['engine_conversations_not_linked'],
             '- Chats whose links disagree: %d.' % t['conflicts'], '',
             '## Which chats exist where', '',
             '| Kind of chat | Chats |', '|---|---|']
    for name, words in CLASSES.items():
        lines.append('| %s | %d |' % (words, report['classes'].get(name, 0)))
    if report['classes'].get('unknown'):
        lines.append('| Could not be classified | %d |' % report['classes']['unknown'])
    lines += ['', '"The app\'s store" is the chat list you see (kept by the bundled aioncore host). '
              '"Kel\'s store" is Kel\'s own database of what was said and done.', '']

    def when(chat):
        return (chat['created'] or 'unknown date') + (' (archived)' if chat['archived'] else '')

    def title(chat):
        return (chat['title'] or '(untitled)').replace('|', '/').replace('\n', ' ')

    only_app = [c for c in chats if c['class'] in ('dead-donor-words', 'unlinked-donor-words', 'linked-donor-only')]
    lines += ['## Chats whose words exist only in the app\'s store (%d)' % len(only_app), '',
              'Kel\'s own store has none of these words. Stage 2 would copy them into Kel\'s store, marked as '
              'imported, after you have looked at this list. Nothing is copied yet.', '',
              '| Title | Started | Last change | Rows in the app | Why |', '|---|---|---|---|---|']
    for c in only_app:
        rows = c['donor_rows']
        lines.append('| %s | %s | %s | %d text, %d notes | %s |' % (
            title(c), when(c), c['updated'] or '', rows['text'], rows['tips'],
            'its Kel conversation is gone' if c['class'] == 'dead-donor-words' else
            'never linked to Kel' if c['class'] == 'unlinked-donor-words' else "Kel's side is empty"))
    dead = [c for c in chats if c['class'] == 'dead-empty']
    lines += ['', '## Empty chats whose Kel side is gone (%d)' % len(dead), '',
              'These show in the sidebar as empty chats. Most are audit and test chats. Nothing here is deleted; '
              'the design suggests hiding them later (question 4).', '',
              '| Title | Started | Last change |', '|---|---|---|']
    for c in dead:
        lines.append('| %s | %s | %s |' % (title(c), when(c), c['updated'] or ''))
    conflicts = [c for c in chats if c['conflict']]
    names = {'session-map': "Kel's session record", 'legacy-map': "Kel's older map", 'donor-extra': "the app's own link"}
    lines += ['', '## Chats whose links disagree (%d)' % len(conflicts), '',
              "Kel answered in the conversation its session record names, while the app showed the one its own "
              'link names. With the one link table (stage 1, switch `chat_store = engine`), the side whose Kel '
              'conversation exists and has messages wins; when none does, the chat is treated as unlinked and gets '
              'a fresh link the next time you open it. Nothing is deleted either way.', '',
              '| Title | Started | Sides (Kel conversation: state) | With the link table |', '|---|---|---|---|']
    for c in conflicts:
        sides = '; '.join('%s → %s: %s' % (names.get(s['source'], s['source']), _short(s['conversation']),
                                            ('%d messages' % s['messages']) if s['exists'] else 'gone')
                          for s in c['conflict']['sides'])
        outcome = ('links to ' + _short(c['conflict']['stage1_winner'])) if c['conflict']['stage1_winner'] else \
            'unlinked (no side has messages)'
        lines.append('| %s | %s | %s | %s |' % (title(c), when(c), sides, outcome))
    partial = [c for c in chats if c['class'] == 'linked' and
               (c['plan_summary'].get('donor-only', 0) + c['plan_summary'].get('partial', 0))]
    if partial:
        lines += ['', "## Linked chats with rows the rule could not match (%d)" % len(partial), '',
                  "These chats are linked and mostly the same in both stores, but some rows in the app have no "
                  "twin in Kel's store by the desktop's matching rule (same speaker, same words or the start of "
                  "them). Usually a reply the app shows that Kel stored differently, or one that stopped part-way. "
                  'Stage 2 treats them like the chats above: copied, marked, after your review.', '',
                  '| Title | Started | App rows with no Kel twin | Whose |', '|---|---|---|---|']
        for c in partial:
            roles = sorted({p.get('role') or '' for p in c['plan'] if p['plan'] in ('donor-only', 'partial')})
            lines.append('| %s | %s | %d | %s |' % (title(c), when(c), c['plan_summary'].get('donor-only', 0)
                                                     + c['plan_summary'].get('partial', 0),
                                                     ', '.join('yours' if r == 'user' else "Kel's" for r in roles)))
    if report['engine_conversations_not_linked']:
        lines += ['', "## Kel conversations no app chat links to (%d)" % len(report['engine_conversations_not_linked']), '',
                  '| Title | Started | Messages | Kel\'s own utility chat |', '|---|---|---|---|']
        for c in report['engine_conversations_not_linked']:
            lines.append('| %s | %s | %d | %s |' % ((c['title'] or '(untitled)').replace('|', '/'), c['created'] or '',
                                                    c['messages'], 'yes' if c['utility'] else 'no'))
    lines += ['', '## Every chat', '',
              '| Title | Started | Kind | App rows | Kel messages | Same in both | Text only in app | Only in Kel |',
              '|---|---|---|---|---|---|---|---|']
    for c in chats:
        s = c['plan_summary']
        lines.append('| %s | %s | %s | %d | %d | %d | %d | %d |' % (
            title(c), when(c), CLASSES.get(c['class'], 'Could not be classified'), sum(c['donor_rows'].values()),
            (c['effective'] or {}).get('messages', 0), s.get('same', 0), s.get('donor-only', 0) + s.get('partial', 0),
            s.get('engine-only', 0)))
    lines += ['', '## What needs you', '',
              '1. May the chats in "words exist only in the app\'s store" be copied into Kel\'s store in stage 2? '
              '(Recommended: yes.)',
              '2. May the empty chats whose Kel side is gone be hidden from the sidebar later? They are not deleted. '
              '(Recommended: hide.)',
              ('3. The chats whose links disagree are all empty or gone on both sides, so the rule changes nothing '
               'you can see. Nothing to decide unless one of them matters to you.'
               if not any(s['messages'] for c in conflicts for s in c['conflict']['sides']) else
               '3. At least one chat whose links disagree has messages on a side. Check the "links disagree" table: '
               'the side with messages is the one kept.'), '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='python -m kel.chatstore')
    sub = parser.add_subparsers(dest='command', required=True)
    inv = sub.add_parser('inventory', help='classify every chat across both stores (read-only)')
    inv.add_argument('--data', required=True, help='the Data folder (or its engine folder)')
    inv.add_argument('--store', help="the donor host's store folder (default: <Data>/store)")
    inv.add_argument('--json', help='write the JSON report here (default: print it)')
    inv.add_argument('--markdown', help='also write the plain-words report here')
    inv.add_argument('--show-text', action='store_true', help='include message text (for review only)')
    args = parser.parse_args(argv)
    report = inventory(args.data, args.store, show_text=args.show_text)
    encoded = json.dumps(report, indent=2, ensure_ascii=False)
    if args.json:
        Path(args.json).write_text(encoded, encoding='utf-8')
    else:
        sys.stdout.write(encoded + '\n')
    if args.markdown:
        Path(args.markdown).write_text(markdown(report), encoding='utf-8')
    return 2 if report['classes'].get('unknown') else 0


if __name__ == '__main__':
    sys.exit(main())
