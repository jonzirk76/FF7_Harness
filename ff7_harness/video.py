"""Low-resolution, window-targeted clips for temporal state evidence."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import time
from pathlib import Path
from uuid import uuid4

from .io import discover_windows
from .store import Store


class VideoError(RuntimeError):
    pass


def _ensure_schema(store: Store) -> None:
    store.db.execute("""
        CREATE TABLE IF NOT EXISTS clips (
            id INTEGER PRIMARY KEY,
            run_id INTEGER NOT NULL REFERENCES runs(id),
            event_id INTEGER NOT NULL UNIQUE REFERENCES events(id),
            path TEXT NOT NULL,
            window_id INTEGER NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            fps INTEGER NOT NULL,
            duration_seconds REAL NOT NULL,
            frame_count INTEGER NOT NULL,
            sha256 TEXT NOT NULL
        )
    """)
    store.db.commit()


def latest_clip(store: Store) -> dict[str, object] | None:
    _ensure_schema(store)
    row = store.db.execute("SELECT * FROM clips WHERE run_id = 1 ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def record_clip(store: Store, window_id: int, seconds: int = 8, fps: int = 4,
                width: int = 640) -> dict[str, object]:
    if not 1 <= seconds <= 30:
        raise ValueError("clip duration must be between 1 and 30 seconds")
    if not 1 <= fps <= 10:
        raise ValueError("clip frame rate must be between 1 and 10 fps")
    if not 320 <= width <= 960 or width % 2:
        raise ValueError("clip width must be an even number between 320 and 960")
    windows = {window.id: window for window in discover_windows()}
    if window_id not in windows:
        raise VideoError("window ID is not a visible FF7 window")
    display = os.environ.get("DISPLAY")
    if not display:
        raise VideoError("DISPLAY is unset; X11 capture is unavailable")

    _ensure_schema(store)
    directory = store.root / "clips"
    directory.mkdir(exist_ok=True)
    filename = f"{time.time_ns()}-{uuid4().hex}.mp4"
    final_path = directory / filename
    temporary = directory / (filename + ".part.mp4")
    request_event_id = store.event("clip_requested", {
        "window_id": window_id, "window_title": windows[window_id].title,
        "seconds": seconds, "fps": fps, "width": width,
    }, time.monotonic_ns())
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
        "-f", "x11grab", "-window_id", str(window_id), "-draw_mouse", "0",
        "-framerate", str(fps), "-i", display, "-t", str(seconds),
        "-vf", f"scale={width}:-2", "-an", "-c:v", "libx264",
        "-preset", "ultrafast", "-crf", "30", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-n", str(temporary),
    ]
    try:
        subprocess.run(command, capture_output=True, check=True, timeout=seconds + 30)
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=width,height,nb_frames", "-of", "json", str(temporary),
        ], capture_output=True, check=True, timeout=10)
        metadata = json.loads(probe.stdout)
        stream = metadata["streams"][0]
        duration = float(metadata["format"]["duration"])
        frame_count = int(stream["nb_frames"])
        if duration <= 0 or frame_count <= 0:
            raise VideoError("encoded clip has no frames")
        temporary.replace(final_path)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
            KeyError, IndexError, ValueError, VideoError) as exc:
        temporary.unlink(missing_ok=True)
        detail = exc.stderr.decode(errors="replace").strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        store.event("clip_failed", {"request_event_id": request_event_id, "error": detail},
                    time.monotonic_ns())
        raise VideoError(detail) from exc

    relative = str(final_path.relative_to(store.root))
    digest = hashlib.sha256(final_path.read_bytes()).hexdigest()
    event_id = store.event("clip_completed", {
        "request_event_id": request_event_id, "window_id": window_id,
        "path": relative, "duration_seconds": duration, "frame_count": frame_count,
    }, time.monotonic_ns())
    with store.db:
        cursor = store.db.execute(
            """INSERT INTO clips(run_id, event_id, path, window_id, width, height, fps,
               duration_seconds, frame_count, sha256) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_id, relative, window_id, int(stream["width"]), int(stream["height"]),
             fps, duration, frame_count, digest),
        )
    return {"clip_id": int(cursor.lastrowid), "path": str(final_path),
            "duration_seconds": duration, "frame_count": frame_count,
            "width": int(stream["width"]), "height": int(stream["height"]), "fps": fps}
