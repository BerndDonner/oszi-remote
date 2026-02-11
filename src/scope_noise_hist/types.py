from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Waveform:
    volts: list[float]
    raw_int16: list[int]
