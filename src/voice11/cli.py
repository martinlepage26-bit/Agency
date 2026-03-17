"""Command-line helpers for the Voice11 styles."""

from __future__ import annotations

import argparse

from . import (
    Voice11DependencyError,
    check_speech_dependencies,
    create_mp3,
    list_available_voices,
    live_text_to_speech,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="voice11", description="Voice11 MP3 export + live TTS utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mp3 = subparsers.add_parser("mp3", help="render text to an MP3 file")
    mp3.add_argument("-t", "--text", required=True, help="Text to render")
    mp3.add_argument("-o", "--output", default="voice11-output.mp3", help="Output MP3 path")
    mp3.add_argument("-v", "--voice-id", help="Voice identifier (call `voice11 list` to inspect)")
    mp3.add_argument("-r", "--rate", type=int, help="Driving rate (words per minute)")
    mp3.add_argument("--bitrate", default="192k", help="MP3 bitrate (example: 192k)")

    live = subparsers.add_parser("live", help="speak text on the default audio device")
    live.add_argument("-t", "--text", required=True, help="Text to vocalize now")
    live.add_argument("-v", "--voice-id", help="Voice identifier for pyttsx3")
    live.add_argument("-r", "--rate", type=int, help="Speech rate override")

    subparsers.add_parser("list", help="list voices registered with pyttsx3")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    try:
        check_speech_dependencies()

        if args.command == "mp3":
            destination = create_mp3(
                args.text,
                args.output,
                voice_id=args.voice_id,
                rate=args.rate,
                bitrate=args.bitrate,
            )
            print(f"MP3 ready at: {destination}")
            return 0

        if args.command == "live":
            live_text_to_speech(args.text, voice_id=args.voice_id, rate=args.rate)
            return 0

        if args.command == "list":
            for voice in list_available_voices():
                print(voice)
            return 0
    except Voice11DependencyError as exc:
        raise SystemExit(str(exc)) from exc

    raise SystemExit("Unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
