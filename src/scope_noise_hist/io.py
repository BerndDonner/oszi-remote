from __future__ import annotations

import csv
from pathlib import Path

from .types import Waveform


def write_csv(path: Path, wf: Waveform) -> None:
    """Schreibt index, value, raw_int16 als CSV. Datei darf nicht existieren."""

    if path.exists():
        raise FileExistsError(f"CSV-Datei existiert bereits: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["index", "value", "raw_int16"])
        for i, (v, raw) in enumerate(zip(wf.volts, wf.raw_int16, strict=True)):
            w.writerow([i, v, raw])
