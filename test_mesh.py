import unittest
import time
from mesh_node import MeshLinkNode

class TestMeshLink(unittest.TestCase):
    def test_signature_verification(self):
        node = MeshLinkNode(node_id="test-node-1")
        payload = {"sample": "data", "counter": 42}
        signed = node._sign_payload(payload)
        self.assertTrue(node._verify_payload(signed))

        # Tampered payload must fail
        signed["data"]["counter"] = 43
        self.assertFalse(node._verify_payload(signed))

    def test_lifecycle_startup(self):
        node = MeshLinkNode(node_id="test-node-2")
        node.start()
        time.sleep(1.5)
        topo = node.get_topology()
        self.assertEqual(topo["local_node"], "test-node-2")
        node.stop()

if __name__ == "__main__":
    unittest.main()
