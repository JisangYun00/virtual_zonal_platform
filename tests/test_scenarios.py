"""Plan section 5 scenarios A-D through the real bringup commands, on loopback addresses.

Linux routes all of 127.0.0.0/8 to loopback, so 127.0.0.11-14 bind with no network setup.
"""
import json
import socket
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.zone_controller = subprocess.Popen(
            ["bash", "bringup/zone_controller.sh", "--local"], cwd=ROOT,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.stop_zone_controller)
        stdin, stdout, stderr = (self.zone_controller.stdin, self.zone_controller.stdout,
                                 self.zone_controller.stderr)
        assert stdin and stdout and stderr
        self.stdin, self.stdout, self.stderr = stdin, stdout, stderr
        self.assertEqual(self.zone_controller_line(), "READY active_zone=FRONT")

    def stop_zone_controller(self):
        if self.zone_controller.poll() is None:
            self.zone_controller.kill()
            self.zone_controller.communicate()

    def zone_controller_line(self):
        line = self.stdout.readline()
        if not line:
            self.fail(f"zone controller exited: {self.stderr.read()}")
        return line.strip()

    def press_zone_select(self):
        self.stdin.write("\n")
        self.stdin.flush()
        while (line := self.zone_controller_line()).startswith("COMMAND"):
            pass
        return line

    def central(self, *lines):
        return subprocess.run(["bash", "bringup/central.sh", "--local"],
                              input="".join(f"{line}\n" for line in lines), cwd=ROOT,
                              capture_output=True, text=True, timeout=10, check=False)

    def replies(self, *lines):
        result = self.central(*lines)
        self.assertEqual(result.returncode, 0, result.stderr)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        for reply in replies:
            self.assertGreaterEqual(reply.pop("rtt_ms"), 0)
        return replies

    def test_a_zone_switching_moves_control_and_clears_lamps(self):
        self.assertEqual(self.replies("FRONT SET_SIGNAL HAZARD")[0]["signal"], "HAZARD")
        self.assertEqual(self.press_zone_select(), "ZONE_CHANGED FRONT -> REAR")
        rear, front = self.replies("REAR SET_BRAKE ON", "FRONT SET_SIGNAL LEFT")
        self.assertEqual((rear["status"], rear["active_zone"], rear["signal"], rear["brake"]),
                         ("SUCCESS", "REAR", "OFF", True))
        self.assertEqual(front["status"], "REJECTED_INACTIVE_ZONE")

    def test_a_zone_select_presses_arriving_together_all_count(self):
        self.stdin.write("\n\n\n")
        self.stdin.flush()
        self.assertEqual([self.zone_controller_line() for _ in range(3)],
                         ["ZONE_CHANGED FRONT -> REAR", "ZONE_CHANGED REAR -> LEFT",
                          "ZONE_CHANGED LEFT -> RIGHT"])

    def test_b_lighting_commands_set_and_repeat_safely(self):
        self.press_zone_select()  # REAR
        replies = self.replies("rear set_signal left", "REAR SET_SIGNAL LEFT",
                               "REAR SET_SIGNAL RIGHT", "REAR SET_BRAKE ON")
        self.assertEqual([r["request_id"] for r in replies], [1, 2, 3, 4])
        self.assertEqual([(r["status"], r["signal"], r["brake"]) for r in replies],
                         [("SUCCESS", "LEFT", False), ("SUCCESS", "LEFT", False),
                          ("SUCCESS", "RIGHT", False), ("SUCCESS", "RIGHT", True)])

    def test_c_inactive_zone_command_is_rejected_and_changes_nothing(self):
        rear, brake = self.replies("REAR SET_SIGNAL LEFT", "FRONT SET_BRAKE ON")
        self.assertEqual(rear, {"zone": "REAR", "action": "SET_SIGNAL", "value": "LEFT",
                                "request_id": 1, "status": "REJECTED_INACTIVE_ZONE",
                                "active_zone": "FRONT", "signal": "OFF", "brake": False})
        self.assertEqual((brake["status"], brake["brake"]), ("REJECTED_NOT_ALLOWED", False))
        self.assertIn("COMMAND ip=127.0.0.12 zone=REAR request_id=1", self.zone_controller_line())

    def test_d_unreachable_zone_controller_is_reported(self):
        self.stop_zone_controller()
        result = self.central("FRONT SET_SIGNAL LEFT")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("FRONT 127.0.0.11:5000 failed", result.stderr)

    def test_bad_console_input_is_reported_and_the_console_keeps_going(self):
        result = self.central("SIDE SET_SIGNAL LEFT", "REAR SET_BRAKE MAYBE", "REAR SET_SIGNAL")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr.count("invalid input"), 3)
        self.assertEqual(result.stdout, "")

    def test_malformed_message_gets_error_and_connection_stays_usable(self):
        with socket.create_connection(("127.0.0.11", 5000), timeout=5) as sock:
            replies = sock.makefile("rb")
            sock.sendall(b"nope\n")
            self.assertEqual(json.loads(replies.readline())["type"], "ERROR")
            sock.sendall(b'{"type": "COMMAND", "action": "SET_SIGNAL", "value": "HAZARD", '
                         b'"request_id": 2}\n')
            self.assertEqual(json.loads(replies.readline())["status"], "SUCCESS")
