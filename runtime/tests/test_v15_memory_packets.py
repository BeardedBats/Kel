"""V1.5 G6: memory lifecycle reaches the composed context packet end to end.

MEM-01..15 prove the memory store itself. These probes prove the *user-visible* contract: a
retracted, forgotten, or stale memory never appears in a packet, a forgotten value leaves no bytes
or search hits behind, and one project's retraction never touches another project's packet.
"""
import tempfile
import unittest
from pathlib import Path

from kel.composer import Composer
from kel.context import Context
from kel.memory import Memory
from kel.projectmap import ProjectMap
from kel.core import Store


class PacketLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.store = Store(base / 'data')
        self.context = Context(self.store)
        (base / 'proj1').mkdir()
        (base / 'proj2').mkdir()
        self.p1 = self.context.project('Packets', str(base / 'proj1'), 'packet tests')
        self.p2 = self.context.project('Other', str(base / 'proj2'), 'packet tests')
        self.cid = self.context.conversation(self.p1)
        self.memory = Memory(self.store)
        self.composer = Composer(self.store, self.memory, ProjectMap(self.store))

    def memory_refs(self, packet):
        return [s['ref'] for s in packet['sources'] if s['kind'] == 'memories']

    def test_retracted_memory_leaves_the_packet(self):
        mid = self.memory.record(self.p1, 'decision', 'deploy.target',
                                 {'statement': 'Deploy to staging first'},
                                 'Deploy target decision: staging first.',
                                 source_type='user_instruction', source_ref='chat:1')
        before = self.composer.build(self.p1, 'What is the deploy target decision?',
                                     conversation_id=self.cid)
        self.assertIn(mid, self.memory_refs(before))
        self.memory.retract(mid, reason='superseded by policy')
        after = self.composer.build(self.p1, 'What is the deploy target decision?',
                                    conversation_id=self.cid)
        self.assertNotIn(mid, self.memory_refs(after))

    def test_stale_memory_leaves_the_packet_and_stays_visible_in_records(self):
        mid = self.memory.record(self.p1, 'command', 'build.command',
                                 {'command': 'bun run build'}, 'Desktop build command.',
                                 source_type='config_inspection',
                                 source_ref='desktop/package.json', source_digest='sha256:old')
        packet = self.composer.build(self.p1, 'Which build command do we use?',
                                     conversation_id=self.cid)
        self.assertIn(mid, self.memory_refs(packet))
        self.assertEqual(self.memory.revalidate(self.p1,
                                                {'desktop/package.json': 'sha256:new'}), [mid])
        after = self.composer.build(self.p1, 'Which build command do we use?',
                                    conversation_id=self.cid)
        self.assertNotIn(mid, self.memory_refs(after))
        visible = [r['id'] for r in self.memory.records(self.p1, status='stale')]
        self.assertIn(mid, visible, 'a stale memory stays inspectable, never silently deleted')

    def test_forgotten_memory_leaves_no_bytes_or_search_hits(self):
        marker = 'forget-me-marker-7c1f'
        mid = self.memory.record(self.p1, 'fact', 'scratch.note',
                                 {'statement': marker}, 'Temporary note ' + marker + '.',
                                 source_type='repo_inspection', source_ref='scratch')
        self.assertTrue([r for r in self.memory.select(self.p1, purpose='t', query=marker)])
        self.memory.forget(mid)
        self.assertEqual(self.memory.select(self.p1, purpose='t', query=marker), [])
        packet = self.composer.build(self.p1, marker, conversation_id=self.cid)
        self.assertNotIn(mid, self.memory_refs(packet))
        for path in (self.store.root).rglob('*'):
            if path.is_file():
                raw = path.read_bytes()
                self.assertNotIn(marker.encode(), raw, str(path))

    def test_retraction_in_one_project_never_touches_another_packet(self):
        keep = self.memory.record(self.p2, 'decision', 'deploy.target',
                                  {'statement': 'Deploy to production directly'},
                                  'Other project deploys straight to production.',
                                  source_type='user_instruction', source_ref='chat:2')
        mid = self.memory.record(self.p1, 'decision', 'deploy.target',
                                 {'statement': 'Deploy to staging first'},
                                 'This project deploys to staging first.',
                                 source_type='user_instruction', source_ref='chat:3')
        other = self.composer.build(self.p2, 'Where do we deploy?',
                                    conversation_id=self.context.conversation(self.p2))
        self.assertIn(keep, self.memory_refs(other))
        self.memory.retract(mid, reason='local change')
        other_again = self.composer.build(self.p2, 'Where do we deploy?',
                                          conversation_id=self.context.conversation(self.p2))
        self.assertIn(keep, self.memory_refs(other_again),
                      'another project\'s retraction never affects this packet')


if __name__ == '__main__':
    unittest.main()
