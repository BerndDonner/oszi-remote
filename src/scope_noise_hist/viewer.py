from __future__ import annotations

import matplotlib.pyplot as plt

from .stats import gaussian_pdf, mean, stddev_sample


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
