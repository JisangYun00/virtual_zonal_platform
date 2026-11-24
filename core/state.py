"""The zone controller's whole state and the only rules that change it. Pure."""
from __future__ import annotations  # builtin generics in hints on Python 3.8

from typing import NamedTuple, Union

from .zones import ALLOWED_ACTIONS, Action, Signal, Status, Zone, next_zone

Value = Union[Signal, bool]  # Signal for SET_SIGNAL, bool for SET_BRAKE


class State(NamedTuple):
    active_zone: Zone
    signal: Signal
    brake: bool


INITIAL = State(Zone.FRONT, Signal.OFF, False)


def apply(state: State, target: Zone, action: Action, value: Value) -> tuple[State, Status]:
    """A command sent to `target`'s address. A rejected command leaves the state as it was.

    `value` must match `action`; core.protocol checks that at the boundary.
    """
    if target is not state.active_zone:
        return state, Status.REJECTED_INACTIVE_ZONE
    if action not in ALLOWED_ACTIONS[target]:
        return state, Status.REJECTED_NOT_ALLOWED
    if action is Action.SET_SIGNAL:
        return state._replace(signal=value), Status.SUCCESS
    return state._replace(brake=value), Status.SUCCESS


def select_next_zone(state: State) -> State:
    """ZONE SELECT. Safe transition: lamps set in the previous zone never stay on in the next one."""
    return State(next_zone(state.active_zone), Signal.OFF, False)
