# NeuraDictate

Lokale Speech-to-Text Diktiersoftware von NEURA Robotics. Laeuft 100% auf deinem Rechner — keine Daten an externe Server, keine Cloud, keine Kosten.

## Quick Start

**Voraussetzung:** Python 3.10+ ([python.org](https://python.org) — bei Windows **"Add to PATH" anhaken!**)

### Windows

1. Python installieren: [python.org/downloads](https://python.org/downloads) → **"Add to PATH" anhaken**
2. Projekt herunterladen:
   - **Option A:** [ZIP herunterladen](https://github.com/maxilvn/NeuraDictate/archive/refs/heads/main.zip) und entpacken
   - **Option B:** `git clone https://github.com/maxilvn/NeuraDictate.git`
3. Doppelklick auf `VoiceInput-Windows.vbs` (oder `python start.py` im Terminal)
4. Beim ersten Start werden automatisch alle Dependencies installiert und das Whisper-Model (466 MB) heruntergeladen

### macOS

```bash
git clone https://github.com/maxilvn/NeuraDictate.git
cd NeuraDictate
python3 start.py
```

macOS fragt nach **Accessibility-Berechtigung** (Systemeinstellungen > Datenschutz & Sicherheit > Bedienungshilfen).

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
