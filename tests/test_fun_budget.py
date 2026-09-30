from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ff7_harness.fun import FunBudget
from ff7_harness.store import Store


class FunBudgetTests(unittest.TestCase):
    def test_excursion_and_return_objective_survive_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with Store(root) as store:
                objective_id = store.add_objective("Reach next town", "Town name appears")
                fun = FunBudget(store)
                excursion_id = fun.start("Explore side path", "It looks interesting", objective_id)
                self.assertEqual(fun.status()["minutes_per_excursion"], 30)
            with Store(root) as store:
                fun = FunBudget(store)
                active = fun.status()["active"]
                self.assertEqual(active["id"], excursion_id)
                self.assertEqual(active["return_objective_id"], objective_id)
                self.assertGreater(fun.status()["remaining_seconds"], 0)
                fun.end("Found a scenic detour")
                self.assertIsNone(fun.status()["active"])
                self.assertEqual(fun.status()["latest"]["outcome"], "Found a scenic detour")

    def test_urgent_objective_blocks_and_interrupts_fun(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with Store(Path(directory)) as store:
                objective_id = store.add_objective("Continue story", "Scene changes")
                fun = FunBudget(store)
                fun.start("Explore", "Curiosity", objective_id)
                fun.set_urgency(objective_id, "urgent")
                self.assertIsNone(fun.status()["active"])
                self.assertEqual(fun.status()["latest"]["status"], "interrupted")
                with self.assertRaisesRegex(ValueError, "urgent objective"):
                    fun.start("Explore again", "Curiosity", objective_id)

    def test_elapsed_budget_stops_discretionary_actions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with Store(Path(directory)) as store:
                objective_id = store.add_objective("Continue story", "Scene changes")
                fun = FunBudget(store)
                fun.start("Explore", "Curiosity", objective_id)
                with store.db:
                    store.db.execute("UPDATE fun_excursions SET deadline_at = ? WHERE status = 'active'",
                                     ("2000-01-01T00:00:00+00:00",))
                with self.assertRaisesRegex(ValueError, "budget elapsed"):
                    fun.guard()
                self.assertEqual(fun.status()["latest"]["status"], "expired")


if __name__ == "__main__":
    unittest.main()
