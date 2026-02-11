import argparse
import math
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import serial


@dataclass
class Waveform:
    volts: list[float]
    raw_int16: list[int]


class GDSMemoryReader:
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


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def stddev_sample(xs: list[float]) -> float:
    mu = mean(xs)
    s2 = sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(s2)


def gaussian_pdf(x: float, mu: float, sigma: float) -> float:
    return (1.0 / (sigma * math.sqrt(2.0 * math.pi))) * math.exp(
        -0.5 * ((x - mu) / sigma) ** 2
    )


def read_waveform_once(
    port: str, baud: int = 115200, channel: int = 1, timeout_s: float = 5.0
) -> Waveform:
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


def write_csv(path: Path, wf: Waveform) -> None:
    if path.exists():
        raise FileExistsError(f"CSV-Datei existiert bereits: {path}")

    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("x", encoding="utf-8", newline="\n") as f:
        f.write("index,raw_int16,volts\n")
        for i, (raw, v) in enumerate(zip(wf.raw_int16, wf.volts)):
            f.write(f"{i},{raw},{v}\n")

class Viewer:
    VIEW_BOTH = 1
    VIEW_TIME = 2
    VIEW_HIST = 3

    def __init__(self, values: list[float], bins: int, debug_keys: bool = False) -> None:
        self.values = values
        self.bins = bins
        self.debug_keys = debug_keys
        self.view = self.VIEW_BOTH

        self.mu = mean(values)
        self.sigma = stddev_sample(values)

        vmin = min(values)
        vmax = max(values)
        uniq = len(set(values))
        print(
            f"N={len(values)}  min={vmin:.6g}  max={vmax:.6g}  unique={uniq}  µ={self.mu:.6g}  σ={self.sigma:.6g}"
        )

        self.fig = plt.figure()
        self.fig.canvas.mpl_connect("key_press_event", self.on_key)

        # Zwei Achsen – werden je nach Ansicht nur umpositioniert / versteckt
        self.ax_time = self.fig.add_axes([0.08, 0.55, 0.90, 0.37])  # initial: oben
        self.ax_hist = self.fig.add_axes([0.08, 0.10, 0.90, 0.37])  # initial: unten

        self._draw_time()
        self._draw_hist()

        self.set_view(self.VIEW_BOTH)

    def on_key(self, event) -> None:
        k = (event.key or "").lower()
        if self.debug_keys:
            print("key:", repr(event.key))

        # Bei manchen Tastaturen kommen numpad-Ziffern als "kp1" usw.
        if k in ("n", "right"):
            self.set_view(1 + (self.view % 3))
        elif k in ("p", "left"):
            self.set_view(3 if self.view == 1 else (self.view - 1))
        elif k in ("1", "kp1"):
            self.set_view(self.VIEW_BOTH)
        elif k in ("2", "kp2"):
            self.set_view(self.VIEW_TIME)
        elif k in ("3", "kp3"):
            self.set_view(self.VIEW_HIST)
        elif k in ("q", "escape"):
            plt.close(self.fig)

    def set_view(self, v: int) -> None:
        self.view = v

        if v == self.VIEW_BOTH:
            # Zeitreihe oben, Histogramm unten
            self.ax_time.set_visible(True)
            self.ax_hist.set_visible(True)
            self.ax_time.set_position([0.08, 0.55, 0.90, 0.37])
            self.ax_hist.set_position([0.08, 0.10, 0.90, 0.37])
            title = "Ansicht 1/3: Zeitreihe + Histogramm  (1/2/3, n/p, q)"
        elif v == self.VIEW_TIME:
            # Zeitreihe allein groß
            self.ax_time.set_visible(True)
            self.ax_hist.set_visible(False)
            self.ax_time.set_position([0.08, 0.10, 0.90, 0.82])
            title = "Ansicht 2/3: Zeitreihe  (1/2/3, n/p, q)"
        else:
            # Histogramm allein groß
            self.ax_hist.set_visible(True)
            self.ax_time.set_visible(False)
            self.ax_hist.set_position([0.08, 0.10, 0.90, 0.82])
            title = "Ansicht 3/3: Histogramm  (1/2/3, n/p, q)"

        self.fig.suptitle(title)

        # TkAgg ist manchmal erst mit draw() wirklich glücklich:
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def _draw_time(self) -> None:
        ax = self.ax_time
        ax.clear()
        ax.plot(self.values)
        ax.set_title("Zeitreihe (Sample-Index)")
        ax.set_xlabel("Sample")
        ax.set_ylabel("Spannung [V]")
        ax.text(
            0.98,
            0.95,
            f"µ = {self.mu:.6g} V\nσ = {self.sigma:.6g} V\nN = {len(self.values)}",
            transform=ax.transAxes,
            ha="right",
            va="top",
        )

    def _draw_hist(self) -> None:
        ax = self.ax_hist
        ax.clear()
        counts, bin_edges, _ = ax.hist(self.values, bins=self.bins)
        ax.set_xlabel("Spannung [V]")
        ax.set_ylabel("Anzahl pro Bin")

        if self.sigma == 0.0:
            ax.set_title("Histogramm (σ=0: alle Messwerte identisch)")
            return

        bin_width = bin_edges[1] - bin_edges[0]
        centers = [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(len(bin_edges) - 1)]
        N = len(self.values)
        gauss_y = [N * bin_width * gaussian_pdf(x, self.mu, self.sigma) for x in centers]
        ax.plot(centers, gauss_y)
        ax.set_title("Histogramm + Gauss-Fit (µ, σ aus Messdaten)")



def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--port", default="/dev/ttyACM0")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--channel", type=int, default=1)
    p.add_argument("--timeout", type=float, default=5.0)
    p.add_argument("--bins", type=int, default=60)
    p.add_argument(
        "--csv",
        metavar="DATEI",
        help="Optional: CSV speichern (index,raw_int16,volts). Datei darf nicht existieren.",
    )
    p.add_argument("--debug-keys", action="store_true", help="Gibt empfangene Key-Events aus")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    wf = read_waveform_once(
        port=args.port, baud=args.baud, channel=args.channel, timeout_s=args.timeout
    )

    if args.csv:
        try:
            write_csv(Path(args.csv), wf)
            print(f"CSV geschrieben: {args.csv}")
        except FileExistsError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(2)

    viewer = Viewer(wf.volts, bins=args.bins, debug_keys=args.debug_keys)
    viewer.fig._viewer_ref = viewer  # starke Referenz am Figure speichern
    plt.show()


if __name__ == "__main__":
    main()
