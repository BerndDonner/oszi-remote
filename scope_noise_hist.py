import re
import time
import math
from dataclasses import dataclass

import serial
import matplotlib.pyplot as plt


@dataclass
class Waveform:
    volts: list[float]


class GDSMemoryReader:
    """
    Liest eine :ACQ1:MEM? Antwort im "Streaming"-Stil:
    - sammelt Bytes in einem Puffer
    - extrahiert Vertical Scale und SCPI-Blocklänge
    - wartet, bis die Rohdaten vollständig da sind
    - dekodiert int16 big-endian und skaliert zu Volt
    """

    def __init__(self) -> None:
        self.buf = bytearray()
        self.waiting_for_data = False
        self.vertical_scale: float | None = None
        self.length: int | None = None

    def feed(self, data: bytes) -> Waveform | None:
        self.buf += data

        if not self.waiting_for_data:
            # 1) Vertical Scale aus dem Header ziehen: "Vertical Scale,5.000e+00;"
            m = re.search(br"Vertical Scale,([^;]+);", self.buf)
            if not m:
                return None
            self.vertical_scale = float(m.group(1).decode("ascii", errors="replace"))

            # 2) Beginn des Datenblocks suchen: "Waveform Data;\n#"
            marker = b"Waveform Data;\n#"
            i = self.buf.find(marker)
            if i == -1:
                return None

            p = i + len(marker)

            if p >= len(self.buf):
                return None

            # 3) SCPI-Blockformat: #<n><len><bytes...>
            n_digits = int(chr(self.buf[p]))
            p += 1

            if p + n_digits > len(self.buf):
                return None

            self.length = int(self.buf[p:p + n_digits].decode("ascii"))
            p += n_digits

            # Alles bis zum Beginn der Rohdaten entfernen
            self.buf = self.buf[p:]
            self.waiting_for_data = True

        assert self.length is not None
        assert self.vertical_scale is not None

        if len(self.buf) < self.length:
            return None

        raw = self.buf[:self.length]
        self.buf = self.buf[self.length:]
        self.waiting_for_data = False

        # 4) Rohdaten: je 2 Byte => signed int16 (big-endian)
        # Umrechnung laut Manual: (raw/25) * VerticalScale
        AD_FACTOR = 25.0

        volts: list[float] = []
        for i in range(0, len(raw), 2):
            val = int.from_bytes(raw[i:i+2], byteorder="big", signed=True)
            volts.append((val / AD_FACTOR) * self.vertical_scale)

        return Waveform(volts=volts)


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def stddev_sample(xs: list[float]) -> float:
    # empirische Standardabweichung (Stichprobe): ddof=1
    mu = mean(xs)
    s2 = sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(s2)


def gaussian_pdf(x: float, mu: float, sigma: float) -> float:
    return (1.0 / (sigma * math.sqrt(2.0 * math.pi))) * math.exp(-0.5 * ((x - mu) / sigma) ** 2)


def read_waveform_once(port: str, baud: int = 115200, channel: int = 1, timeout_s: float = 5.0) -> Waveform:
    reader = GDSMemoryReader()

    with serial.Serial(port, baudrate=baud, timeout=0.1) as ser:
        def send(cmd: str) -> None:
            ser.write((cmd + "\n").encode("ascii"))
            ser.flush()

        # Header einschalten, damit Vertical Scale etc. sicher mitkommen
        send(":HEADer ON")

        # Daten anfordern (abgekürzte SCPI-Form ist üblich)
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


def plot_hist_and_gauss(values: list[float], bins: int = 50) -> None:
    mu = mean(values)
    sigma = stddev_sample(values)

    # Histogramm zeichnen (Counts)
    counts, bin_edges, _ = plt.hist(values, bins=bins)

    # Bin-Mitten und Bin-Breite
    bin_width = bin_edges[1] - bin_edges[0]
    centers = [(bin_edges[i] + bin_edges[i+1]) / 2 for i in range(len(bin_edges) - 1)]

    # Gausskurve auf Counts skalieren: N * bin_width * pdf(x)
    N = len(values)
    gauss_y = [N * bin_width * gaussian_pdf(x, mu, sigma) for x in centers]

    plt.plot(centers, gauss_y)

    plt.title("Rauschen: Histogramm und Gauss-Fit (µ, σ aus Messdaten)")
    plt.xlabel("Spannung [V]")
    plt.ylabel("Anzahl pro Bin")

    # Kurze Info ins Diagramm
    plt.text(0.02, 0.98, f"µ = {mu:.6g} V\nσ = {sigma:.6g} V\nN = {N}",
             transform=plt.gca().transAxes, va="top")

    plt.show()


def main() -> None:
    # >>> ANPASSEN <<<
    port = "COM5"   # Windows z.B. COM5, Linux z.B. /dev/ttyACM0

    wf = read_waveform_once(port=port, channel=1)
    plot_hist_and_gauss(wf.volts, bins=60)


if __name__ == "__main__":
    main()

