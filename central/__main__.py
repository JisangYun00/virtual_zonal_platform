"""Laptop entry point: a console that reads 'ZONE ACTION VALUE' lines and prints each ACK with its RTT.

Start it with bringup/central.sh. One-shot use: echo "REAR SET_BRAKE ON" | python3 -m central
"""
from __future__ import annotations  # builtin generics in hints on Python 3.8

import argparse
import json
import socket
import sys
import time

from core.protocol import PORT, Ack, ProtocolError, command, parse_ack
from core.state import Value
from core.zones import DEFAULT_SUBNET, Action, Signal, Zone, zone_address

USAGE = "'ZONE SET_SIGNAL OFF|LEFT|RIGHT|HAZARD' or 'ZONE SET_BRAKE ON|OFF', e.g. 'REAR SET_BRAKE ON'"


def parse_input(line: str) -> tuple[Zone, Action, Value]:
    words = line.upper().split()
    if len(words) != 3:
        raise ValueError(f"expected {USAGE}")
    zone, action = Zone(words[0]), Action(words[1])
    if action is Action.SET_SIGNAL:
        return zone, action, Signal(words[2])
    if words[2] not in ("ON", "OFF"):
        raise ValueError("SET_BRAKE takes ON or OFF")
    return zone, action, words[2] == "ON"


def send(host: str, request: bytes, timeout: float) -> tuple[Ack, float]:
    with socket.create_connection((host, PORT), timeout=timeout) as sock:
        start = time.perf_counter()  # RTT excludes connect: command sent -> ACK received
        sock.sendall(request)
        reply = sock.makefile("rb").readline()
        rtt_ms = (time.perf_counter() - start) * 1000
    return parse_ack(reply), rtt_ms


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m central",
                                     description=f"Reads one command per line from stdin: {USAGE}.")
    parser.add_argument("--subnet", default=DEFAULT_SUBNET,
                        help="first three octets of the zone addresses (127.0.0 for a local run)")
    parser.add_argument("--timeout", type=float, default=1.0, help="seconds per command")
    args = parser.parse_args(argv)
    if sys.stdin.isatty():
        print(f"type {USAGE}; Ctrl-D to quit", file=sys.stderr)

    request_id = 0
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                zone, action, value = parse_input(line)
            except ValueError as cause:
                print(f"invalid input {line.strip()!r}: {cause}", file=sys.stderr)
                continue
            request_id += 1
            host = zone_address(args.subnet, zone)
            try:
                reply, rtt_ms = send(host, command(request_id, action, value), args.timeout)
            except (OSError, ProtocolError) as cause:
                print(f"{zone.value} {host}:{PORT} failed: {cause}", file=sys.stderr)
                continue
            print(json.dumps({
                "zone": zone.value, "action": action.value, "value": line.split()[2].upper(),
                "request_id": reply.request_id, "status": reply.status.value,
                "active_zone": reply.state.active_zone.value, "signal": reply.state.signal.value,
                "brake": reply.state.brake, "rtt_ms": round(rtt_ms, 3),
            }, sort_keys=True), flush=True)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
