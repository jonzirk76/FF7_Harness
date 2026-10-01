from __future__ import annotations

import unittest
from unittest.mock import patch

from ff7_harness.io import press


class InputTests(unittest.TestCase):
    def test_background_input_targets_window_without_activating_it(self) -> None:
        with patch("ff7_harness.io._run") as run, patch("ff7_harness.io.time.sleep"):
            press(42, "Return", 0.1, focus=False)
        self.assertEqual(run.call_args_list[0].args,
                         ("xdotool", "keydown", "--window", "42", "Return"))
        self.assertEqual(run.call_args_list[1].args,
                         ("xdotool", "keyup", "--window", "42", "Return"))
        self.assertEqual(run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
