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
INPUT_LIMIT = 60000
RESPONSE_LIMIT = 2_000_000


def has_key(provider, env=None):
    env = os.environ if env is None else env
    item = ENDPOINTS.get(provider)
    return bool(item and env.get(item['env']))


class OpenAICompatAdapter:
    """A bounded chat-completions worker for one OpenAI-compatible endpoint."""

    def __init__(self, provider, model=None, timeout=90, max_tokens=4096, transport=None, effort=None):
        if provider not in ENDPOINTS:
            raise ValueError('Unknown API model provider')
        self.provider = provider
        self.model = model or ENDPOINTS[provider]['default_model']
        self.timeout = min(max(timeout, 1), 180)
        self.max_tokens = min(max_tokens, 8192)
        self.transport = transport or self._request
        self.effort = effort
        self.on_refusal = None
        from .model_prefs import model_label
        self.label = model_label(self.model) or ENDPOINTS[provider]['label']

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

    def execute(self, prompt, run_id=None, session_id=None, cancel=None, images=None, system=None):
        run_id = run_id or uid()
        if images:
            return {'outcome': 'FAILED', 'error': '%s here reads text only' % ENDPOINTS[self.provider]['label']}
        if len(prompt) > INPUT_LIMIT:
            return {'outcome': 'FAILED', 'error': 'Context exceeds the %d-character input budget; refusing '
                                                  'silent truncation' % INPUT_LIMIT}
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
