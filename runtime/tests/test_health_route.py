"""CP-2 / ST-23: the desktop's cheap engine routes, over the real authenticated HTTP service.

`/api/health` is the 5 s liveness ping (no database work); `/api/conversations` gives start-up the
message and job counts it needs to skip empty chats in one read.
"""
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from kel import service as kel_service


class HealthRouteTests(unittest.TestCase):
    def setUp(self):
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('ANTHROPIC_API_KEY', None)
        os.environ['KEL_REVIEWER'] = 'none'
        os.environ['KEL_SKIP_TELEMETRY'] = '1'
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.root = Path(self.tmp.name) / 'engine'
        self.root.mkdir(parents=True)
        self.engine = threading.Thread(target=kel_service.serve, args=(str(self.root), 0), daemon=True)
        self.engine.start()
        self.descriptor = self._wait_for_engine()
        self.addCleanup(self._stop)

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def _stop(self):
        try:
            self.request('/api/shutdown-idle', {})
        except Exception:
            pass
        self.engine.join(timeout=20)

    def _wait_for_engine(self):
        path = self.root / 'desktop-session.json'
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                data = json.loads(path.read_text(encoding='utf-8-sig'))
                if data.get('url') and data.get('token'):
                    return data
            except Exception:
                pass
            time.sleep(0.1)
        self.fail('the engine did not come up')

    def request(self, route, body=None, token=True):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + self.descriptor['token']
        request = urllib.request.Request(self.descriptor['url'].rstrip('/') + route,
                                         data=None if body is None else json.dumps(body).encode('utf-8'),
                                         headers=headers, method='GET' if body is None else 'POST')
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))

    def test_health_answers_without_state_and_still_needs_the_session(self):
        health = self.request('/api/health')
        self.assertEqual(health['ok'], True)
        self.assertEqual(health['engine_version'], kel_service.ENGINE_VERSION)
        with self.assertRaises(urllib.error.HTTPError) as refused:
            self.request('/api/health', token=False)
        self.assertEqual(refused.exception.code, 403)

    def test_conversations_carry_their_counts(self):
        cid = self.request('/api/conversation', {'project': 'default'})['id']
        listed = {row['id']: row for row in self.request('/api/conversations')['conversations']}
        self.assertEqual((listed[cid]['message_count'], listed[cid]['job_count']), (0, 0))
        self.assertIn('main', listed)


if __name__ == '__main__':
    unittest.main()
