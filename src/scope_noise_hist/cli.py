from __future__ import annotations

import argparse
import sys
from pathlib import Path

from serial.tools import list_ports

from .gds_reader import read_waveform_once
from .io import write_csv
from .viewer import Viewer


def _available_ports() -> list[str]:
    return [p.device for p in list_ports.comports()]


def _print_ports() -> None:
    ports = _available_ports()
    if not ports:
        print("Keine seriellen Ports gefunden.")
        return
    for p in ports:
        print(p)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="oszi-remote",
        description=(
            "Liest Memory-Waveform aus dem GW Instek GDS-1000B und zeigt Zeitreihe + Histogramm. "
            "Optional: Export als CSV/PNG."
        ),
    )

    p.add_argument(
        "--list-ports",
        action="store_true",
        help="Verfügbare COM-Ports auflisten und beenden.",
    )

    p.add_argument("--port", help="COM-Port, z.B. COM5. (Pflicht, außer bei --list-ports)")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--channel", type=int, default=1)
    p.add_argument("--timeout", type=float, default=5.0)
    p.add_argument("--bins", type=int, default=60)

    p.add_argument(
        "--csv",
        metavar="DATEI",
        help="Optional: CSV speichern (index,value,raw_int16). Datei darf nicht existieren.",
    )
    p.add_argument(
        "--png",
        metavar="DATEI",
        help="Optional: Plot als PNG speichern (z.B. out.png).",
    )
    p.add_argument(
        "--no-show",
        action="store_true",
        help="Kein Plot-Fenster öffnen (praktisch für automatisierte Runs).",
    )
    p.add_argument("--debug-keys", action="store_true", help="Gibt empfangene Key-Events aus")
    p.add_argument("-v", "--verbose", action="store_true", help="Mehr Ausgaben (Debug).")

    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.list_ports:
        _print_ports()
        return

    if not args.port:
        print("ERROR: --port ist erforderlich (außer bei --list-ports).", file=sys.stderr)
        ports = _available_ports()
        if ports:
            print("Verfügbare Ports:", file=sys.stderr)
            for p in ports:
                print(f"  {p}", file=sys.stderr)
        print("Tipp: oszi-remote --list-ports", file=sys.stderr)
        sys.exit(2)

    # Optional: kleine Vorwarnung, wenn der Port nicht existiert (trotzdem versuchen wir es).
    if args.verbose:
        ports = _available_ports()
        if ports and args.port not in ports:
            print(
                f"WARNING: Port {args.port!r} nicht in der aktuellen Port-Liste gefunden.",
                file=sys.stderr,
            )

    try:
        wf = read_waveform_once(
            port=args.port, baud=args.baud, channel=args.channel, timeout_s=args.timeout
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("Tipp: oszi-remote --list-ports", file=sys.stderr)
        sys.exit(2)

    if args.csv:
        try:
            write_csv(Path(args.csv), wf)
            print(f"Wrote CSV: {args.csv} (N={len(wf.volts)})")
        except FileExistsError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(2)

    viewer = Viewer(wf.volts, bins=args.bins, debug_keys=args.debug_keys)
    # Wichtig: starke Referenz, sonst werden Key-Callbacks manchmal "komisch"
    viewer.fig._viewer_ref = viewer  # type: ignore[attr-defined]

    import matplotlib.pyplot as plt

    if args.png:
        try:
            Path(args.png).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(args.png, dpi=150)
            print(f"Wrote PNG: {args.png}")
        except Exception as e:
            print(f"ERROR: Konnte PNG nicht schreiben: {e}", file=sys.stderr)
            sys.exit(2)

    if args.no_show:
        # Wenn nur Datei-Outputs gewünscht sind: nicht blockieren.
        return

    plt.show()
