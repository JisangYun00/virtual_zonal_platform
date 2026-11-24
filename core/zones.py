"""Vocabulary and fixed tables of the testbed. Pure: no sockets, files, GPIO, or clocks."""
from enum import Enum


class Zone(str, Enum):
    """Declaration order is the ZONE SELECT cycle: FRONT -> REAR -> LEFT -> RIGHT -> FRONT."""
    FRONT = "FRONT"
    REAR = "REAR"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class Signal(str, Enum):
    """Turn-signal lamp state."""
    OFF = "OFF"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    HAZARD = "HAZARD"


class Action(str, Enum):
    """What a command sets. Commands name a target state, so repeating one changes nothing."""
    SET_SIGNAL = "SET_SIGNAL"  # value: Signal
    SET_BRAKE = "SET_BRAKE"    # value: bool, True = brake lamp on


class Status(str, Enum):
    SUCCESS = "SUCCESS"
    REJECTED_INACTIVE_ZONE = "REJECTED_INACTIVE_ZONE"
    REJECTED_NOT_ALLOWED = "REJECTED_NOT_ALLOWED"


# Which actions each zone accepts while it is active (plan section 4.3).
ALLOWED_ACTIONS = {
    Zone.FRONT: frozenset({Action.SET_SIGNAL}),
    Zone.REAR: frozenset({Action.SET_SIGNAL, Action.SET_BRAKE}),
    Zone.LEFT: frozenset(),
    Zone.RIGHT: frozenset(),
}

# Fixed addresses: subnet prefix + last octet. scripts/setup_network.sh repeats these numbers.
DEFAULT_SUBNET = "192.168.10"
ZONE_HOST = {Zone.FRONT: 11, Zone.REAR: 12, Zone.LEFT: 13, Zone.RIGHT: 14}


def next_zone(zone: Zone) -> Zone:
    order = list(Zone)
    return order[(order.index(zone) + 1) % len(order)]


def zone_address(subnet: str, zone: Zone) -> str:
    return f"{subnet}.{ZONE_HOST[zone]}"
