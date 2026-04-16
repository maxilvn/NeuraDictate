# NeuraDictate

Lokale Speech-to-Text Diktiersoftware von NEURA Robotics. Laeuft 100% auf deinem Rechner — keine Daten an externe Server, keine Cloud, keine Kosten.

## Quick Start

**Voraussetzung:** Python 3.10+ ([python.org](https://python.org) — bei Windows **"Add to PATH" anhaken!**)

### Windows (1-Klick Installation)

1. **[ZIP herunterladen](https://github.com/maxilvn/NeuraDictate/archive/refs/heads/main.zip)** und entpacken
2. **Doppelklick auf `install.bat`**

Das war's. `install.bat` macht automatisch:
- Installiert Python (falls nicht vorhanden) via winget
- Installiert alle Dependencies
- Laedt das Whisper-Model (466 MB) herunter
- Erstellt Desktop-Verknuepfung
- Richtet Autostart ein
- Startet NeuraDictate

Beim ersten Start fragt Windows evtl. nach Berechtigung fuer den Keyboard-Listener — bestaetigen.

### macOS (1-Klick Installation)

1. **[ZIP herunterladen](https://github.com/maxilvn/NeuraDictate/archive/refs/heads/main.zip)** und entpacken
2. **Doppelklick auf `install-mac.command`**

Das Script:
- Installiert alle Dependencies
- Laedt das Whisper-Model (466 MB) herunter
- Installiert `NeuraDictate.app` nach `/Applications`
- Richtet Autostart ein (LaunchAgent)
- Startet die App

macOS fragt beim ersten Start nach **Accessibility-Berechtigung** (Systemeinstellungen > Datenschutz & Sicherheit > Bedienungshilfen) — das ist fuer den globalen Hotkey noetig.

Die App erscheint danach im Launchpad und /Applications wie jede andere App.

## Benutzung

1. **Taste gedrueckt halten** = Aufnahme laeuft
2. **Loslassen** = Text wird transkribiert und automatisch eingefuegt
3. **Erneut druecken waehrend Transkription** = Abbrechen und neu aufnehmen

| Plattform | Standard-Hotkey |
|-----------|----------------|
| macOS     | Fn             |
| Windows   | Right Alt      |

Der Hotkey kann in den Settings beliebig geaendert werden (jede Taste moeglich).

Einstellungen ueber **Tray-Icon > Control Panel** oder **Menu-Bar-Icon (macOS)**.

## Features

- **Beliebiger Hotkey** — jede Taste als Push-to-Talk konfigurierbar
- **Sprachauswahl** — Auto-Detect, Deutsch, English (uebersetzt), Francais, Espanol
- **Filler-Entfernung** — "aehm", "halt", "basically" etc. werden automatisch entfernt
- **Model-Management** — Models im Settings-Panel herunterladen/entfernen
- **Session-History** — Alle Transkripte der Sitzung mit Copy-Button
- **Auto-Paste** — Text wird direkt ins aktive Fenster eingefuegt
- **HUD-Overlay** — Animiertes NEURA-Icon zeigt Status (Listening/Transcribing/Copied)
- **Autosave** — Einstellungen werden sofort gespeichert
- **Komplett lokal** — Keine Cloud, keine API-Keys, DSGVO-konform

## Models

| Model | Groesse | Speed | Qualitaet |
|-------|---------|-------|-----------|
| tiny | 75 MB | 5/5 | 2/5 |
| base | 142 MB | 4/5 | 3/5 |
| **small** | **466 MB** | **3/5** | **4/5 (empfohlen)** |
| medium | 1.5 GB | 2/5 | 4/5 |
| large-v3-turbo | 1.5 GB | 4/5 | 5/5 |
| large-v3 | 3 GB | 1/5 | 5/5 |

Das "small" Model wird beim ersten Start automatisch heruntergeladen. Weitere Models koennen im Settings > Models Tab verwaltet werden.

## Technologie

- **faster-whisper** (CTranslate2) fuer lokale Transkription
- Unterstuetzt CPU und NVIDIA GPU (CUDA)
- macOS: Quartz (Hotkey), AppKit (HUD), rumps (Tray)
- Windows: pynput (Hotkey), tkinter (HUD), pystray (Tray)

## Fehlerbehebung

**Windows: "Python nicht gefunden"**
→ Python neu installieren und **"Add to PATH"** anhaken

**Windows: Nichts passiert beim Start**
→ `python start.py` im Terminal ausfuehren und Fehlermeldung pruefen. Falls ERROR.txt erstellt wurde, Inhalt pruefen.

**macOS: Hotkey reagiert nicht**
→ Accessibility-Berechtigung in Systemeinstellungen pruefen

**Model-Download haengt**
→ Internetverbindung pruefen, ggf. App neu starten
