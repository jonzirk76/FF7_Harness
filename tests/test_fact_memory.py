from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from ff7_harness.cli import main
from ff7_harness.store import Store


class FactMemoryTests(unittest.TestCase):
    def test_verified_fact_with_provenance_survives_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with Store(root) as store:
                event_id = store.event("observation", {"movement": "confirmed"}, 1)
            with redirect_stdout(io.StringIO()):
                result = main(["--data-dir", directory, "fact", "field movement",
                               "Up moved Cloud", "--confidence", "0.95",
                               "--source-event", str(event_id), "--status", "verified"])
            self.assertEqual(result, 0)
            with Store(root) as store:
                fact = store.status()["facts"][0]
                self.assertEqual(fact["status"], "verified")
                self.assertEqual(fact["source_event_id"], event_id)


if __name__ == "__main__":
    unittest.main()
