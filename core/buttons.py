"""Deterministic button event interpreter. Clock comes from caller; no device I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ButtonEvent:
    kind: str  # ZONE_SELECT, SIGNAL_LEFT, SIGNAL_RIGHT, HAZARD, BRAKE
    value: Optional[bool] = None


class Buttons:
    """Debounced, short/long, two-button brake (hold) input.

    Physical samples must be passed in with monotonic timestamps. A change is
    accepted only once stable for debounce_s; tick() finalizes pending changes.
    A simultaneous LEFT+RIGHT hold invokes BRAKE_ON; release invokes BRAKE_OFF.
    No signal events are generated for a chord. These are proposed defaults,
    not yet validated against the actual buttons.
    """

    NAMES = ("ZONE", "LEFT", "RIGHT")

    def __init__(self, debounce_s: float = 0.05, long_s: float = 0.7,
                 chord_s: float = 0.12) -> None:
        if not (0 <= debounce_s < long_s and 0 <= chord_s < long_s):
            raise ValueError("invalid button thresholds")
        self.debounce_s, self.long_s, self.chord_s = debounce_s, long_s, chord_s
        self.raw = {name: False for name in self.NAMES}
        self.stable = self.raw.copy()
        self.changed_at = {name: 0.0 for name in self.NAMES}
        self.pressed_at = {name: None for name in self.NAMES}
        self._pending: Dict[str, Optional[float]] = {name: None for name in self.NAMES}
        self._chord = False
        self._consumed = set()
        self._last_time = float('-inf')

    def sample(self, name: str, pressed: bool, now: float) -> List[ButtonEvent]:
        if name not in self.raw or type(pressed) is not bool:
            raise ValueError("unknown button or invalid state")
        self._check_clock(now)
        if self.raw[name] != pressed:
            self.raw[name] = pressed
            self.changed_at[name] = now
        return self._settle(now)

    def tick(self, now: float) -> List[ButtonEvent]:
        self._check_clock(now)
        return self._settle(now)

    def _check_clock(self, now: float) -> None:
        if now < self._last_time:
            raise ValueError("timestamps must be monotonic")
        self._last_time = now

    def _settle(self, now: float) -> List[ButtonEvent]:
        out = []
        for name in self.NAMES:
            if self.stable[name] == self.raw[name]:
                continue
            if now - self.changed_at[name] < self.debounce_s:
                continue
            self.stable[name] = self.raw[name]
            if self.stable[name]:
                self.pressed_at[name] = self.changed_at[name] + self.debounce_s
            else:
                start = self.pressed_at[name]
                self.pressed_at[name] = None
                if name == "ZONE":
                    if start is not None:
                        out.append(ButtonEvent("ZONE_SELECT"))
                elif self._chord:
                    self._consumed.add(name)
                elif name not in self._consumed and start is not None:
                    self._pending[name] = self.changed_at[name] + self.debounce_s - start
        both = self.stable["LEFT"] and self.stable["RIGHT"]
        if both and not self._chord:
            left_t, right_t = self.pressed_at["LEFT"], self.pressed_at["RIGHT"]
            if left_t is not None and right_t is not None and abs(left_t - right_t) <= self.chord_s:
                self._chord = True
                self._pending["LEFT"] = self._pending["RIGHT"] = None
                self._consumed.update(("LEFT", "RIGHT"))
                out.append(ButtonEvent("BRAKE", True))
        if self._chord and not both:
            self._chord = False
            out.append(ButtonEvent("BRAKE", False))
        # Wait for the chord window to expire before classifying a release.
        for name in ("LEFT", "RIGHT"):
            duration = self._pending[name]
            if duration is not None and now - self.changed_at[name] >= self.chord_s:
                out.append(ButtonEvent("HAZARD" if duration >= self.long_s else "SIGNAL_" + name))
                self._pending[name] = None
                self._consumed.discard(name)
        if not any(self.stable[name] or self.raw[name] for name in ("LEFT", "RIGHT")):
            self._consumed.clear()
        return out
