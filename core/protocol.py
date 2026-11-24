"""Wire format: one UTF-8 JSON object per line over TCP. Provisional, see docs/design.md.

Every message shape lives here; both programs build and parse messages only through these functions.
"""
import json
from typing import NamedTuple

from .state import State, Value
from .zones import Action, Signal, Status, Zone

PORT = 5000
MAX_LINE = 4096


class ProtocolError(ValueError):
    pass


class Command(NamedTuple):
    request_id: int
    action: Action
    value: Value


class Ack(NamedTuple):
    request_id: int
    status: Status
    state: State  # the state after the command, also when it was rejected


def command(request_id: int, action: Action, value: Value) -> bytes:
    """The target zone is the address the command is sent to, so it is not in the payload."""
    wire_value = value.value if isinstance(value, Signal) else value
    return _encode({"type": "COMMAND", "request_id": request_id,
                    "action": action.value, "value": wire_value})


def ack(request_id: int, status: Status, state: State) -> bytes:
    return _encode({"type": "ACK", "request_id": request_id, "status": status.value,
                    "active_zone": state.active_zone.value, "signal": state.signal.value,
                    "brake": state.brake})


def error(reason: str) -> bytes:
    return _encode({"type": "ERROR", "reason": reason})


def parse_command(line: bytes) -> Command:
    message = _decode(line, "COMMAND")
    action = _member(Action, message.get("action"))
    if action is Action.SET_SIGNAL:
        value = _member(Signal, message.get("value"))
    else:
        value = _bool(message, "value")
    return Command(_request_id(message), action, value)


def parse_ack(line: bytes) -> Ack:
    message = _decode(line, "ACK")
    state = State(_member(Zone, message.get("active_zone")),
                  _member(Signal, message.get("signal")), _bool(message, "brake"))
    return Ack(_request_id(message), _member(Status, message.get("status")), state)


def _encode(message: dict) -> bytes:
    return (json.dumps(message, sort_keys=True) + "\n").encode()


def _decode(line: bytes, kind: str) -> dict:
    try:
        message = json.loads(line)
    except ValueError as cause:  # also covers invalid UTF-8
        raise ProtocolError(f"not a JSON line: {line[:80]!r}") from cause
    if not isinstance(message, dict) or message.get("type") != kind:
        raise ProtocolError(f"expected a {kind} message, got {message!r}")
    return message


def _request_id(message: dict) -> int:
    request_id = message.get("request_id")
    if type(request_id) is not int:
        raise ProtocolError(f"request_id must be an integer, got {request_id!r}")
    return request_id


def _bool(message: dict, key: str) -> bool:
    value = message.get(key)
    if type(value) is not bool:
        raise ProtocolError(f"{key} must be true or false, got {value!r}")
    return value


def _member(enum, value):
    try:
        return enum(value)
    except ValueError:
        raise ProtocolError(f"invalid {enum.__name__}: {value!r}") from None
