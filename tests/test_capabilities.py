from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from ff7_harness.capabilities import catalog
from ff7_harness.cli import main


class CapabilityCatalogTests(unittest.TestCase):
    def test_catalog_is_unique_machine_readable_and_explicit_about_evidence(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["capabilities"]), 0)
        data = json.loads(output.getvalue())
        self.assertEqual(data, catalog())
        names = [entry["name"] for entry in data["capabilities"]]
        self.assertEqual(len(names), len(set(names)))
        for entry in data["capabilities"]:
            self.assertIn(entry["maturity"], ("live_verified", "tested_only", "experimental"))
            for field in ("command", "requires", "effect", "evidence", "limits"):
                self.assertTrue(entry[field].strip(), (entry["name"], field))


if __name__ == "__main__":
    unittest.main()
