"""Sole owner of the zone controller state. Every input (network command, ZONE SELECT) comes through here."""
from __future__ import annotations  # builtin generics in hints on Python 3.8

from core.state import INITIAL, State, Value, apply, select_next_zone
from core.zones import Action, Status, Zone


def log(text: str) -> None:
    print(text, flush=True)


class ZoneController:
    """One object plays all four logical zone controllers, which share one active zone.

    Everything runs on one asyncio loop, so the state needs no lock.
    Outputs (GPIO lamps, STATE push to the central controller) attach here when they exist.
    """

    def __init__(self) -> None:
        self.state = INITIAL

    def request(self, zone: Zone, action: Action, value: Value) -> tuple[Status, State]:
        self.state, status = apply(self.state, zone, action, value)
        return status, self.state

    def select_next(self) -> None:
        previous = self.state.active_zone
        self.state = select_next_zone(self.state)
        log(f"ZONE_CHANGED {previous.value} -> {self.state.active_zone.value}")
