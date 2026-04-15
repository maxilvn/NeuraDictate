"""Audio recording via sounddevice - WAV 16kHz mono 16-bit PCM."""

import io
import threading
import wave

import numpy as np
import sounddevice as sd

from . import config

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
MIN_RECORDING_BYTES = 8000


class Recorder:
    def __init__(self):
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        with self._lock:
            if self._recording:
                return
            self._frames.clear()
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._recording = True

    def stop(self) -> str | None:
        """Stop recording and save WAV. Returns file path or None if too short."""
        with self._lock:
            if not self._recording:
                return None
            self._recording = False
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

        if not self._frames:
            return None

        audio_data = np.concatenate(self._frames)
        self._frames.clear()

        wav_path = str(config.RECORDING_PATH)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())

        wav_bytes = buf.getvalue()
        if len(wav_bytes) < MIN_RECORDING_BYTES:
            return None

        with open(wav_path, "wb") as f:
            f.write(wav_bytes)

        return wav_path

    def _audio_callback(self, indata, frames, time_info, status):
        if self._recording:
            self._frames.append(indata.copy())
