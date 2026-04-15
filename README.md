# Voice Input - Lokale Speech-to-Text Alternative

Lokale WhisperFlow-Alternative. Läuft 100% auf deinem Rechner - keine Daten an externe Server, DSGVO-konform, keine laufenden Kosten.

## Installation (Windows)

1. **Doppelklick auf `setup_windows.bat`**
2. Fertig. Desktop-Shortcut "Voice Input" wird erstellt.

### Voraussetzungen

- Windows 10/11
- Python 3.10+ (wird automatisch installiert falls nicht vorhanden)
- Mikrofon
- Optional: NVIDIA GPU mit CUDA für schnellere Transcription

## Benutzung

1. Starte "Voice Input" vom Desktop
2. **Rechte Alt-Taste gedrückt halten** = Aufnahme läuft
3. **Loslassen** = Text wird transkribiert und eingefügt

### Status-Anzeige (HUD)

| Farbe  | Bedeutung      |
|--------|---------------|
| Rot    | Aufnahme läuft |
| Orange | Transkribiert  |
| Grün   | Fertig/Kopiert |
| Pink   | Fehler         |

### Settings

Rechtsklick auf das Tray-Icon → Settings:

- **Hotkey**: Right Alt, Caps Lock, Scroll Lock, Pause
- **Model**: tiny (75MB, schnell) bis large-v3-turbo (1.5GB, beste Qualität)
- **Sprache**: Auto-Detect oder manuell (DE, EN, FR, ...)
- **Auto-Paste**: Text direkt einfügen oder nur in Zwischenablage

## Modelle

| Model           | Größe  | Geschwindigkeit | Qualität |
|-----------------|--------|-----------------|----------|
| tiny            | 75 MB  | Sehr schnell    | Okay     |
| base            | 142 MB | Schnell         | Gut      |
| small           | 466 MB | Mittel          | Sehr gut |
| medium          | 1.5 GB | Langsamer       | Exzellent|
| large-v3-turbo  | 1.5 GB | Mittel          | Beste    |

## Technologie

- **faster-whisper** (CTranslate2) - optimierte Whisper-Implementierung
- Läuft auf CPU und NVIDIA GPU (CUDA)
- Audio-Aufnahme via sounddevice (16kHz, mono)
