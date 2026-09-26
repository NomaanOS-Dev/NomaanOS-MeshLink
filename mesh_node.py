import socket
import threading
import json
import time
import os
import hmac
import hashlib
import sys

DEFAULT_PORT = 9876
BROADCAST_ADDR = "255.255.255.255"
SHARED_MESH_KEY = b"nomaanos-mesh-secret-v1"

class MeshLinkNode:
    def __init__(self, node_id=None, port=DEFAULT_PORT):
        self.port = port
        self.node_id = node_id or f"node-{os.uname().nodename}-{int(time.time()) % 10000}"
        self.peers = {}  # {node_id: {"ip": ip, "last_seen": ts, "status": "ALIVE", "uptime": s}}
        self.running = False
        self._lock = threading.Lock()

    def _sign_payload(self, data_dict):
        serialized = json.dumps(data_dict, sort_keys=True).encode("utf-8")
        signature = hmac.new(SHARED_MESH_KEY, serialized, hashlib.sha256).hexdigest()
        return {"data": data_dict, "sig": signature}

    def _verify_payload(self, packet):
        try:
            data = packet.get("data")
            sig = packet.get("sig")
            expected = hmac.new(SHARED_MESH_KEY, json.dumps(data, sort_keys=True).encode("utf-8"), hashlib.sha256).hexdigest()
            return hmac.compare_digest(sig, expected)
        except Exception:
            return False

    def start_receiver(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception:
            pass
        sock.bind(("", self.port))
        sock.settimeout(1.0)

        while self.running:
            try:
                data, addr = sock.recvfrom(4096)
                packet = json.loads(data.decode("utf-8"))
                if not self._verify_payload(packet):
                    continue

                payload = packet["data"]
                sender_id = payload.get("node_id")
                if sender_id and sender_id != self.node_id:
                    with self._lock:
                        self.peers[sender_id] = {
                            "ip": addr[0],
                            "port": addr[1],
                            "last_seen": time.time(),
                            "status": "ALIVE",
                            "role": payload.get("role", "edge-peer")
                        }
            except socket.timeout:
                continue
            except Exception:
                pass
        sock.close()

    def start_broadcaster(self, interval=2.0):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while self.running:
            try:
                payload = {
                    "node_id": self.node_id,
                    "timestamp": time.time(),
                    "role": "SovereignAI-Edge",
                    "sys_arch": os.uname().machine
                }
                signed_packet = self._sign_payload(payload)
                sock.sendto(json.dumps(signed_packet).encode("utf-8"), (BROADCAST_ADDR, self.port))
            except Exception:
                pass
            time.sleep(interval)
        sock.close()

    def start_failure_detector(self, interval=2.0):
        while self.running:
            now = time.time()
            with self._lock:
                for peer_id, info in self.peers.items():
                    delta = now - info["last_seen"]
                    if delta > 8.0:
                        info["status"] = "DEAD"
                    elif delta > 4.0:
                        info["status"] = "SUSPECT"
                    else:
                        info["status"] = "ALIVE"
            time.sleep(interval)

    def start(self):
        self.running = True
        t_recv = threading.Thread(target=self.start_receiver, daemon=True)
        t_bcast = threading.Thread(target=self.start_broadcaster, daemon=True)
        t_fd = threading.Thread(target=self.start_failure_detector, daemon=True)

        t_recv.start()
        t_bcast.start()
        t_fd.start()

    def get_topology(self):
        with self._lock:
            return {
                "local_node": self.node_id,
                "active_peer_count": len([p for p in self.peers.values() if p["status"] == "ALIVE"]),
                "peers": self.peers
            }

    def stop(self):
        self.running = False
