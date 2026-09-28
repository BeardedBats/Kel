"""OpenAI-compatible API models as bounded text workers: DeepSeek and OpenRouter (Routing 2 §5.6).

Design: `docs/v2/design/ROUTING_2.md` §5.6; intent document §12 ("DeepSeek and similar API models:
Kel can use them as raw fast/cheap workers"). One adapter, two endpoints:

- DeepSeek (`https://api.deepseek.com`, key `DEEPSEEK_API_KEY`): `deepseek-flash` is DeepSeek-V4.1-Flash
  (DeepSeek's own model list, read 2026-09-27) — the D-67 Utility model.
- OpenRouter (`https://openrouter.ai/api/v1`, key `OPENROUTER_API_KEY`): a second route to catalog
  models (DeepSeek Flash = `deepseek/deepseek-v4.1-flash` there); it reports each call's cost when
  asked (`usage: {include: true}`).

Keys stay in the desktop's OS-backed custody and reach only the engine's environment at spawn, like
the Anthropic key; they travel only in the request header and are redacted from anything durable.
Without a key the adapter is simply not registered and Settings says the key is needed. Text in, text
out: no tools, no files, no images; the result carries the model the API says answered and its usage.
"""
import json
import os
import time
import urllib.error
import urllib.request

from .core import uid
from .internal import LEAF_SYSTEM, redact

ENDPOINTS = {
    'deepseek': {'base_url': 'https://api.deepseek.com', 'env': 'DEEPSEEK_API_KEY', 'label': 'DeepSeek API',
                 'default_model': 'deepseek-flash'},
    'openrouter': {'base_url': 'https://openrouter.ai/api/v1', 'env': 'OPENROUTER_API_KEY',
                   'label': 'OpenRouter', 'default_model': 'deepseek/deepseek-v4.1-flash'},
}
# D-72 item 4: OpenRouter carries only DeepSeek Flash for now (one setting to widen later).
ALLOWED_MODELS = {'openrouter': ('deepseek/deepseek-v4.1-flash',)}
INPUT_LIMIT = 60000
RESPONSE_LIMIT = 2_000_000


def has_key(provider, env=None):
    env = os.environ if env is None else env
    item = ENDPOINTS.get(provider)
    return bool(item and env.get(item['env']))


class OpenAICompatAdapter:
    """A bounded chat-completions worker for one OpenAI-compatible endpoint."""

    def __init__(self, provider, model=None, timeout=90, max_tokens=4096, transport=None, effort=None,
                 stream_transport=None):
        if provider not in ENDPOINTS:
            raise ValueError('Unknown API model provider')
        self.provider = provider
        self.model = model or ENDPOINTS[provider]['default_model']
        self.timeout = min(max(timeout, 1), 180)
        self.max_tokens = min(max_tokens, 8192)
        self.transport = transport or self._request
        # D-75.1: a reply streams its words when asked (`on_text`); a test transport streams only if
        # it brings its own streaming transport.
        self.stream_transport = stream_transport or (self._stream_request if transport is None else None)
        self.effort = effort
        self.on_refusal = None
        from .model_prefs import model_label
        self.label = model_label(self.model) or ENDPOINTS[provider]['label']

    def _stream_request(self, body, timeout, on_text, cancel=None):
        """A streamed chat completion (server-sent events), shaped like the non-streamed answer."""
        body = dict(body, stream=True)
        if self.provider == 'deepseek':
            body['stream_options'] = {'include_usage': True}
        request = self._build(body)
        text, model, usage, size = [], None, None, 0
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                for raw in response:
                    size += len(raw)
                    if size > RESPONSE_LIMIT:
                        raise RuntimeError('Provider response exceeded its byte limit')
                    if cancel is not None and cancel.is_set():
                        break
                    line = raw.decode('utf-8', 'replace').strip()
                    if not line.startswith('data:'):
                        continue
                    payload = line[5:].strip()
                    if payload == '[DONE]':
                        break
                    try:
                        chunk = json.loads(payload)
                    except ValueError:
                        continue
                    model = chunk.get('model') or model
                    if isinstance(chunk.get('usage'), dict):
                        usage = chunk['usage']
                    for choice in chunk.get('choices') or []:
                        piece = ((choice or {}).get('delta') or {}).get('content')
                        if isinstance(piece, str) and piece:
                            text.append(piece)
                            try:
                                on_text(''.join(text))
                            except Exception:
                                pass  # showing words early never changes the answer
        except urllib.error.HTTPError as exc:
            raise RuntimeError('HTTP %s: %s' % (exc.code, self._error_detail(exc) or exc.reason)) from None
        return {'choices': [{'message': {'content': ''.join(text)}}], 'model': model, 'usage': usage}

    @staticmethod
    def _error_detail(exc):
        try:
            detail = exc.read(4000).decode('utf-8', 'replace')
            message = (json.loads(detail).get('error') or {})
            return message.get('message') if isinstance(message, dict) else message
        except Exception:
            return None

    def _build(self, body):
        item = ENDPOINTS[self.provider]
        key = os.environ.get(item['env'])
        if not key:
            raise RuntimeError('%s is needed for %s' % (item['env'], item['label']))
        headers = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}
        if self.provider == 'openrouter':
            headers.update({'X-Title': 'Kel'})
        return urllib.request.Request(item['base_url'].rstrip('/') + '/chat/completions',
                                      data=json.dumps(body).encode('utf-8'), headers=headers)

    def _request(self, body, timeout):
        item = ENDPOINTS[self.provider]
        key = os.environ.get(item['env'])
        if not key:
            raise RuntimeError('%s is needed for %s' % (item['env'], item['label']))
        headers = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}
        if self.provider == 'openrouter':
            headers.update({'X-Title': 'Kel'})
        request = urllib.request.Request(item['base_url'].rstrip('/') + '/chat/completions',
                                         data=json.dumps(body).encode('utf-8'), headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read(RESPONSE_LIMIT + 1)
        except urllib.error.HTTPError as exc:
            # Keep the service's own words (a refused or unknown model says so), never the key.
            try:
                detail = exc.read(4000).decode('utf-8', 'replace')
                message = (json.loads(detail).get('error') or {})
                message = message.get('message') if isinstance(message, dict) else message
            except Exception:
                message = None
            raise RuntimeError('HTTP %s: %s' % (exc.code, message or exc.reason)) from None
        if len(raw) > RESPONSE_LIMIT:
            raise RuntimeError('Provider response exceeded its byte limit')
        return json.loads(raw)

    def execute(self, prompt, run_id=None, session_id=None, cancel=None, images=None, system=None, on_text=None):
        run_id = run_id or uid()
        if images:
            return {'outcome': 'FAILED', 'error': '%s here reads text only' % ENDPOINTS[self.provider]['label']}
        if len(prompt) > INPUT_LIMIT:
            return {'outcome': 'FAILED', 'error': 'Context exceeds the %d-character input budget; refusing '
                                                  'silent truncation' % INPUT_LIMIT}
        allowed = ALLOWED_MODELS.get(self.provider)
        if allowed and self.model not in allowed:
            return {'outcome': 'FAILED', 'provider': self.provider, 'wall_ms': 0,
                    'error': '%s runs only DeepSeek Flash in Kel for now' % ENDPOINTS[self.provider]['label']}
        if cancel and cancel.is_set():
            return {'outcome': 'CANCELLED'}
        body = {'model': self.model, 'max_tokens': self.max_tokens, 'stream': False,
                'messages': [{'role': 'system', 'content': system or LEAF_SYSTEM.replace(
                    ' Return your artifact with submit_result.', ' Return only the requested result.')},
                    {'role': 'user', 'content': prompt}]}
        if self.provider == 'openrouter':
            body['usage'] = {'include': True}  # OpenRouter reports the call's cost
        started = time.monotonic()
        try:
            if on_text is not None and self.stream_transport is not None:
                data = self.stream_transport(body, self.timeout, on_text, cancel)
            else:
                data = self.transport(body, self.timeout)
            choices = data.get('choices') or []
            message = (choices[0] or {}).get('message') if choices else None
            text = (message or {}).get('content') if isinstance(message, dict) else None
            if not isinstance(text, str) or not text.strip():
                result = {'outcome': 'FAILED', 'error': 'The model returned no answer'}
            elif len(text.encode('utf-8')) > 1_000_000:
                result = {'outcome': 'FAILED', 'error': 'Output limit'}
            else:
                result = {'outcome': 'SUCCESS', 'text': text, 'session_id': run_id,
                          'model_used': data.get('model') or self.model, 'reasoning_used': 'auto',
                          'usage': data.get('usage') if isinstance(data.get('usage'), dict) else None}
        except Exception as exc:
            result = {'outcome': 'FAILED', 'error': redact(type(exc).__name__ + ': ' + str(exc))}
        result.update(provider=self.provider, wall_ms=int((time.monotonic() - started) * 1000))
        if result['outcome'] == 'FAILED' and self.on_refusal is not None:
            try:
                self.on_refusal(result.get('error'), None)
            except Exception:
                pass
        return result
