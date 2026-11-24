import unittest

from core.protocol import (
    Ack,
    Command,
    ProtocolError,
    ack,
    command,
    error,
    parse_ack,
    parse_command,
)
from core.state import State
from core.zones import Action, Signal, Status, Zone


class ProtocolTests(unittest.TestCase):
    def test_messages_round_trip(self):
        for action, value in [(Action.SET_SIGNAL, Signal.HAZARD), (Action.SET_BRAKE, True),
                              (Action.SET_BRAKE, False)]:
            with self.subTest(action=action, value=value):
                self.assertEqual(parse_command(command(7, action, value)), Command(7, action, value))
        state = State(Zone.REAR, Signal.LEFT, True)
        self.assertEqual(parse_ack(ack(7, Status.SUCCESS, state)), Ack(7, Status.SUCCESS, state))

    def test_command_wire_format(self):
        self.assertEqual(command(1, Action.SET_BRAKE, True),
                         b'{"action": "SET_BRAKE", "request_id": 1, "type": "COMMAND", "value": true}\n')

    def test_rejects_malformed_commands(self):
        for line in [b"", b"nope", b"[]", b"\xff\n",
                     b'{"type": "ACK", "action": "SET_BRAKE", "value": true, "request_id": 1}',
                     b'{"type": "COMMAND", "action": "HONK", "value": true, "request_id": 1}',
                     b'{"type": "COMMAND", "action": "SET_SIGNAL", "value": "UP", "request_id": 1}',
                     b'{"type": "COMMAND", "action": "SET_SIGNAL", "value": true, "request_id": 1}',
                     b'{"type": "COMMAND", "action": "SET_BRAKE", "value": "ON", "request_id": 1}',
                     b'{"type": "COMMAND", "action": "SET_BRAKE", "value": 1, "request_id": 1}',
                     b'{"type": "COMMAND", "action": "SET_BRAKE", "value": true, "request_id": true}',
                     b'{"type": "COMMAND", "action": "SET_BRAKE", "value": true}']:
            with self.subTest(line=line), self.assertRaises(ProtocolError):
                parse_command(line)

    def test_error_reply_is_not_an_ack(self):
        with self.assertRaisesRegex(ProtocolError, "bad input"):
            parse_ack(error("bad input"))
