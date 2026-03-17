from __future__ import annotations

import argparse
import ctypes
import importlib.util
import sys
import time
from pathlib import Path

from PIL import Image, ImageGrab


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


def _capture_hwnd(hwnd: int, width: int, height: int) -> Image.Image | None:
    window_dc = user32.GetWindowDC(hwnd)
    if not window_dc:
        return None

    memory_dc = gdi32.CreateCompatibleDC(window_dc)
    bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
    old_bitmap = gdi32.SelectObject(memory_dc, bitmap)

    try:
        rendered = user32.PrintWindow(hwnd, memory_dc, 0)
        if rendered != 1:
            return None

        buffer_size = width * height * 4
        buffer = ctypes.create_string_buffer(buffer_size)
        copied = gdi32.GetBitmapBits(bitmap, buffer_size, buffer)
        if copied != buffer_size:
            return None

        return Image.frombuffer("RGB", (width, height), buffer, "raw", "BGRX", 0, 1)
    finally:
        gdi32.SelectObject(memory_dc, old_bitmap)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(hwnd, window_dc)


def load_app_class(module_path: Path, class_name: str):
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_path.stem] = module
    spec.loader.exec_module(module)
    try:
        return getattr(module, class_name)
    except AttributeError as exc:
        raise RuntimeError(f"Class '{class_name}' was not found in {module_path}") from exc


def capture_window(
    module_path: Path,
    class_name: str,
    output_path: Path,
    settle_seconds: float,
    geometry: str | None,
) -> None:
    app_class = load_app_class(module_path, class_name)
    app = app_class()
    if geometry:
        app.geometry(geometry)
    for _ in range(3):
        app.update_idletasks()
        app.deiconify()
        app.lift()
        app.focus_force()
        app.attributes("-topmost", True)
        app.update()
        time.sleep(0.25)
    time.sleep(settle_seconds)
    app.update_idletasks()
    app.update()
    app.attributes("-topmost", False)
    app.update()

    left = app.winfo_rootx()
    top = app.winfo_rooty()
    width = app.winfo_width()
    height = app.winfo_height()
    right = left + width
    bottom = top + height

    image = _capture_hwnd(app.winfo_id(), width, height)
    if image is None or image.getbbox() is None:
        image = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    app.destroy()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture a screenshot of a Tk app window.")
    parser.add_argument("--module-path", required=True)
    parser.add_argument("--class-name", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--settle-seconds", type=float, default=1.4)
    parser.add_argument("--geometry", default="")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    capture_window(
        Path(args.module_path).resolve(),
        args.class_name,
        Path(args.output).resolve(),
        args.settle_seconds,
        args.geometry or None,
    )


if __name__ == "__main__":
    main()
