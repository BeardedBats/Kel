"""Single context-composition path for Commander, workers, reviewers, and continuation.

V1.3 C4 (docs/v1.3/KEL_V1.3_ARCHITECTURE.md 3-4, KEL_V1.3_CONTINUATION_SPEC.md).
Packets are provenance-labeled, budgeted, digest-stable and inspectable. The structure is
persisted for every packet; full text is persisted only for job-linked packets.
"""
import contextlib
import hashlib
import json
import re
import time

from .core import PolicyError, digest
from .projectmap import ensure_schema

# Context-fencing + sanitizer adapted from NousResearch/hermes-agent (MIT license),
# agent/memory_manager.py:167-177, inspected revision 40f2702b22a3. Injected context is
# wrapped in <memory-context> fences; markers are stripped from model output so a worker
# cannot forge provenance (mirrored test: fence stripping, case-insensitive).
_FENCE_TAG_RE = re.compile(r'</?\s*memory-context\s*>', re.IGNORECASE)
_INTERNAL_CONTEXT_RE = re.compile(
    r'<\s*memory-context\s*>[\s\S]*?</\s*memory-context\s*>', re.IGNORECASE)

TRUST_LABELS = {1: 'current instruction', 2: 'user-confirmed', 3: 'verified source',
                4: 'accepted work', 5: 'reviewed evidence', 6: 'inferred', 7: 'external (untrusted)'}


def sanitize_context(text):
    """Strip injected context blocks and fence markers from model output (hermes-adapted)."""
    if not isinstance(text, str):
        return text
    for pattern in (_INTERNAL_CONTEXT_RE, _FENCE_TAG_RE):
        text = pattern.sub('', text)
    return text


def fence(label, text):
    """Wrap injected context in provenance fences (sanitize_context strips these)."""
    return '<memory-context>\n[source: %s]\n%s\n</memory-context>' % (label, text)


def _tokens(text):
    return set(re.findall(r'[a-z0-9]{4,}', str(text).lower()))


class Composer:
    def __init__(self, store, memory, projectmap):
        self.store = store
        self.memory = memory
        self.projectmap = projectmap
        ensure_schema(store)

    # ---- sources ---------------------------------------------------------

    def _source(self, kind, ref, text, trust, reason, *, must=False):
        return {'kind': kind, 'ref': ref, 'text': text, 'trust': trust, 'reason': reason,
                'chars': len(text), 'digest': hashlib.sha256(text.encode()).hexdigest()[:16],
                '_must': must}

    def _add_memories(self, project_id, request, purpose, sources, omitted):
        wanted = _tokens(request)
        candidates = self.memory.select(project_id, purpose=purpose, limit=30, max_chars=12000)
        selected = []
        for record in candidates:
            record_tokens = _tokens(record['topic']) | _tokens(record['summary']) | _tokens(record['value'])
            if wanted & record_tokens:
                selected.append(record)
            elif record['user_confirmed'] and record['type'] in ('decision', 'preference'):
                selected.append(record)  # user-confirmed project decisions always ride along
        conflict_refs = set()
        for c in self.memory.conflicts(project_id):
            conflict_refs.add(c['memory_a'])
            conflict_refs.add(c['memory_b'])
        used = 0
        for record in selected[:12]:
            if record['id'] in conflict_refs:
                reason = 'matches the request (open conflict: user choice pending)'
            elif record['user_confirmed'] and record['type'] in ('decision', 'preference'):
                reason = 'user-confirmed project decision'
            else:
                reason = 'matches the request'
            label = '%s / trust %d (%s)' % (record['id'], record['trust'],
                                            TRUST_LABELS.get(record['trust'], 'unknown'))
            text = fence(label, '[%s] %s' % (record['topic'], record['summary']))
            used += len(text)
            if used > 6000:
                omitted.append({'kind': 'memories', 'ref': record['id'], 'reason': 'size cap'})
                continue
            must = record['trust'] <= 2 or record['type'] == 'decision'
            sources.append(self._source('memories', record['id'], text, record['trust'],
                                        reason, must=must))
        for record in self.memory.records(project_id, status='active', limit=200):
            if record['trust'] >= 6 and not any(s['ref'] == record['id'] for s in sources):
                omitted.append({'kind': 'memories', 'ref': record['id'],
                                'reason': 'below trust threshold (not included by default)'})
                if len([o for o in omitted if o['kind'] == 'memories']) >= 5:
                    break
    def _add_job(self, job, sources):
        milestones = []
        if isinstance(job.get('milestones'), dict):
            for mid, milestone in job['milestones'].items():
                entry = {'id': mid, 'state': milestone.get('state'),
                         'attempts': milestone.get('attempts')}
                artifact = milestone.get('artifact') or {}
                if artifact.get('sha256'):
                    entry['artifact'] = artifact['sha256'][:16]
                milestones.append(entry)
        contract = job.get('contract') or {}
        text = json.dumps({'state': job.get('state'), 'verdict': job.get('verdict'),
                           'request': str(contract.get('request', ''))[:400],
                           'milestones': milestones,
                           'contract_version': job.get('contract_version')}, sort_keys=True)
        sources.append(self._source('job_state', str(job.get('id')), text, 4,
                                    'current job state (durable source of truth)', must=True))
        for mid, milestone in (job.get('milestones') or {}).items():
            artifact = milestone.get('artifact') or {}
            if artifact.get('sha256'):
                sources.append(self._source('evidence', '%s:%s' % (job.get('id'), mid),
                                            artifact['sha256'], 4,
                                            'accepted milestone artifact digest'))

    def _add_map(self, project_id, sources, omitted):
        latest = self.projectmap.get(project_id)
        if not latest:
            omitted.append({'kind': 'map_sections', 'ref': project_id,
                            'reason': 'no project map yet (manual refresh available)'})
            return
        count = 0
        for name in ('identity', 'execution', 'conventions', 'architecture', 'state'):
            if count >= 4:
                break
            section = latest['sections'].get(name)
            if not section:
                continue
            body = json.dumps(section.get('content'), sort_keys=True, default=str)
            if section.get('summary'):
                body = section['summary'] + '\n' + body
            body = body[:2000]
            label = 'map:%s@v%d (%s)' % (name, latest['version'], section.get('trust', 'verified'))
            sources.append(self._source(
                'map_sections', 'map:%s@v%d' % (name, latest['version']), fence(label, body), 3,
                'project map section %s, freshness v%d' % (name, latest['version'])))
            count += 1

    def _add_recent(self, conversation_id, recent_limit, recent_chars, sources, omitted):
        with contextlib.closing(self.store.connect()) as db:
            rows = [dict(r) for r in db.execute(
                'SELECT role, text FROM messages WHERE conversation_id=?'
                ' ORDER BY seq DESC LIMIT ?', (conversation_id, recent_limit))]
        rows.reverse()
        lines = ['[%s] %s' % (row['role'], str(row['text'])[:400]) for row in rows]
        while lines and sum(len(line) for line in lines) > recent_chars:
            lines.pop(0)
        if lines:
            sources.append(self._source(
                'recent_turns', 'conversation:' + conversation_id, '\n'.join(lines), 5,
                'bounded recent conversation window (%d messages)' % len(lines)))
        elif rows:
            omitted.append({'kind': 'recent_turns', 'ref': 'conversation:' + conversation_id,
                            'reason': 'window cap'})

    def _add_attachments(self, attachments, sources):
        for att in attachments or ():
            name = str(att.get('name', 'attachment'))
            if isinstance(att.get('text'), str):
                body = att['text'][:4000]
            else:
                body = '[binary attachment: %s sha256=%s]' % (name, str(att.get('sha256', ''))[:16])
            sources.append(self._source('attachments', name, body, 5,
                                        'explicitly attached by the user'))
    # ---- packet assembly -------------------------------------------------

    def build(self, project_id, request, *, conversation_id='main', job=None,
              continuation=None, attachments=(), purpose='plan', budget_chars=32000,
              recent_limit=16, recent_chars=8000):
        if not isinstance(request, str) or not request.strip():
            raise PolicyError('A nonempty request is required')
        if type(budget_chars) is not int or not 1000 <= budget_chars <= 200000:
            raise PolicyError('Context budget must be 1000 to 200000 characters')
        sources = [self._source('request', 'request', request, 1, 'the current request',
                                must=True)]
        omitted = []
        self._add_memories(project_id, request, purpose, sources, omitted)
        if job:
            self._add_job(job, sources)
        self._add_map(project_id, sources, omitted)
        self._add_recent(conversation_id, recent_limit, recent_chars, sources, omitted)
        self._add_attachments(attachments, sources)
        conflicts = [{'id': c['id'], 'memory_a': c['memory_a'], 'memory_b': c['memory_b'],
                      'state': c['state']} for c in self.memory.conflicts(project_id)]
        packet = self._pack(project_id, purpose, conversation_id, job, sources, omitted,
                            conflicts, budget_chars)
        self._persist(packet, job)
        return packet

    def _pack(self, project_id, purpose, conversation_id, job, sources, omitted, conflicts,
              budget_chars):
        with contextlib.closing(self.store.connect()) as db:
            for entry in sources:
                if entry['kind'] == 'memories':
                    row = db.execute('SELECT project_id FROM memories WHERE id=?',
                                     (entry['ref'],)).fetchone()
                    if row and row['project_id'] != project_id:
                        raise PolicyError('Context packet crossed a project boundary')
        must = [s for s in sources if s['_must']]
        optional = [s for s in sources if not s['_must']]
        for entry in sources:
            entry.pop('_must', None)
        used = sum(s['chars'] for s in must) + 120
        if used > budget_chars:
            raise PolicyError('Context budget is too small for the request and decisions '
                              '(%d characters needed)' % used)
        included = list(must)
        for entry in optional:
            if used + entry['chars'] <= budget_chars:
                included.append(entry)
                used += entry['chars']
            else:
                omitted.append({'kind': entry['kind'], 'ref': entry['ref'], 'reason': 'budget'})
        basis = {'schema': 1, 'project_id': project_id, 'purpose': purpose,
                 'sources': [{'kind': s['kind'], 'ref': s['ref'], 'trust': s['trust'],
                              'chars': s['chars'], 'digest': s['digest']} for s in included],
                 'omitted': omitted,
                 'conflicts': [c['id'] for c in conflicts]}
        packet_id = 'pkt_' + digest(basis)
        return {'schema': 1, 'packet_id': packet_id, 'project_id': project_id,
                'purpose': purpose, 'conversation_id': conversation_id,
                'job_id': (job or {}).get('id'), 'sources': included, 'omitted': omitted,
                'conflicts': conflicts,
                'size': {'chars': used, 'tokens_est': int(used / 4)}, 'created': time.time()}

    def _persist(self, packet, job):
        if job:
            data = json.dumps(packet, sort_keys=True, default=str)
        else:
            structural = dict(packet)
            structural['sources'] = [
                {key: (value if key != 'text' else
                       {'sha256': hashlib.sha256(value.encode()).hexdigest(),
                        'chars': len(value)})
                 for key, value in entry.items()}
                for entry in packet['sources']]
            data = json.dumps(structural, sort_keys=True, default=str)
        with self.store.transaction() as db:
            db.execute('INSERT OR REPLACE INTO context_packets VALUES(?,?,?,?,?,?,?)',
                       (packet['packet_id'], packet['project_id'], packet.get('job_id'),
                        packet['conversation_id'], packet['purpose'], data, packet['created']))

    def packet(self, packet_id):
        """Inspect a stored packet (full text only for job-linked packets)."""
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM context_packets WHERE packet_id=?',
                             (packet_id,)).fetchone()
        return dict(row) if row else None
