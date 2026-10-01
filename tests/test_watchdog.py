from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ff7_harness.store import Store
from ff7_harness.watchdog import StrategyWatchdog


class StrategyWatchdogTests(unittest.TestCase):
    def test_repeated_abandonment_reduces_budget(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with Store(Path(directory)) as store:
                objective_id = store.add_objective("Reach a menu", "Menu is visible")
                watchdog = StrategyWatchdog(store)
                first = watchdog.start("wait_for_menu", "Menu appears", objective_id, 60, 3)
                self.assertEqual((first["allowed_seconds"], first["stall_limit"]), (60, 3))
                watchdog.end("abandoned", "No menu appeared")
                second = watchdog.start("wait_for_menu", "Menu appears", objective_id, 60, 3)
                self.assertEqual((second["allowed_seconds"], second["stall_limit"]), (30, 2))
                watchdog.end("abandoned", "Still no menu")
                third = watchdog.start("wait_for_menu", "Menu appears", objective_id, 60, 3)
                self.assertEqual((third["allowed_seconds"], third["stall_limit"]), (20, 1))

    def test_stall_evidence_abandons_and_survives_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with Store(root) as store:
                objective_id = store.add_objective("Reach a menu", "Menu is visible")
                watchdog = StrategyWatchdog(store)
                watchdog.start("wait_for_menu", "Menu appears", objective_id, 60, 2)
                first = store.event("observation", {"state": "credits"}, 1)
                watchdog.assess("stalled", first, "Credits continue")
                self.assertEqual(watchdog.status()["active"]["stall_count"], 1)
                second = store.event("observation", {"state": "credits"}, 2)
                watchdog.assess("stalled", second, "Same sequence repeats")
                self.assertIsNone(watchdog.status()["active"])
            with Store(root) as store:
                watchdog = StrategyWatchdog(store)
                self.assertEqual(watchdog.status()["latest"]["status"], "abandoned")
                retry = watchdog.start("wait_for_menu", "Menu appears", objective_id, 60, 2)
                self.assertEqual(retry["stall_limit"], 1)

    def test_elapsed_deadline_stops_next_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with Store(Path(directory)) as store:
                objective_id = store.add_objective("Reach a menu", "Menu is visible")
                watchdog = StrategyWatchdog(store)
                watchdog.start("wait_for_menu", "Menu appears", objective_id, 60, 3)
                with store.db:
                    store.db.execute("UPDATE strategies SET deadline_at = ? WHERE status = 'active'",
                                     ("2000-01-01T00:00:00+00:00",))
                with self.assertRaisesRegex(ValueError, "deadline elapsed"):
                    watchdog.guard()
                self.assertEqual(watchdog.status()["latest"]["status"], "abandoned")


if __name__ == "__main__":
    unittest.main()
