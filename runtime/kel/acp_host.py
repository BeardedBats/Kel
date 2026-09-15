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
    def __init__(self, client, emit, poll_interval=.25):
        self.client, self.emit, self.poll_interval = client, emit, poll_interval
        self.active = {}
        self.lock = threading.RLock()
        self.closed = threading.Event()

    def update(self, session, update):
        if not self.closed.is_set():
            self.emit({'jsonrpc': '2.0', 'method': 'session/update',
                       'params': {'sessionId': session, 'update': update}})

    def text(self, session, text):
        self.update(session, {'sessionUpdate': 'agent_message_chunk', 'content': {'type': 'text', 'text': text}})

    def session(self, session):
        if not isinstance(session, str) or not session.startswith('kel:'):
            raise ValueError('Unknown Kel session')
        cid = session[4:]
        state = self.client.state(cid)
        if not any(c['id'] == cid for c in state['conversations']):
            raise ValueError('Kel conversation no longer exists')
        return cid, state

    def dispatch(self, method, params):
        if method == 'initialize':
            from .service import ENGINE_VERSION
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
            # greenfield intent. Default to the unrooted project.
            project = 'default'
            cid = self.client.call('/api/conversation', {'project': project})['id']
            if record:
                record.parent.mkdir(exist_ok=True)
                temporary = record.with_suffix('.' + uuid.uuid4().hex + '.tmp')
                with temporary.open('w', encoding='utf-8') as handle:
                    json.dump({donor_id: cid}, handle)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, record)
            return {'sessionId': 'kel:' + cid}
        if method == 'session/load':
            session = params['sessionId']
            _, state = self.session(session)
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
        raise ValueError('Unsupported ACP method: ' + method)

    def content(self, cid, blocks):
        texts, attachments = [], []
        for index, block in enumerate(blocks):
            kind = block.get('type')
            if kind == 'text':
                texts.append(block['text'])
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
                if not path.is_file() or not 0 < path.stat().st_size <= 5_000_000:
                    raise ValueError('Attachment must be a file between 1 byte and 5 MB')
                raw = path.read_bytes()
                name = path.name
                mime = block.get('mimeType') or mimetypes.guess_type(name)[0] or 'text/plain'
            else:
                raise ValueError('Unsupported ACP content type: ' + str(kind))
            attachments.append(self.client.call('/api/attach', {'conversation': cid, 'name': name,
                                                                 'mime': mime, 'content': base64.b64encode(raw).decode()})['id'])
        text = '\n'.join(texts).strip()
        if not text:
            raise ValueError('Add a text request with the attachment')
        return text, attachments

    def prompt(self, params):
        session = params['sessionId']
        cid, baseline = self.session(session)
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
            sid = 'acp-' + uuid.uuid4().hex
            self.client.call('/api/send', {'id': sid, 'conversation': cid, 'text': text, 'attachments': attachments})
            seen = {m['seq'] for m in baseline['messages']}
            last_status = None
            cancelled_job = None
            while not self.closed.is_set():
                state = self.client.state(cid)
                submission = next((s for s in state['submissions'] if s['id'] == sid), None)
                for message in state['messages']:
                    if message['seq'] not in seen:
                        seen.add(message['seq'])
                        if message['role'] == 'assistant':
                            self.text(session, message['text'] + '\n\n')
                if not submission:
                    raise RuntimeError('Kel lost the submitted request record')
                if submission['state'] in ('FAILED', 'INTERRUPTED'):
                    self.text(session, 'Kel could not plan this request: ' + (submission.get('error') or submission['state']))
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
                                              'toolCallId': job_id, 'title': 'Kel work: ' + status.lower().replace('_', ' '),
                                              'kind': 'other', 'status': 'in_progress'})
                        last_status = status
                    if status in ('CLOSED', 'CANCELLED', 'PAUSED', 'AWAITING_USER', 'WAITING_RESOURCE'):
                        verdict = job.get('verdict') or 'UNCERTAIN'
                        # Assessment closes the job before publication commits its final reply.
                        if status == 'CLOSED' and not any(m.get('job_id') == job_id and m['role'] == 'assistant' for m in state['messages']):
                            self.closed.wait(self.poll_interval)
                            continue
                        terminal = status in ('CLOSED', 'CANCELLED')
                        self.update(session, {'sessionUpdate': 'tool_call_update', 'toolCallId': job_id,
                                              'status': 'completed' if status == 'CLOSED' and verdict == 'VERIFIED' else ('failed' if terminal else 'pending'),
                                              'title': 'Kel work: ' + status + ' / ' + verdict})
                        if status == 'AWAITING_USER':
                            approvals = state.get('approvals') or []
                            pending = [a for a in approvals if a.get('job_id') == job_id]
                            summary = ''
                            if pending:
                                summary = pending[0].get('action_summary') or ServiceClient.approval_summary(pending[0].get('action'))
                            self.text(session, explain_approval(str(summary)) + '\n')
                        elif status == 'WAITING_RESOURCE':
                            note = explain_failure(job)
                            self.text(session, (note or ('Work state: WAITING_RESOURCE. Verification: ' + verdict + '.')) + '\n')
                        elif status != 'CLOSED' and (not terminal or verdict != 'VERIFIED'):
                            # A settled job already streamed its publication reply
                            # (with its trust summary) and the card title carries
                            # the verdict; only unresolved or cancelled states
                            # still need this one-line status.
                            self.text(session, 'Work state: ' + status + '. Verification: ' + verdict + '.\n')
                        return {'stopReason': 'cancelled' if status == 'CANCELLED' else 'end_turn'}
                elif submission['state'] == 'DISPATCHED':
                    return {'stopReason': 'end_turn'}
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
                        'error': {'code': -32000, 'message': str(error)}}
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
