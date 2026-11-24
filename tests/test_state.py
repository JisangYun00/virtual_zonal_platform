import unittest

from core.state import INITIAL, State, apply, select_next_zone
from core.zones import Action, Signal, Status, Zone

FRONT_IDLE = State(Zone.FRONT, Signal.OFF, False)
REAR_IDLE = State(Zone.REAR, Signal.OFF, False)


class StateTests(unittest.TestCase):
    def test_starts_in_front_with_lamps_off(self):
        self.assertEqual(INITIAL, FRONT_IDLE)

    def test_inactive_zone_rejects_and_keeps_the_state(self):
        for action, value in [(Action.SET_SIGNAL, Signal.LEFT), (Action.SET_BRAKE, True)]:
            self.assertEqual(apply(FRONT_IDLE, Zone.REAR, action, value),
                             (FRONT_IDLE, Status.REJECTED_INACTIVE_ZONE))

    def test_permissions_follow_the_spec_table(self):
        # Plan 4.3: signals in FRONT and REAR, brake only in REAR, nothing in LEFT/RIGHT.
        cases = [(Zone.FRONT, Action.SET_SIGNAL, True), (Zone.FRONT, Action.SET_BRAKE, False),
                 (Zone.REAR, Action.SET_SIGNAL, True), (Zone.REAR, Action.SET_BRAKE, True),
                 (Zone.LEFT, Action.SET_SIGNAL, False), (Zone.LEFT, Action.SET_BRAKE, False),
                 (Zone.RIGHT, Action.SET_SIGNAL, False), (Zone.RIGHT, Action.SET_BRAKE, False)]
        for zone, action, allowed in cases:
            value = Signal.HAZARD if action is Action.SET_SIGNAL else True
            idle = State(zone, Signal.OFF, False)
            with self.subTest(zone=zone, action=action):
                new, status = apply(idle, zone, action, value)
                self.assertEqual(status, Status.SUCCESS if allowed else Status.REJECTED_NOT_ALLOWED)
                self.assertEqual(new != idle, allowed)

    def test_commands_set_a_target_state_so_repeats_change_nothing(self):
        once, _ = apply(REAR_IDLE, Zone.REAR, Action.SET_SIGNAL, Signal.LEFT)
        twice, status = apply(once, Zone.REAR, Action.SET_SIGNAL, Signal.LEFT)
        self.assertEqual((twice, status), (State(Zone.REAR, Signal.LEFT, False), Status.SUCCESS))
        braking, _ = apply(twice, Zone.REAR, Action.SET_BRAKE, True)
        self.assertEqual(braking, State(Zone.REAR, Signal.LEFT, True))
        self.assertEqual(apply(braking, Zone.REAR, Action.SET_BRAKE, False)[0], twice)

    def test_zone_select_turns_the_previous_zones_lamps_off(self):
        lit = State(Zone.REAR, Signal.HAZARD, True)
        self.assertEqual(select_next_zone(lit), State(Zone.LEFT, Signal.OFF, False))
