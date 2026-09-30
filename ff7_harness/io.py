"""Window-scoped X11 capture and short, observable keyboard actions."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass


class AdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class Window:
    id: int
    title: str


def _run(*args: str, timeout: float = 10) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=True, timeout=timeout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = exc.stderr.decode(errors="replace").strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        raise AdapterError(f"{' '.join(args[:2])} failed: {detail}") from exc


def discover_windows() -> list[Window]:
    try:
        result = _run("xdotool", "search", "--onlyvisible", "--name", "FINAL FANTASY VII")
    except AdapterError:
        return []
    windows: list[Window] = []
    for raw_id in result.stdout.splitlines():
        window_id = int(raw_id)
        try:
            title = _run("xdotool", "getwindowname", str(window_id)).stdout.decode(errors="replace").strip()
        except AdapterError:
            continue
        windows.append(Window(window_id, title))
    return windows


def capture(window_id: int) -> bytes:
    if window_id <= 0:
        raise ValueError("window_id must be positive")
    png = _run("import", "-window", str(window_id), "png:-", timeout=15).stdout
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AdapterError("capture did not return a PNG image")
    return png


ALLOWED_KEYS = frozenset({
    "Up", "Down", "Left", "Right", "Return", "Escape", "space", "BackSpace",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
})


def press(window_id: int, key: str, duration: float) -> None:
    if window_id <= 0:
        raise ValueError("window_id must be positive")
    if key not in ALLOWED_KEYS:
        raise ValueError(f"unsupported key: {key}")
    if not 0.02 <= duration <= 2.0:
        raise ValueError("duration must be between 0.02 and 2 seconds")
    _run("xdotool", "windowactivate", "--sync", str(window_id))
    _run("xdotool", "keydown", key)
    try:
        time.sleep(duration)
    finally:
        _run("xdotool", "keyup", key)
