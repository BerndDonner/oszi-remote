from __future__ import annotations

import re
import time

import serial

from .types import Waveform


class GDSMemoryReader:
    """Parst den GDS-1000B Memory-Transfer (Header + Binärdaten) stückweise."""

    def __init__(self) -> None:
        self.buf = bytearray()
        self.waiting_for_data = False
        self.vertical_scale: float | None = None
        self.length: int | None = None

    def feed(self, data: bytes) -> Waveform | None:
        self.buf += data

        if not self.waiting_for_data:
            m = re.search(br"Vertical Scale,([^;]+);", self.buf)
            if not m:
                return None
            self.vertical_scale = float(m.group(1).decode("ascii", errors="replace"))

            marker = b"Waveform Data;\n#"
            i = self.buf.find(marker)
            if i == -1:
                return None

            p = i + len(marker)
            if p >= len(self.buf):
                return None

            n_digits = int(chr(self.buf[p]))
            p += 1

            if p + n_digits > len(self.buf):
                return None

            self.length = int(self.buf[p : p + n_digits].decode("ascii"))
            p += n_digits

            self.buf = self.buf[p:]
            self.waiting_for_data = True

        assert self.length is not None
        assert self.vertical_scale is not None

        if len(self.buf) < self.length:
            return None

        raw = self.buf[: self.length]
        self.buf = self.buf[self.length :]
        self.waiting_for_data = False

        AD_FACTOR = 25.0
        raw_int16: list[int] = []
        volts: list[float] = []

        for i in range(0, len(raw), 2):
            val = int.from_bytes(raw[i : i + 2], byteorder="big", signed=True)
            raw_int16.append(val)
            volts.append((val / AD_FACTOR) * self.vertical_scale)

        return Waveform(volts=volts, raw_int16=raw_int16)


def read_waveform_once(
    port: str,
    baud: int = 115200,
    channel: int = 1,
    timeout_s: float = 5.0,
) -> Waveform:
    """Liest genau einen Waveform-Dump aus dem Scope-Memory."""

    reader = GDSMemoryReader()

    with serial.Serial(port, baudrate=baud, timeout=0.1) as ser:

        def send(cmd: str) -> None:
            ser.write((cmd + "\n").encode("ascii"))
            ser.flush()

        send(":HEADer ON")
        send(f":ACQ{channel}:MEM?")

        t0 = time.time()
        while True:
            chunk = ser.read(ser.in_waiting or 1)
            if chunk:
                wf = reader.feed(chunk)
                if wf is not None:
                    return wf
            if time.time() - t0 > timeout_s:
                raise TimeoutError("Timeout: keine vollständigen Daten vom Oszilloskop erhalten.")
