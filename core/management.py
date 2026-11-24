"""Management STATE line encoding/decoding; pure shared protocol helper."""
from __future__ import annotations
import json
from .protocol import ProtocolError
from .state import State
from .zones import Zone, Signal

MANAGEMENT_PORT = 5001


def state_line(state: State, sequence: int) -> bytes:
    if sequence < 0:
        raise ValueError("sequence must be nonnegative")
    return (json.dumps({"type": "STATE", "sequence": sequence,
                        "active_zone": state.active_zone.value,
                        "signal": state.signal.value,
                        "brake": state.brake}, sort_keys=True) + "\n").encode("utf-8")


def parse_state(line: bytes):
    try:
        data = json.loads(line)
        if not isinstance(data, dict) or data.get("type") != "STATE":
            raise ValueError("not STATE")
        if type(data.get("sequence")) is not int or data["sequence"] < 0:
            raise ValueError("bad sequence")
        if type(data.get("brake")) is not bool:
            raise ValueError("bad brake")
        state = State(Zone(data["active_zone"]), Signal(data["signal"]), data["brake"])
        return data["sequence"], state
    except (ValueError, TypeError, KeyError, UnicodeError) as exc:
        raise ProtocolError("invalid STATE: " + str(exc)) from exc
