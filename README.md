# NeuraDictate

Lokale Speech-to-Text Diktiersoftware. Laeuft 100% auf deinem Rechner - keine Daten an externe Server.

## Quick Start

**Voraussetzung:** Python 3.10+ ([python.org](https://python.org) - bei Windows "Add to PATH" anhaken)

```bash
git clone https://github.com/DEIN-USERNAME/NeuraDictate.git
cd NeuraDictate
python start.py
```

Beim ersten Start:
- Dependencies werden automatisch installiert
- Das Whisper "small" Model (466 MB) wird heruntergeladen
- App startet im Hintergrund (Tray-Icon)

### macOS
macOS fragt nach **Accessibility-Berechtigung** (Systemeinstellungen > Datenschutz & Sicherheit > Bedienungshilfen).

### Windows
Alternativ: Doppelklick auf `VoiceInput-Windows.vbs`

## Benutzung

1. **Taste gedrueckt halten** = Aufnahme
2. **Loslassen** = Transkription + Auto-Paste

| Plattform | Standard-Hotkey | Alternativen |
|-----------|----------------|--------------|
| macOS     | Fn             | Right Option, Right Command, Left Control |
| Windows   | Right Alt      | Caps Lock, Scroll Lock, Pause |

Einstellungen ueber **Tray-Icon > Control Panel**.

## Models

| Model | Groesse | Speed | Qualitaet |
|-------|---------|-------|-----------|
| tiny | 75 MB | 5/5 | 2/5 |
| base | 142 MB | 4/5 | 3/5 |
| **small** | **466 MB** | **3/5** | **4/5 (empfohlen)** |
| medium | 1.5 GB | 2/5 | 4/5 |
| large-v3-turbo | 1.5 GB | 4/5 | 5/5 |
| large-v3 | 3 GB | 1/5 | 5/5 |

Weitere Models ueber Settings > Models Tab herunterladen.

## Features

- Automatische Spracherkennung (merkt sich die zuletzt erkannte Sprache)
- Konfigurierbarer Hotkey
- Model-Management (Download/Remove)
- Session-basierte Transcript-History mit Copy-Button
- Auto-Paste in aktives Fenster
- HUD-Overlay (Listening/Transcribing/Copied)
- Dark Mode Settings-Panel
- Laeuft komplett lokal, keine Cloud
