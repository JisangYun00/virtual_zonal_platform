import unittest
from core.buttons import Buttons
from core.outputs import leds
from core.state import State
from core.zones import Zone, Signal
from zone_controller.controller import ZoneController
from zone_controller.camera import CameraService

class FailedCamera:
    def __init__(self):self.closes=0
    def open(self):raise RuntimeError('camera not found')
    def close(self):self.closes+=1

class FaultTests(unittest.TestCase):
    def test_camera_open_failure_releases_partial_resources(self):
        ctrl=ZoneController();ctrl.select_next()
        b=FailedCamera();cam=CameraService(ctrl,b)
        self.assertEqual(cam.snapshot()[0],503)
        self.assertEqual(b.closes,1)
    def test_button_invalid_input(self):
        b=Buttons()
        with self.assertRaises(ValueError):b.sample('REAR', True, 1)
        with self.assertRaises(ValueError):b.sample('LEFT', 1, 1)
    def test_signal_never_on_left_right_zone(self):
        for z in (Zone.LEFT,Zone.RIGHT):
            for t in (0,.1,.4):
                state=State(z,Signal.HAZARD,True)
                lamps=leds(state,t)
                self.assertFalse(lamps['SIGNAL_LEFT'])
                self.assertFalse(lamps['SIGNAL_RIGHT'])
                self.assertFalse(lamps['BRAKE'])
