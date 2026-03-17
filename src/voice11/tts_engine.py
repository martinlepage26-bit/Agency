"""Small TTS plumbing for Voice11 helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Iterable, Optional

import pyttsx3
from pydub import AudioSegment


def list_available_voices() -> Iterable[str]:
    """List registered voices so callers can bind a voice_id."""

    engine = pyttsx3.init()
    try:
        for voice in engine.getProperty("voices"):
            yield voice.id
    finally:
        engine.stop()


def _configure_engine(engine: pyttsx3.Engine, voice_id: Optional[str], rate: Optional[int]) -> None:
    if voice_id:
        engine.setProperty("voice", voice_id)
    if rate:
        engine.setProperty("rate", rate)


def create_mp3(
    text: str,
    output_path: Path | str,
    voice_id: Optional[str] = None,
    rate: Optional[int] = None,
    bitrate: str = "192k",
) -> Path:
    """Render ``text`` to MP3 while leveraging pyttsx3 to keep the stack offline.

    The function first creates a temporary WAV file via ``pyttsx3`` and then converts
    it to MP3 with ``pydub`` (requires ``ffmpeg`` on PATH).
    """

    output_path = Path(output_path)
    output_path = output_path.with_suffix(".mp3")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    engine = pyttsx3.init()
    temp_wav: Path | None = None
    try:
        _configure_engine(engine, voice_id, rate)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            temp_wav = Path(tmp.name)
        engine.save_to_file(text, str(temp_wav))
        engine.runAndWait()
        segment = AudioSegment.from_wav(str(temp_wav))
        segment.export(output_path, format="mp3", bitrate=bitrate)
    finally:
        engine.stop()
        if temp_wav is not None and temp_wav.exists():
            temp_wav.unlink()
    return output_path


def live_text_to_speech(
    text: str,
    voice_id: Optional[str] = None,
    rate: Optional[int] = None,
) -> None:
    """Speak ``text`` immediately through the default audio device."""

    engine = pyttsx3.init()
    try:
        _configure_engine(engine, voice_id, rate)
        engine.say(text)
        engine.runAndWait()
    finally:
        engine.stop()
