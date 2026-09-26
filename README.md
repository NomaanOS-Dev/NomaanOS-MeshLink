# NomaanOS-MeshLink — Autonomous P2P Mesh Gossip Discovery Engine

[![MeshLink CI](https://github.com/NomaanOS-Dev/NomaanOS-MeshLink/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/NomaanOS-Dev/NomaanOS-MeshLink/actions)

NomaanOS-MeshLink is a zero-dependency, edge-native peer-to-peer discovery daemon designed for autonomous edge swarms, air-gapped nodes, and IoT fleets.

## Architecture & Protocols
* **Transport:** Raw non-blocking UDP broadcast sockets (`255.255.255.255:9876`).
* **Cryptographic Attestation:** Every packet carries a keyed HMAC-SHA256 signature to prevent spoofing or rogue node injection.
* **Failure Detection:** Sliding-window threshold state machine (`ALIVE` -> `SUSPECT` [>4s] -> `DEAD` [>8s]).
* **Topology Observability:** Built-in HTTP micro-daemon exposing `/topology` JSON state.

## Quickstart

```bash
# Run local socket test
python mesh_cli.py test-probe

# Start background discovery node
python mesh_cli.py daemon

Query topology in another shell:
curl -s [http://127.0.0.1:8088/topology](http://127.0.0.1:8088/topology)

