"""PyInstaller entrypoint for oszi-remote (console app)."""

from scope_noise_hist.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
