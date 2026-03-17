from __future__ import annotations

import argparse
import os
from pathlib import Path

from flowerapp.core.engine import calculate_agency
from flowerapp.core.storage import load_project, save_project

DATA_DIR = Path("data")
APP_NAME = "Lotus"
CANONICAL_CLI_NAME = "lotus"
LEGACY_CLI_NAME = "flowerapp"


def _voice11_helpers():
    try:
        import voice11

        voice11.check_speech_dependencies()
    except ImportError as exc:
        raise SystemExit(
            "Voice11 helpers are unavailable. Install the speech extras (e.g., `pip install .[speech]` "
            "or `pip install pyttsx3 pydub`) before using the `tts` subcommand."
        ) from exc
    return voice11.create_mp3, voice11.live_text_to_speech, voice11.list_available_voices


def _project_path(project_name: str) -> Path:
    return DATA_DIR / project_name


def _load_project(project_name: str) -> dict | None:
    return load_project(str(_project_path(project_name)))


def _format_summary_text(project: dict, summary: dict) -> str:
    metadata = project.get("metadata", {})
    project_name = metadata.get("project_name") or metadata.get("project_id") or "project"
    perceptual = summary["subscores"]["perceptual_latitude"]["score"]
    caps = summary["subscores"]["perceptual_latitude"].get("caps_applied", [])
    caps_text = "" if not caps else f" Caps applied: {', '.join(caps)}."
    return (
        f"{project_name} agency score is {summary['agency_total']:.1f}. "
        f"Perceptual latitude sits at {perceptual:.1f}.{caps_text}"
    )


def _print_scores(results: dict) -> None:
    print(f"Agency total: {results['agency_total']:.1f}")
    for name, data in results["subscores"].items():
        caps = data.get("caps_applied", [])
        caps_text = "" if not caps else f" (Caps: {', '.join(caps)})"
        friendly_name = name.replace("_", " ").title()
        print(f"  - {friendly_name}: {data['score']:.1f}{caps_text}")


def _missing_project_message(project_name: str) -> str:
    return (
        f"No project data for {project_name}. "
        f"Run `{CANONICAL_CLI_NAME} init --project {project_name}` first. "
        f"(`{LEGACY_CLI_NAME}` also works.)"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=CANONICAL_CLI_NAME,
        description=f"{APP_NAME} scoring assistant",
        epilog=f"`{LEGACY_CLI_NAME}` remains available as a compatibility alias.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a Lotus project scaffold")
    init_parser.add_argument("--project", default="default", help="Project identifier")

    score_parser = subparsers.add_parser("score", help="Evaluate stored Lotus intake data")
    score_parser.add_argument("--project", default="default", help="Project identifier")

    web_parser = subparsers.add_parser("web", help="Launch the Lotus web interface")
    web_parser.add_argument("--project", default="default", help="Project identifier")
    web_parser.add_argument("--host", default="127.0.0.1", help="Host for the webserver")
    web_parser.add_argument("--port", type=int, default=8000, help="Port for the webserver")

    tts_parser = subparsers.add_parser("tts", help="Speak or render a summary via Voice11")
    tts_parser.add_argument("--project", default="default", help="Project identifier")
    tts_parser.add_argument("-t", "--text", help="Override text to speak or save")
    tts_parser.add_argument("-o", "--output", help="Path for generated MP3 (suffix added automatically)")
    tts_parser.add_argument("-v", "--voice-id", help="pyttsx3 voice identifier")
    tts_parser.add_argument("-r", "--rate", type=int, help="Speech rate (words per minute)")
    tts_parser.add_argument("--bitrate", default="192k", help="MP3 bitrate when exporting to file")
    tts_parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List pyttsx3 voices that Voice11 can use",
    )
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "init":
        target = _project_path(args.project)
        data = {
            "app_version": "1.0.0",
            "session_schema_version": 1,
            "metadata": {"project_id": args.project, "project_name": args.project},
            "intake": {"signals": [], "constraints": []},
            "scoring": {"agency_total": 0, "subscores": {}},
        }
        save_project(data, str(target))
        print(f"{APP_NAME} project {args.project} initialized at {target}")
        return

    if args.command == "score":
        project = _load_project(args.project)
        if project is None:
            raise SystemExit(_missing_project_message(args.project))
        results = calculate_agency(project.get("intake", {}))
        _print_scores(results)
        return

    if args.command == "web":
        project = args.project
        proj_path = _project_path(project)
        os.environ["PROJ_PATH"] = str(proj_path)
        from flowerapp.web import app

        import uvicorn

        uvicorn.run(app, host=args.host, port=args.port)
        return

    if args.command == "tts":
        create_mp3, live_text_to_speech, list_available_voices = _voice11_helpers()

        if args.list_voices:
            for voice in list_available_voices():
                print(voice)
            return

        text = args.text
        if not text:
            project = _load_project(args.project)
            if project is None:
                raise SystemExit(_missing_project_message(args.project))
            results = calculate_agency(project.get("intake", {}))
            text = _format_summary_text(project, results)

        if args.output:
            destination = create_mp3(
                text,
                Path(args.output),
                voice_id=args.voice_id,
                rate=args.rate,
                bitrate=args.bitrate,
            )
            print(f"MP3 ready at: {destination}")
        else:
            live_text_to_speech(text, voice_id=args.voice_id, rate=args.rate)
        return

    raise SystemExit("Unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
