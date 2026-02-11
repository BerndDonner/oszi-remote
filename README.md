# oszi-remote

Kleines Tool zum Auslesen der **Memory-Waveform** vom GW Instek **GDS-1000B** (oder kompatibel)
und Anzeigen von:

- Zeitreihe (Samples)
- Histogramm inkl. Gauss-Fit (µ/σ aus Messdaten)

## Bedienung (Windows)

Nach dem Entpacken:

- `Start_oszi-remote.bat` doppelklicken (empfohlen)

### Ports finden

```bat
oszi-remote --list-ports
```

### Plot anzeigen

```bat
oszi-remote --port COM5 --channel 1 --bins 60
```

Tasten im Plot-Fenster:

- `1/2/3` oder `n/p`: Ansichten umschalten
- `q` oder `Esc`: schließen

## CSV export

CSV-Spalten: `index,value,raw_int16`

```bat
oszi-remote --port COM5 --csv messung.csv
```

Nach erfolgreichem Schreiben meldet das Programm z.B.:

```
Wrote CSV: messung.csv (N=10000)
```

## PNG export (optional)

```bat
oszi-remote --port COM5 --png plot.png
```

Nur Dateien schreiben, **ohne** Plot-Fenster:

```bat
oszi-remote --port COM5 --csv messung.csv --png plot.png --no-show
```
