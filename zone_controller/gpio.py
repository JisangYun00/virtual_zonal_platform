"""Opt-in Jetson.GPIO adapter; BOARD map supplied only after physical wiring review.

The team Lab 6 uses BOARD pin IDs. Do not assume a default full 10-pin map.
Inputs are active-low with EXTERNAL 10-kohm pull-ups (Jetson.GPIO ignores
pull_up_down on some boards); outputs require checked resistors/drivers.
"""
from __future__ import annotations
import asyncio
import json
import time
from core.buttons import Buttons
from core.outputs import leds
from core.zones import Action, Signal

INPUTS = ('ZONE', 'LEFT', 'RIGHT')
OUTPUTS = ('ZONE_FRONT', 'ZONE_REAR', 'ZONE_LEFT', 'ZONE_RIGHT',
           'SIGNAL_LEFT', 'SIGNAL_RIGHT', 'BRAKE')


def load_wiring(path):
    with open(path, encoding='utf8') as f:
        data = json.load(f)
    if set(data) != {'inputs', 'outputs'}:
        raise ValueError('wiring must contain exactly inputs and outputs')
    if set(data['inputs']) != set(INPUTS) or set(data['outputs']) != set(OUTPUTS):
        raise ValueError('wiring keys incomplete or unexpected')
    pins = list(data['inputs'].values()) + list(data['outputs'].values())
    if any(type(pin) is not int or pin < 1 or pin > 40 for pin in pins):
        raise ValueError('all BOARD pins must be integer in [1,40]')
    if len(set(pins)) != len(pins):
        raise ValueError('BOARD pin conflict')
    return data


class GPIOAdapter:
    def __init__(self, controller, wiring, driver=None):
        self.controller = controller
        self.wiring = wiring
        if driver is None:
            import Jetson.GPIO as driver
        self.gpio = driver
        self.buttons = Buttons()
        self._last = None

    def setup(self):
        g = self.gpio
        g.setmode(g.BOARD)
        for pin in self.wiring['inputs'].values():
            g.setup(pin, g.IN)  # External pull-up resistor required.
        for pin in self.wiring['outputs'].values():
            g.setup(pin, g.OUT, initial=g.LOW)

    def _handle(self, event):
        from core.buttons import ButtonEvent
        kind = event.kind
        if kind == 'ZONE_SELECT':
            self.controller.select_next()
            return
        if kind == 'BRAKE':
            self.controller.request(self.controller.state.active_zone, Action.SET_BRAKE, bool(event.value))
            return
        if kind in ('SIGNAL_LEFT', 'SIGNAL_RIGHT', 'HAZARD'):
            choice = {'SIGNAL_LEFT': Signal.LEFT, 'SIGNAL_RIGHT': Signal.RIGHT,
                      'HAZARD': Signal.HAZARD}[kind]
            current = self.controller.state.signal
            target = Signal.OFF if current is choice else choice
            self.controller.request(self.controller.state.active_zone, Action.SET_SIGNAL, target)

    def sample(self, now):
        for name in INPUTS:
            # Stable count and debounce happen in pure Buttons.
            low_is_pressed = not bool(self.gpio.input(self.wiring['inputs'][name]))
            for event in self.buttons.sample(name, low_is_pressed, now):
                self._handle(event)
        for event in self.buttons.tick(now):
            self._handle(event)
        requested = leds(self.controller.state, now)
        if requested != self._last:
            for name, enabled in requested.items():
                self.gpio.output(self.wiring['outputs'][name], self.gpio.HIGH if enabled else self.gpio.LOW)
            self._last = requested

    async def run(self):
        self.setup()
        try:
            while True:
                self.sample(time.monotonic())
                await asyncio.sleep(.02)
        finally:
            for pin in self.wiring['outputs'].values():
                self.gpio.output(pin, self.gpio.LOW)
            self.gpio.cleanup()
