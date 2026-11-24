import unittest
from core.buttons import Buttons, ButtonEvent
from core.outputs import leds
from core.management import state_line, parse_state
from core.state import State
from core.zones import Zone, Signal
from core.protocol import ProtocolError

class Phase2Tests(unittest.TestCase):
    def test_short_left(self):
        b = Buttons()
        b.sample('LEFT', True, 0)
        b.tick(.06)
        b.sample('LEFT', False, .18)
        self.assertEqual(b.tick(.24), [])
        self.assertEqual(b.tick(.31), [ButtonEvent('SIGNAL_LEFT')])
    def test_long_hazard(self):
        b = Buttons()
        b.sample('RIGHT', True, 0)
        b.tick(.06)
        b.sample('RIGHT', False, .9)
        b.tick(.96)
        self.assertEqual(b.tick(1.1), [ButtonEvent('HAZARD')])
    def test_simultaneous_brake(self):
        b = Buttons()
        b.sample('LEFT', True, 0)
        b.sample('RIGHT', True, .02)
        b.tick(.08)
        # At t=.08 both accepted, pressed_at equal. Chord recognized.
        self.assertEqual(b.sample('RIGHT', False, .3), [])
        self.assertEqual(b.tick(.36), [ButtonEvent('BRAKE', False)])
        self.assertEqual(b.sample('LEFT', False, .4), [])
        self.assertEqual(b.tick(.6), [])
    def test_late_tick_does_not_create_false_chord(self):
        b = Buttons()
        b.sample('LEFT', True, 0)
        b.sample('RIGHT', True, .4)
        events = b.tick(.5)
        self.assertEqual(events, [])

    def test_zone_select(self):
        b = Buttons()
        b.sample('ZONE', True, 0)
        b.tick(.1)
        b.sample('ZONE', False, .15)
        self.assertEqual(b.tick(.21), [ButtonEvent('ZONE_SELECT')])
    def test_bounce(self):
        b = Buttons()
        b.sample('ZONE', True, 0)
        b.sample('ZONE', False, .01)
        b.tick(.07)
        self.assertEqual(b.tick(.2), [])
    def test_bad_clock(self):
        b = Buttons()
        b.tick(2)
        with self.assertRaises(ValueError): b.tick(1)
    def test_leds(self):
        rear=State(Zone.REAR, Signal.HAZARD, True)
        self.assertEqual(len(leds(rear,0)),7)
        self.assertTrue(leds(rear,0)['SIGNAL_LEFT'])
        self.assertFalse(leds(rear,.34)['SIGNAL_LEFT'])
        self.assertTrue(leds(rear,0)['BRAKE'])
        self.assertEqual(sum(leds(rear,0)[x] for x in ('ZONE_FRONT','ZONE_REAR','ZONE_LEFT','ZONE_RIGHT')),1)
    def test_management(self):
        s=State(Zone.LEFT, Signal.OFF, False)
        self.assertEqual(parse_state(state_line(s,5)), (5,s))
        for bad in [b'{}', b'nope', b'{"type":"STATE","sequence":true}',
                    b'{"type":"STATE","sequence":0,"active_zone":"FRONT","signal":"OFF","brake":1}']:
            with self.subTest(bad=bad), self.assertRaises(ProtocolError): parse_state(bad)
