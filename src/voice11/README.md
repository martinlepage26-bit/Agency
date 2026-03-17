# Voice11 Helpers

This package exposes lightweight helpers that render MP3s or speak text via Voice11.

## Features

- `create_mp3(text, output_path, voice_id=None, rate=None)` – renders text to an MP3 using `pyttsx3` + `pydub`.
- `live_text_to_speech(text, voice_id=None, rate=None)` – speaks text immediately through the default audio device.
- `voice11.cli` – a small CLI wrapper that renders MP3s, speaks text live, or lists available voices.

## Requirements

Install the optional speech dependencies before using the CLI:

```bash
pip install .[speech]
```

`pydub` requires `ffmpeg` or `avconv` on your PATH (e.g., `sudo apt install ffmpeg` / `brew install ffmpeg`).

## CLI Usage

```bash
python -m voice11.cli mp3 -t 'Hello Lotus' -o ~/Desktop/voice11-greeting.mp3
```

```bash
python -m voice11.cli live -t 'Live text to speech is ready!'
```

```bash
python -m voice11.cli list
```

If you install the package, the console script `voice11` is also available:

```bash
voice11 mp3 -t 'Hi' -o output.mp3
```
