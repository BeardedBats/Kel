"""ACP presentation adapter for the existing durable Kel HTTP service.

The adapter owns no engine. Closing stdin leaves service work alive.
"""
import argparse
import base64
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlparse, unquote
from urllib.request import Request, urlopen, url2pathname
import uuid

if __package__ in (None, ''):
    # ACP runs as a standalone stdio script in source mode
    # (python kel/acp_host.py --data <root>), where relative imports do not resolve.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from kel.core import explain_approval, explain_failure
else:
    from .core import explain_approval, explain_failure


PLAIN_STATES = {
    'QUEUED': 'Kel is queued',
    'READY': 'Kel is ready to start',
    'RUNNING': 'Kel is working',
    'WAITING_RESOURCE': 'Kel is waiting for a model to continue',
    'AWAITING_USER': 'Kel is waiting for you',
    'PAUSED': 'Kel is paused',
    'BLOCKED': 'Kel is blocked by a safety rule',
    'CLOSED': 'Kel finished',
    'CANCELLED': 'Kel cancelled this',
}


# D-75.1: how often an open reply's words are read while the model writes them.
DRAFT_INTERVAL = 0.15

# CH-3: what the chat shows when the person stops a reply (the engine posts the same note).
STOPPED_NOTE = 'You stopped this reply.'


def _plain_state(status):
    return PLAIN_STATES.get(str(status), 'Kel is working on it')


def _settled_title(status, verdict):
    """A job's card title once it stops moving: what happened, never a raw verdict word."""
    if status == 'CLOSED':
        return {'VERIFIED': 'Kel finished — it passed its checks',
                'FAILED': "Kel finished — it didn't pass its checks"}.get(
                    verdict, 'Kel finished — not fully verified')
    return _plain_state(status)


def _failure_sentence(submission):
    """One plain sentence for a message Kel could not answer or start (never a state name)."""
    error = str(submission.get('error') or '').strip().rstrip('.')
    if error:
        return "I couldn't finish that — " + error + '. Try sending it again.'
    if submission.get('state') == 'INTERRUPTED':
        return "Kel closed before it could answer that. Send it again when you're ready."
    return 'Something went wrong before I could answer that. Try sending it again.'


FILES_MARKER = '[[AION_FILES]]'
ATTACHMENT_LIMIT = 5_000_000


def _local_path(line):
    """An absolute local file path from one marker line, or None (URLs, UNC shares, prose)."""
    candidate = line.strip()
    if not candidate or '://' in candidate or candidate.startswith(('\\\\', '//')):
        return None
    if not (candidate.startswith('/') or (len(candidate) > 2 and candidate[1] == ':' and candidate[2] in '\\/')):
        return None
    return candidate


def split_file_marker(text):
    """(text without the block, [paths]) for the desktop's ``[[AION_FILES]]`` block (FN-04).

    The shell sends files the person attached as a trailing marker block of absolute paths — the
    same format its message view parses (fileMarker.ts): the last marker line, then one path per
    non-empty line until the next ``[[…]]`` line. A block holding anything but local absolute paths
    is not a file block and the text is returned untouched (a message that only mentions the marker).
    """
    lines = text.split('\n')
    marker = next((i for i in range(len(lines) - 1, -1, -1) if lines[i].strip() == FILES_MARKER), -1)
    if marker < 0:
        return text, []
    end = next((i for i in range(marker + 1, len(lines)) if lines[i].strip().startswith('[[')), len(lines))
    entries = [line.strip() for line in lines[marker + 1:end] if line.strip()]
    paths = [_local_path(line) for line in entries]
    if not paths or any(path is None for path in paths):
        return text, []
    kept = lines[:marker] + lines[end:]
    return '\n'.join(kept).strip(), paths


class MethodNotFound(ValueError):
    """JSON-RPC -32601: the host asked for a method this agent does not implement."""


# JSON-RPC error codes. -32000 is deliberately never used: the bundled host reads it as
# "Authentication required" and tells the person the agent needs signing in.
METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR = -32601, -32602, -32603


def error_code(error):
    if isinstance(error, MethodNotFound):
        return METHOD_NOT_FOUND
    if isinstance(error, (KeyError, TypeError, ValueError)):
        return INVALID_PARAMS
    return INTERNAL_ERROR


def _without_clauses(text, clauses):
    """The user's request with the applied reserved [kel:…] directives removed.

    Only the exact reserved token travels away, with the whitespace around it and at most one
    adjacent separator per side; an empty delimiter pair left behind by the token ("A ([kel:web=off]) B")
    is removed with it. A pair of list separators ("A,[kel:web=off],B") keeps one comma instead of
    deleting both. Words are never joined, and nothing beyond the token and its immediate seam is
    ever deleted.
    """
    out = text
    for clause in sorted(clauses, key=lambda item: item['start'], reverse=True):
        start, end = clause['start'], clause['end']
        left = start
        while left > 0 and out[left - 1] in ' \t':
            left -= 1
        right = end
        while right < len(out) and out[right] in ' \t':
            right += 1
        if left > 0 and right < len(out) and out[left - 1] == '(' and out[right] == ')':
            # The token was the only content of a parenthesised aside: take the empty pair too.
            start, end = left - 1, right + 1
            while start > 0 and out[start - 1] in ' \t':
                start -= 1
            while end < len(out) and out[end] in ' \t':
                end += 1
        else:
            separators = ',;'
            dashes = '\u2014\u2013-'
            left_sep = out[left - 1] if left > 0 and out[left - 1] in separators else ''
            right_sep = out[right] if right < len(out) and out[right] in separators else ''
            left_dash = left > 0 and out[left - 1] in dashes
            right_dash = right < len(out) and out[right] in dashes
            if left_sep and right_sep:
                start, end = left - 1, right          # keep the right comma: "A,[kel:x=off],B" -> "A,B"
            elif left_sep or left_dash:
                start = left - 1
                end = right
            elif right_sep or right_dash:
                start = left
                end = right + 1
                while end < len(out) and out[end] in ' \t':
                    end += 1
            else:
                start, end = left, right
            if left_dash and right_dash:
                start, end = left - 1, right + 1
                while start > 0 and out[start - 1] in ' \t':
                    start -= 1
                while end < len(out) and out[end] in ' \t':
                    end += 1
        if start > 0 and end < len(out) and out[start - 1].isalnum() and out[end].isalnum():
            out = out[:start] + ' ' + out[end:]    # never join two words that were separated
        else:
            out = out[:start] + out[end:]
    return out.strip()


class ServiceClient:
    def __init__(self, data):
        self.data = Path(data)

    @staticmethod
    def approval_summary(action):
        """Human-readable summary of a pending approval action.

        Older engines do not emit action_summary; fall back to the action
        payload itself so the ACP stream can still name the step.
        """
        try:
            parsed = json.loads(action) if isinstance(action, str) else (action or {})
        except Exception:
            parsed = {}
        kind = parsed.get('kind') or (parsed.get('action', {}) or {}).get('type') or 'permission'
        if parsed.get('kind') == 'command':
            return 'run ' + str(parsed.get('command', ''))[:120]
        if parsed.get('kind') == 'permissions':
            return 'grant requested permissions'
        if parsed.get('kind') == 'grantRoot':
            return 'grant full workspace access'
        if parsed.get('kind') == 'changes':
            return 'apply the checked change set'
        return 'take the requested ' + str(kind) + ' action'

    def call(self, route, payload=None):
        descriptor = json.loads((self.data / 'desktop-session.json').read_text(encoding='utf-8-sig'))
        parsed = urlparse(descriptor['url'])
        if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.username:
            raise ValueError('Kel service descriptor must use authenticated loopback HTTP')
        request = Request(descriptor['url'].rstrip('/') + route,
                          data=None if payload is None else json.dumps(payload).encode(),
                          headers={'Authorization': 'Bearer ' + descriptor['token'], 'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code in (401, 403):
                error.close()
                raise RuntimeError('Kel service authentication failed; reopen Kel to reconnect') from None
            try:
                detail = json.load(error).get('error', 'Kel service request failed')
            except Exception:
                detail = 'Kel service request failed'
            error.close()
            raise RuntimeError(detail) from None

    def state(self, conversation='main'):
        return self.call('/api/state?conversation=' + quote(conversation))


class ACPHost:
    # CP-2: one /api/state read a second while a turn is open (it was four).
    def __init__(self, client, emit, poll_interval=1.0):
        self.client, self.emit, self.poll_interval = client, emit, poll_interval
        self.active = {}
        self.reserved = set()  # ST-04: chats opened here whose conversation is not created yet
        self.lock = threading.RLock()
        self.closed = threading.Event()

    def update(self, session, update):
        if not self.closed.is_set():
            self.emit({'jsonrpc': '2.0', 'method': 'session/update',
                       'params': {'sessionId': session, 'update': update}})

    def text(self, session, text):
        self.update(session, {'sessionUpdate': 'agent_message_chunk', 'content': {'type': 'text', 'text': text}})

    def _vetting(self, cid, text):
        """Design Vetting: silent ingestion of answers/controls. Returns the result or None."""
        try:
            result = self.client.call('/api/vetting',
                                      {'action': 'ingest_chat', 'conversation': cid, 'text': text})
        except Exception:
            return None
        return result if isinstance(result, dict) and result.get('kind') not in (None, 'none') else None

    def _capability_directive(self, cid, text):
        """A conversation capability instruction, answered inline. Returns the reply or None."""
        try:
            result = self.client.call('/api/capabilities',
                                      {'action': 'directive', 'conversation': cid, 'text': text})
        except Exception:
            return None
        return result.get('reply') if isinstance(result, dict) and result.get('applied') else None

    def _resurface(self, session, cid):
        """After an interruption, bring the active vetting prompts back into view."""
        try:
            pending = self.client.call('/api/vetting', {'action': 'resurface', 'conversation': cid})
        except Exception:
            return
        message = (pending or {}).get('message')
        if message:
            self.text(session, '\n' + message + '\n')

    def _reserved(self, cid):
        """A conversation id this host handed out on session/new that has no engine row yet (ST-04).

        Known in memory for this host, or from the session-map record written at session/new
        (so a restarted host still recognises a chat that was opened but never used)."""
        if cid in self.reserved:
            return True
        # CP-10a (D-77): with the engine chat store, a chat's live link is its reserved conversation.
        view = self._chat_link(conversation=cid)
        if view.get('mode') == 'engine' and view.get('donor'):
            return True
        folder = self.client.data / 'aion-session-map'
        if folder.is_dir():
            for record in folder.glob('*.json'):
                try:
                    if cid in json.loads(record.read_text(encoding='utf-8-sig')).values():
                        return True
                except (OSError, ValueError, AttributeError):
                    continue
        return False

    @staticmethod
    def _write_record(record, donor_id, cid):
        record.parent.mkdir(exist_ok=True)
        temporary = record.with_suffix('.' + uuid.uuid4().hex + '.tmp')
        with temporary.open('w', encoding='utf-8') as handle:
            json.dump({donor_id: cid}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, record)

    def _chat_link(self, donor=None, conversation=None):
        """CP-10a (D-77): the engine's answer for one chat ({mode, conversation} or {mode, donor}).
        An engine without the link table, or one that cannot be reached, means the legacy files."""
        route = '/api/chat-link?' + ('donor=' + quote(donor) if donor else 'conversation=' + quote(conversation or ''))
        try:
            view = self.client.call(route)
        except Exception:
            return {'mode': 'legacy'}
        if not isinstance(view, dict) or view.get('mode') not in ('legacy', 'engine'):
            return {'mode': 'legacy'}
        return view

    def session(self, session):
        """(conversation id, state, exists). A reserved chat with no row yet has empty state."""
        if not isinstance(session, str) or not session.startswith('kel:'):
            raise ValueError('Unknown Kel session')
        cid = session[4:]
        state = self.client.state(cid)
        if not any(c['id'] == cid for c in state['conversations']):
            if not self._reserved(cid):
                raise ValueError('Kel conversation no longer exists')
            return cid, state, False
        return cid, state, True

    def dispatch(self, method, params):
        if method == 'initialize':
            from kel.service import ENGINE_VERSION
            return {'protocolVersion': 1, 'agentInfo': {'name': 'kel', 'title': 'Kel', 'version': ENGINE_VERSION},
                    'agentCapabilities': {'loadSession': True, 'promptCapabilities': {'image': True, 'embeddedContext': True}},
                    'authMethods': []}
        if method == 'session/new':
            state = self.client.state()
            donor_id = os.environ.get('AIONUI_CONVERSATION_ID')
            record = None
            if donor_id:
                safe_id = hashlib.sha256(donor_id.encode()).hexdigest()
                record = self.client.data / 'aion-session-map' / (safe_id + '.json')
            map_path = self.client.data / 'aion-conversations.json'
            view = self._chat_link(donor=donor_id) if donor_id else {}
            if view.get('mode') == 'engine':
                # CP-10a (D-77): the engine's link table is the one answer. The files are kept for
                # a switch back to legacy: a new chat still gets its record, an existing one is never
                # rewritten.
                if view.get('conversation'):
                    session = 'kel:' + view['conversation']
                    self.dispatch('session/load', {'sessionId': session})
                    return {'sessionId': session}
                cid = str(uuid.uuid4())
                with self.lock:
                    self.reserved.add(cid)
                linked = self.client.call('/api/chat-link', {'action': 'link', 'donor': donor_id,
                                                             'conversation': cid, 'source': 'acp'})
                linked = (linked or {}).get('conversation') or cid
                if linked != cid:
                    with self.lock:
                        self.reserved.discard(cid)
                    session = 'kel:' + linked
                    self.dispatch('session/load', {'sessionId': session})
                    return {'sessionId': session}
                if not record.exists():
                    self._write_record(record, donor_id, cid)
                return {'sessionId': 'kel:' + cid}
            if donor_id:
                mapping = json.loads(map_path.read_text(encoding='utf-8-sig')) if map_path.exists() else {}
                if record.exists():
                    mapping.update(json.loads(record.read_text(encoding='utf-8-sig')))
                mapped = mapping.get(donor_id)
                if mapped:
                    session = 'kel:' + mapped
                    self.dispatch('session/load', {'sessionId': session})
                    return {'sessionId': session}
            # A new ACP conversation has no user-authorized project yet. The
            # donor's working directory (often a temp or install path) is not a
            # project root: a root must come from an explicit project choice or
            # greenfield intent. It will be created in the unrooted project.
            # ST-04: opening a chat writes nothing in the engine — the id is reserved here and the
            # conversation is created on its first message, so launches leave no empty chats.
            cid = str(uuid.uuid4())
            with self.lock:
                self.reserved.add(cid)
            if record:
                self._write_record(record, donor_id, cid)
            return {'sessionId': 'kel:' + cid}
        if method == 'session/load':
            session = params['sessionId']
            _, state, _exists = self.session(session)
            for row in state['messages']:
                kind = 'user_message_chunk' if row['role'] == 'user' else 'agent_message_chunk'
                self.update(session, {'sessionUpdate': kind, 'content': {'type': 'text', 'text': row['text']}})
            return {}
        if method == 'session/prompt':
            return self.prompt(params)
        if method == 'session/cancel':
            session = params['sessionId']
            with self.lock:
                active = self.active.get(session)
                if active:
                    active['cancel'].set()
            return {}
        if method in ('session/set_mode', 'session/set_model', 'session/set_config_option'):
            # Kel has one mode and routes models itself (the model pill writes Kel's own preference
            # through /api/model). The host's session tuning is accepted as a no-op rather than an
            # error the host would misreport as an authentication problem.
            return {}
        if method == 'session/request_permission':
            # V1.5 G12: this host is a transport for the donor agent surface and never grants
            # donor-agent tool permissions. Every permission request is refused explicitly (fail
            # closed with a named policy message) instead of falling through to the generic
            # unsupported-method error; Kel's own effects are authorized by the central boundary
            # (kel/authorize.py) before they ever run.
            raise ValueError('Kel denies tool permissions on this surface by policy (V1.5)')
        raise MethodNotFound('Unsupported ACP method: ' + method)

    def _attach(self, cid, name, mime, raw):
        return self.client.call('/api/attach', {'conversation': cid, 'name': name, 'mime': mime,
                                                'content': base64.b64encode(raw).decode()})['id']

    @staticmethod
    def _read_local(path_text):
        """(bytes, file name) of one file the person attached, with the same limits as a link."""
        try:
            path = Path(path_text).resolve(strict=True)
        except (OSError, RuntimeError):
            raise ValueError("Kel couldn't find the attached file " + Path(path_text).name +
                             '. Attach it again.') from None
        if not path.is_file() or not 0 < path.stat().st_size <= ATTACHMENT_LIMIT:
            raise ValueError('Attachment must be a file between 1 byte and 5 MB')
        return path.read_bytes(), path.name

    def content(self, cid, blocks):
        texts, attachments, seen_paths = [], [], set()
        for index, block in enumerate(blocks):
            kind = block.get('type')
            if kind == 'text':
                # FN-04: files attached in the composer arrive as the shell's [[AION_FILES]] block of
                # local paths. Each file is copied into Kel's own attachment store (this conversation's
                # folder under Kel's data) and the block leaves the text Kel reads.
                body, paths = split_file_marker(block['text'])
                texts.append(body)
                for path_text in paths:
                    key = os.path.normcase(os.path.abspath(path_text))
                    if key in seen_paths:
                        continue
                    seen_paths.add(key)
                    raw, name = self._read_local(path_text)
                    mime = mimetypes.guess_type(name)[0] or 'text/plain'
                    attachments.append(self._attach(cid, name, mime, raw))
                continue
            if kind == 'image':
                mime = block.get('mimeType', '')
                if mime not in ('image/png', 'image/jpeg', 'image/gif', 'image/webp'):
                    raise ValueError('Kel supports PNG, JPEG, GIF, and WebP images')
                raw = base64.b64decode(block['data'], validate=True)
                name = 'image-' + str(index) + '.' + mime.split('/')[1]
            elif kind == 'resource' and isinstance(block.get('resource'), dict):
                resource = block['resource']
                mime = resource.get('mimeType', 'text/plain')
                name = Path(unquote(urlparse(resource.get('uri', '')).path)).name or 'attachment.txt'
                raw = resource['text'].encode() if 'text' in resource else base64.b64decode(resource['blob'], validate=True)
            elif kind == 'resource_link':
                # ACP prompt file references represent files selected by the user.
                # Never fetch network URLs or UNC shares as an implicit attachment.
                uri = urlparse(block.get('uri', ''))
                if uri.scheme != 'file' or uri.netloc not in ('', 'localhost'):
                    raise ValueError('Attach a local file or embed its contents; remote resource links are unsupported')
                path = Path(url2pathname(uri.path)).resolve(strict=True)
                if not path.is_file() or not 0 < path.stat().st_size <= ATTACHMENT_LIMIT:
                    raise ValueError('Attachment must be a file between 1 byte and 5 MB')
                key = os.path.normcase(str(path))
                if key in seen_paths:
                    continue  # the same file also named in the marker block: attach it once
                seen_paths.add(key)
                raw = path.read_bytes()
                name = path.name
                mime = block.get('mimeType') or mimetypes.guess_type(name)[0] or 'text/plain'
            else:
                raise ValueError('Unsupported ACP content type: ' + str(kind))
            attachments.append(self._attach(cid, name, mime, raw))
        text = '\n'.join(t for t in texts if t).strip()
        if not text:
            raise ValueError('Add a text request with the attachment')
        return text, attachments

    def _stream_words(self, session, sid, stream):
        """D-75.1: for one poll interval, show a reply's new words as the model writes them.

        An engine without the draft route (or any failure reading it) leaves the reply to arrive
        whole, as before."""
        deadline = time.monotonic() + self.poll_interval
        while not self.closed.is_set():
            if stream['ok']:
                try:
                    words = (self.client.call('/api/draft?id=' + quote(sid)) or {}).get('text') or ''
                except Exception:
                    stream['ok'], words = False, ''
                shown = stream['shown']
                if isinstance(words, str) and len(words) > len(shown) and words.startswith(shown):
                    self.text(session, words[len(shown):])
                    stream['shown'] = words
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            self.closed.wait(min(DRAFT_INTERVAL, remaining) if stream['ok'] else remaining)

    def _say_message(self, session, message, stream):
        """One new assistant message; a reply whose words were already shown gets only the rest."""
        text, shown = message['text'], stream['shown']
        if not shown or message.get('job_id'):
            self.text(session, ('\n\n' if shown else '') + text + '\n\n')
            return
        stream['shown'] = ''
        if text.startswith(shown):
            self.text(session, text[len(shown):] + '\n\n')
        else:
            # The finished reply is not what was being written (a guard replaced it, or another
            # model answered after a refusal): the words shown stay, and the real reply follows.
            self.text(session, '\n\n' + text + '\n\n')

    def prompt(self, params):
        session = params['sessionId']
        cid, baseline, exists = self.session(session)
        if not exists:
            # ST-04: the reserved chat becomes a real conversation with its first message. D-54: the
            # engine decides its project (the shell's binding for this chat, else the active one).
            donor = os.environ.get('AIONUI_CONVERSATION_ID')
            self.client.call('/api/conversation', dict({'donor': donor} if donor else {}, id=cid))
            with self.lock:
                self.reserved.discard(cid)
        with self.lock:
            previous = self.active.pop(session, None)
            if previous is not None:
                # A side question arrived while the earlier prompt was still polling.
                # Kel jobs are durable and independent of any chat stream: release the
                # old stream without touching the running job, then serve the new request.
                previous['supersede'].set()
            active = {'cancel': threading.Event(), 'supersede': threading.Event()}
            self.active[session] = active
        try:
            text, attachments = self.content(cid, params.get('prompt', []))
            # Vetting answers and batch controls are understood by the ingestion service and
            # answered inline: no submission, no assistant turn, immediate next answer.
            if not attachments:
                vetting = self._vetting(cid, text)
                if vetting:
                    if vetting.get('message'):
                        self.text(session, vetting['message'] + '\n\n')
                    return {'stopReason': 'end_turn'}
            # Conversation capability commands ("web: use default", "don't browse the web in this
            # chat") write exactly the state the Tools control writes, and answer inline the same way
            # vetting does - one policy, two ways to reach it.
            if not attachments:
                # Strict, explicit commands only: a whole message that is one command answers inline;
                # a deliberately explicit reserved Kel directive ("[kel:terminal=off]") inside a
                # larger request is applied while the rest of the message continues as the user's
                # request. Ordinary prose, technical strings, quoted commands and code samples never
                # change state and are never altered. The policy itself stays engine-side.
                from .capabilities import directive, directive_clauses
                if directive(text):
                    confirmation = self._capability_directive(cid, text)
                    if confirmation:
                        self.text(session, confirmation + '\n\n')
                        return {'stopReason': 'end_turn'}
                else:
                    clauses = directive_clauses(text)
                    if clauses:
                        replies = []
                        for clause in clauses:
                            reply = self._capability_directive(cid, clause['inner'])
                            if reply:
                                replies.append(reply)
                        if replies:
                            self.text(session, '\n\n'.join(replies) + '\n\n')
                        text = _without_clauses(text, clauses)
                        if not text.strip():
                            return {'stopReason': 'end_turn'}
            sid = 'acp-' + uuid.uuid4().hex
            self.client.call('/api/send', {'id': sid, 'conversation': cid, 'text': text, 'attachments': attachments})
            seen = {m['seq'] for m in baseline['messages']}
            stream = {'ok': True, 'shown': ''}  # D-75.1: the reply's words already shown
            last_status = None
            cancelled_job = None
            stop_sent = False
            while not self.closed.is_set():
                state = self.client.state(cid)
                submission = next((s for s in state['submissions'] if s['id'] == sid), None)
                for message in state['messages']:
                    if message['seq'] not in seen:
                        seen.add(message['seq'])
                        if message['role'] == 'assistant':
                            self._say_message(session, message, stream)
                if not submission:
                    raise RuntimeError('Kel lost the submitted request record')
                ack_seq = submission.get('ack_seq')
                if ack_seq and ack_seq in seen:
                    # D-53 conversational hand-off: the acknowledgement has been said, the work runs
                    # durably in the background, and the turn ends so the composer stays usable. The
                    # card reads the hand-off's live state; the checked result arrives as a message.
                    self.update(session, {'sessionUpdate': 'tool_call', 'toolCallId': 'kel-work:' + sid,
                                          'title': 'Working on it in the background', 'kind': 'other',
                                          'status': 'pending', 'rawInput': {'submission_id': sid}})
                    self._resurface(session, cid)
                    return {'stopReason': 'end_turn'}
                if submission['state'] == 'CANCELLED':
                    # Stopped (here or from another window): the engine dropped the reply and
                    # posted its own note, which the loop above has already streamed.
                    return {'stopReason': 'cancelled'}
                if active['cancel'].is_set() and not submission.get('job_id') and not stop_sent:
                    # CH-3: Stop ends this reply only, and really ends it: the engine stops the
                    # in-flight answer and drops whatever it returns later, so no late reply can
                    # surface in the next turn. Work already handed off keeps running; its card is
                    # where it can be stopped (D-53).
                    stop_sent = True
                    try:
                        stopped = self.client.call('/api/cancel', {'id': sid, 'conversation': cid})
                    except Exception:
                        stopped = None
                    if stopped is None:
                        return {'stopReason': 'cancelled'}  # an older engine: end the turn as before
                    if stopped.get('cancelled'):
                        seen.add(stopped.get('message_seq'))
                        self.text(session, ('\n\n' if stream['shown'] else '') + STOPPED_NOTE + '\n\n')
                        return {'stopReason': 'cancelled'}
                    # Already answered or handed off: the next poll shows that answer or the card.
                    continue
                if submission['state'] in ('FAILED', 'INTERRUPTED'):
                    self.text(session, _failure_sentence(submission))
                    self._resurface(session, cid)
                    return {'stopReason': 'end_turn'}
                job_id = submission.get('job_id')
                if job_id:
                    job = next((j for j in state['jobs'] if j['id'] == job_id), None)
                    if not job:
                        raise RuntimeError('Kel job record is unavailable')
                    if active['supersede'].is_set():
                        self.text(session, '(Your earlier request is still running in the background; this reply resumes the conversation.)\n')
                        return {'stopReason': 'end_turn'}
                    if active['cancel'].is_set() and cancelled_job != job_id:
                        self.client.call('/api/control', {'job': job_id, 'action': 'cancel'})
                        cancelled_job = job_id
                    status = job['state']
                    if status != last_status:
                        self.update(session, {'sessionUpdate': 'tool_call' if last_status is None else 'tool_call_update',
                                              'toolCallId': job_id, 'title': _plain_state(status),
                                              'kind': 'other', 'status': 'in_progress'})
                        last_status = status
                    if status in ('CLOSED', 'CANCELLED', 'PAUSED', 'AWAITING_USER', 'WAITING_RESOURCE'):
                        verdict = job.get('verdict') or 'UNCERTAIN'
                        # Assessment closes the job before publication commits its final reply.
                        if status == 'CLOSED' and not any(m.get('job_id') == job_id and m['role'] == 'assistant' for m in state['messages']):
                            self.closed.wait(self.poll_interval)
                            continue
                        terminal = status in ('CLOSED', 'CANCELLED')
                        if status == 'CANCELLED':
                            # A stop the person asked for is not a failure.
                            self.update(session, {'sessionUpdate': 'tool_call_update', 'toolCallId': job_id,
                                                  'status': 'completed', 'title': 'Cancelled'})
                        else:
                            self.update(session, {'sessionUpdate': 'tool_call_update', 'toolCallId': job_id,
                                                  'status': 'completed' if status == 'CLOSED' and verdict == 'VERIFIED' else ('failed' if terminal else 'pending'),
                                                  'title': _settled_title(status, verdict)})
                        if status == 'AWAITING_USER':
                            approvals = state.get('approvals') or []
                            pending = [a for a in approvals if a.get('job_id') == job_id]
                            summary = ''
                            if pending:
                                summary = pending[0].get('action_summary') or ServiceClient.approval_summary(pending[0].get('action'))
                            self.text(session, explain_approval(str(summary)) + '\n')
                        elif status == 'WAITING_RESOURCE':
                            note = explain_failure(job)
                            self.text(session, (note or 'Kel is waiting for an available model to continue this work.') + '\n')
                        elif status == 'CANCELLED':
                            self.text(session, 'Cancelled. Kel stopped this work; nothing else will run for it.\n')
                        elif status == 'PAUSED':
                            self.text(session, 'Paused. Say "continue" when you want Kel to pick it back up.\n')
                        self._resurface(session, cid)
                        return {'stopReason': 'cancelled' if status == 'CANCELLED' else 'end_turn'}
                elif submission['state'] in ('DISPATCHED', 'SETTLED'):
                    self._resurface(session, cid)
                    return {'stopReason': 'end_turn'}
                if submission['state'] == 'PLANNING' and not ack_seq and not submission.get('job_id'):
                    self._stream_words(session, sid, stream)
                else:
                    self.closed.wait(self.poll_interval)
            return {'stopReason': 'end_turn'}
        finally:
            with self.lock:
                # Only clear our own stream record: a superseding side-question
                # prompt owns this session now.
                if self.active.get(session) is active:
                    self.active.pop(session, None)


def run(data, source=sys.stdin, output=sys.stdout):
    write_lock = threading.Lock()
    def emit(message):
        with write_lock:
            output.write(json.dumps(message, ensure_ascii=False) + '\n')
            output.flush()
    host = ACPHost(ServiceClient(data), emit)
    def handle(message):
        try:
            result = host.dispatch(message['method'], message.get('params') or {})
            response = {'jsonrpc': '2.0', 'id': message.get('id'), 'result': result}
        except Exception as error:
            response = {'jsonrpc': '2.0', 'id': message.get('id'),
                        'error': {'code': error_code(error), 'message': str(error)}}
        if 'id' in message and not host.closed.is_set():
            emit(response)
    try:
        for line in source:
            try:
                message = json.loads(line)
                if not isinstance(message, dict) or not isinstance(message.get('method'), str):
                    raise ValueError('Expected a JSON-RPC request')
            except Exception:
                emit({'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Invalid JSON-RPC request'}})
                continue
            if message['method'] == 'session/prompt':
                threading.Thread(target=handle, args=(message,), daemon=True).start()
            else:
                handle(message)
    finally:
        host.closed.set()


def main():
    # ACP is UTF-8 JSON, independent of the Windows console code page.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='strict')
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True)
    args = parser.parse_args()
    run(args.data)


if __name__ == '__main__':
    main()
