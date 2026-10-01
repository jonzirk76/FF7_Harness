from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from ff7_harness import cli
from ff7_harness.io import AdapterError, Window
from ff7_harness.store import Store
from ff7_harness.vision import pixel_change


def png(color: str) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (32, 32), color).save(output, format="PNG")
    return output.getvalue()


class FoundationTests(unittest.TestCase):
    def test_run_and_objective_survive_reopening_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with Store(root) as store:
                store.set_assist_policy("No gameplay assists; normal in-game saves allowed")
                objective_id = store.add_objective("Leave platform", "New field scene is visible")
                event_id = store.event("observation", {"description": "platform"}, 123)
            with Store(root) as store:
                status = store.status()
                self.assertEqual(status["run"]["assist_policy"],
                                 "No gameplay assists; normal in-game saves allowed")
                self.assertEqual(status["objectives"][0]["id"], objective_id)
                self.assertEqual(status["recent_events"][0]["id"], event_id)

    def test_action_records_before_and_after_frames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            frames = iter((png("black"), png("white")))
            output = io.StringIO()
            with patch("ff7_harness.cli.capture", side_effect=lambda _: next(frames)), \
                 patch("ff7_harness.cli.press") as press, \
                 patch("ff7_harness.cli.time.sleep"), redirect_stdout(output):
                result = cli.main(["--data-dir", directory, "act", "--window-id", "42",
                                   "--key", "Up", "--seconds", "0.1"])
            self.assertEqual(result, 0)
            press.assert_called_once_with(42, "Up", 0.1, focus=True)
            report = json.loads(output.getvalue())
            self.assertAlmostEqual(report["after"]["pixel_change"], 1.0)
            with Store(Path(directory)) as store:
                kinds = [row[0] for row in store.db.execute("SELECT kind FROM events ORDER BY id")]
                self.assertEqual(kinds, ["action_requested", "observation", "observation",
                                         "action_completed"])
                self.assertEqual(store.db.execute("SELECT COUNT(*) FROM frames").fetchone()[0], 2)

    def test_action_follows_window_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with patch("ff7_harness.cli.capture", side_effect=[png("black"),
                  AdapterError("old window closed"), png("white")]), \
                 patch("ff7_harness.cli.discover_windows", return_value=[Window(99, "FINAL FANTASY VII")]), \
                 patch("ff7_harness.cli.press"), \
                 patch("ff7_harness.cli.time.sleep"), redirect_stdout(output):
                result = cli.main(["--data-dir", directory, "act", "--window-id", "42",
                                   "--key", "Return", "--seconds", "0.1"])
            self.assertEqual(result, 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["after"]["window_id"], 99)
            with Store(Path(directory)) as store:
                event = store.status()["recent_events"][0]
                self.assertEqual(event["kind"], "action_completed")
                self.assertTrue(event["payload"]["window_transition"])

    def test_identical_images_have_zero_change(self) -> None:
        frame = png("green")
        self.assertEqual(pixel_change(frame, frame), 0.0)


if __name__ == "__main__":
    unittest.main()
