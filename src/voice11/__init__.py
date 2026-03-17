"""Voice11 helpers for MP3 rendering and live text-to-speech."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Iterable

_DEPENDENCY_MESSAGE = (
    "Voice11 helpers are unavailable. Install the speech extras "
    "(e.g., `pip install .[speech]` or `pip install pyttsx3 pydub`) before using Voice11."
)


class Voice11DependencyError(ImportError):
    """Raised when optional speech dependencies are unavailable."""


def _load_tts_engine():
    try:
        return import_module(".tts_engine", __name__)
    except ImportError as exc:
        missing = exc.name or ""
        if missing == "pyttsx3" or missing == "pydub" or missing.startswith("pydub."):
            raise Voice11DependencyError(_DEPENDENCY_MESSAGE) from exc
        raise


def check_speech_dependencies() -> None:
    """Fail fast with a clear message when optional speech extras are missing."""

    _load_tts_engine()


def create_mp3(
    text: str,
    output_path: Path | str,
    voice_id: str | None = None,
    rate: int | None = None,
    bitrate: str = "192k",
) -> Path:
    return _load_tts_engine().create_mp3(
        text,
        output_path,
        voice_id=voice_id,
        rate=rate,
        bitrate=bitrate,
    )


def live_text_to_speech(
    text: str,
    voice_id: str | None = None,
    rate: int | None = None,
) -> None:
    _load_tts_engine().live_text_to_speech(text, voice_id=voice_id, rate=rate)


def list_available_voices() -> Iterable[str]:
    return _load_tts_engine().list_available_voices()


__all__ = [
    "Voice11DependencyError",
    "check_speech_dependencies",
    "create_mp3",
    "live_text_to_speech",
    "list_available_voices",
]
