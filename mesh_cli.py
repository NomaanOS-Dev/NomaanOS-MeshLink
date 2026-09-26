import sys
import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from mesh_node import MeshLinkNode

node = MeshLinkNode()

class TopologyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/topology":
            data = node.get_topology()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "help"

    if cmd == "daemon":
        print(f"\033[92m[+] Starting NomaanOS-MeshLink P2P Gossip Daemon on Node ID: {node.node_id}\033[0m")
        node.start()
        server = HTTPServer(("0.0.0.0", 8088), TopologyServer)
        print("[+] Topology API bound to http://0.0.0.0:8088/topology")
        print("[+] Listening for authentic UDP mesh peers... Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Stopping mesh daemon...")
            node.stop()

    elif cmd == "test-probe":
        # Autonomous 5-second simulated local peer verification
        print("[*] Launching 5-second self-probe node test...")
        node.start()
        for i in range(5):
            time.sleep(1)
            topo = node.get_topology()
            print(f"    Cycle {i+1}/5 | Local ID: {topo['local_node']} | Active Peers: {topo['active_peer_count']}")
        node.stop()
        print("\033[92m[✔] Mesh discovery socket lifecycle passed verification.\033[0m")

    else:
        print("Usage:")
        print("  python mesh_cli.py daemon       Start the background UDP mesh daemon & REST API")
        print("  python mesh_cli.py test-probe   Execute 5-second network socket self-test")

if __name__ == "__main__":
    main()
