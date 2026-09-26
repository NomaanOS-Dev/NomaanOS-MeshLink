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
    def __init__(self, node_id=None, port=DEFAULT_PORT, target_ports=None):
        self.port = port
        self.target_ports = target_ports or [DEFAULT_PORT]
        self.node_id = node_id or f"node-{os.uname().nodename}-{int(time.time() * 1000) % 100000}"
        self.peers = {}
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
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except Exception:
                pass
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception:
            pass
        sock.bind(("", self.port))
        sock.settimeout(0.5)

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
                            "last_seen": time.time(),
                            "status": "ALIVE",
                            "role": payload.get("role", "edge-peer")
                        }
            except socket.timeout:
                continue
            except Exception:
                pass
        sock.close()

    def start_broadcaster(self, interval=1.0):
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
                msg = json.dumps(signed_packet).encode("utf-8")
                
                # Send to all target discovery ports
                for p in self.target_ports:
                    # Send loopback for local tests and broadcast for network
                    try:
                        sock.sendto(msg, ("127.0.0.1", p))
                    except Exception:
                        pass
                    try:
                        sock.sendto(msg, (BROADCAST_ADDR, p))
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(interval)
        sock.close()

    def start_failure_detector(self, interval=1.5):
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
        threading.Thread(target=self.start_receiver, daemon=True).start()
        threading.Thread(target=self.start_broadcaster, daemon=True).start()
        threading.Thread(target=self.start_failure_detector, daemon=True).start()

    def get_topology(self):
        with self._lock:
            return {
                "local_node": self.node_id,
                "active_peer_count": len([p for p in self.peers.values() if p["status"] == "ALIVE"]),
                "peers": dict(self.peers)
            }

    def stop(self):
        self.running = False
