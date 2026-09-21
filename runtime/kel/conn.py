"""kel.conn — the assistant runtime's door to Connections (V2-04a).

A normal command the coding runtime may run (the runtime instructions point here):

    python -m kel.conn list
    python -m kel.conn call <action-id> [--param name=value]... [--connection <id>]
                                      [--confirm <approval-id|auto>]

`list` shows the connected-service actions this piece of work may use, resolved through the same
capability controls the app shows. `call` performs one through the engine: the helper never holds a
credential (the engine supplies values from its in-memory custody) and it prints plain, bounded
text. Job and run identity arrive through KEL_JOB_ID / KEL_RUN_ID, set by the engine for the work
this runtime is doing.

Exit codes: 0 Kel answered (whatever the service said); 3 a change needs the user's OK first;
4 not allowed / not usable — the message says why; 5 Kel could not finish the call.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

EXIT_OK = 0
EXIT_NEEDS_CONFIRMATION = 3
EXIT_NOT_ALLOWED = 4
EXIT_FAILED = 5


def _fail(message, code=EXIT_FAILED):
    sys.stdout.write(str(message).rstrip() + '\n')
    raise SystemExit(code)


def _session():
    root = os.environ.get('KEL_DATA_DIR') or ''
    if not root:
        _fail('Kel is not connected on this computer, so connected services are not available here.')
    try:
        data = json.loads((Path(root) / 'desktop-session.json').read_text(encoding='utf-8-sig'))
    except Exception:
        _fail('Kel is not answering on this computer right now.')
    url = str((data or {}).get('url') or '')
    token = str((data or {}).get('token') or '')
    if not url or not token:
        _fail('Kel is not answering on this computer right now.')
    return url.rstrip('/'), token


def _ask(body):
    url, token = _session()
    request = urllib.request.Request(url + '/api/connections',
                                     data=json.dumps(body).encode('utf-8'),
                                     headers={'Authorization': 'Bearer ' + token,
                                              'Content-Type': 'application/json'},
                                     method='POST')
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as error:
        try:
            payload = json.loads(error.read().decode('utf-8'))
            message = str(payload.get('error') or '').strip()
        except Exception:
            message = ''
        _fail(message or ('Kel could not finish that (%d).' % error.code))
    except urllib.error.URLError:
        _fail('Kel is not reachable on this computer right now.')


def _bounded(text, limit=6000):
    text = str(text or '')
    return text if len(text) <= limit else text[:limit] + '\n[cut short]'


def _print_result(result, as_json=False):
    if as_json:
        # The engine envelope is already bounded (answers are cut at TOOL_ANSWER_LIMIT); printing it
        # whole keeps the JSON parseable, unlike a byte-bound slice.
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + '\n')
        return
    state = str(result.get('state') or '')
    note = str(result.get('note') or '')
    sys.stdout.write('%s — %s\n' % (state or 'result', _bounded(note, 500)))
    value = result.get('result')
    if value is not None:
        rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
        sys.stdout.write('result:\n' + _bounded(rendered) + '\n')
    if result.get('truncated'):
        sys.stdout.write('(Kel cut this answer short.)\n')


def main(argv=None):
    parser = argparse.ArgumentParser(prog='kel.conn',
                                     description='Use a connected service through Kel.')
    parser.add_argument('command', choices=('list', 'call'))
    parser.add_argument('action', nargs='?', default='')
    parser.add_argument('--param', action='append', default=[], metavar='NAME=VALUE')
    parser.add_argument('--connection', default='')
    parser.add_argument('--confirm', default='')
    parser.add_argument('--job', default=os.environ.get('KEL_JOB_ID', ''))
    parser.add_argument('--run', default=os.environ.get('KEL_RUN_ID', ''))
    parser.add_argument('--conversation', default='')
    parser.add_argument('--json', dest='as_json', action='store_true')
    args = parser.parse_args(argv)

    params = {}
    for item in args.param:
        if '=' not in item:
            _fail('Use --param name=value for each value the action needs.', EXIT_NOT_ALLOWED)
        name, value = item.split('=', 1)
        params[name.strip()] = value

    body = {'action': 'catalog' if args.command == 'list' else 'call',
            'job': args.job or None, 'conversation': args.conversation or None}
    if args.command == 'call':
        if not args.action:
            _fail('Say which action to use (`python -m kel.conn list` shows them).', EXIT_NOT_ALLOWED)
        body.update({'action_id': args.action, 'params': params,
                     'id': args.connection or None, 'run': args.run or None,
                     'confirm': args.confirm or None})

    result = _ask(body)

    if args.command == 'list':
        if not result.get('allowed'):
            _print_result(result, args.as_json)
            raise SystemExit(EXIT_NOT_ALLOWED)
        if args.as_json:
            _print_result(result, True)
            raise SystemExit(EXIT_OK)
        actions = result.get('actions') or []
        if not actions:
            sys.stdout.write('No connected-service actions are available here yet.\n')
            raise SystemExit(EXIT_OK)
        for item in actions:
            change = ' [asks first: it changes something]' if item.get('mutating') else ''
            usable = '' if item.get('usable') else (' — not usable: ' + str(item.get('reason') or ''))
            fields = ', '.join(item.get('params') or []) or 'no fields'
            sys.stdout.write('%s — %s on %s (%s)%s%s\n' % (
                item.get('id'), item.get('name'),
                item.get('connection_name') or item.get('connection'), fields, change, usable))
        raise SystemExit(EXIT_OK)

    _print_result(result, args.as_json)
    state = str(result.get('state') or '')
    if state.startswith('needs_confirmation'):
        raise SystemExit(EXIT_NEEDS_CONFIRMATION)
    if state in ('not_allowed', 'needs_setup', 'needs_credentials', 'bad_arguments',
                 'unknown_action', 'not_connected', 'cannot_do'):
        raise SystemExit(EXIT_NOT_ALLOWED)
    if state in ('error', 'timeout', 'unreachable'):
        raise SystemExit(EXIT_FAILED)
    raise SystemExit(EXIT_OK)


if __name__ == '__main__':
    main()
