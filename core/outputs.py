"""LED intentions derived from the existing immutable State (no hardware I/O)."""
from __future__ import annotations
from typing import Dict
from .state import State
from .zones import Signal, Zone


def leds(state: State, now: float, flash_hz: float = 1.5) -> Dict[str, bool]:
    if flash_hz <= 0:
        raise ValueError("flash_hz must be positive")
    flash_on = (now * flash_hz) % 1.0 < 0.5
    return {
        "ZONE_FRONT": state.active_zone is Zone.FRONT,
        "ZONE_REAR": state.active_zone is Zone.REAR,
        "ZONE_LEFT": state.active_zone is Zone.LEFT,
        "ZONE_RIGHT": state.active_zone is Zone.RIGHT,
        "SIGNAL_LEFT": state.active_zone in (Zone.FRONT, Zone.REAR) and flash_on and
                       state.signal in (Signal.LEFT, Signal.HAZARD),
        "SIGNAL_RIGHT": state.active_zone in (Zone.FRONT, Zone.REAR) and flash_on and
                        state.signal in (Signal.RIGHT, Signal.HAZARD),
        "BRAKE": state.active_zone is Zone.REAR and state.brake,
    }
