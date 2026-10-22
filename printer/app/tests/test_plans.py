"""Local API guard rails; market data and trading actions are mocked."""
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plans


class PlanGuards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.object(plans, "OPS_DIR", self.tmp.name)
        p.start()
        self.addCleanup(p.stop)
        plans.PLANS.clear()

    def test_invalid_money(self):
        for value in ("abc", "nan", "inf", -1, 0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                plans.situation({"amount": value})

    def test_setup_and_create_enforce_same_loan_limits(self):
        cases = ({"amount": 50000}, {"age": 75}, {"account": "ira"}, {"account": "roth"})
        for fn in (plans.ops_setup, plans.ops_create):
            for changes in cases:
                q = dict(id="box", amount=150000, age=62, account="taxable")
                q.update(changes)
                with self.subTest(fn=fn.__name__, changes=changes), patch.object(plans, "_prices") as prices:
                    with self.assertRaises(ValueError):
                        fn(q)
                    prices.assert_not_called()

    def test_comparison_plan_cannot_create_tracker(self):
        with self.assertRaisesRegex(ValueError, "comparison only"):
            plans.ops_create(dict(id="6040", amount=50000))

    def remember(self, age=0, changed=False):
        st = {"tax": "IRA", "value": 100}
        Path(plans._path("test")).write_text(json.dumps(st))
        plans.PLANS["token"] = ("test", {"date": "2026-10-21"}, dt.datetime.now().timestamp() - age, plans._digest(st))
        if changed:
            Path(plans._path("test")).write_text(json.dumps({**st, "value": 200}))

    def test_stale_missing_and_expired_previews_do_not_apply(self):
        for kind in ("missing", "expired", "changed"):
            plans.PLANS.clear()
            if kind != "missing": self.remember(age=plans.PLAN_TTL + 1 if kind == "expired" else 0, changed=kind == "changed")
            with self.subTest(kind=kind), patch.object(plans.op, "apply") as apply:
                with self.assertRaisesRegex(ValueError, "Check again"):
                    plans.ops_commit({"token": "token"})
                apply.assert_not_called()

    def test_valid_preview_applies_once(self):
        self.remember()
        with patch.object(plans.op, "apply", side_effect=lambda st, *args: {**st, "value": 90}) as apply:
            self.assertEqual(plans.ops_commit({"token": "token"}), {"ok": True})
            with self.assertRaises(ValueError): plans.ops_commit({"token": "token"})
            apply.assert_called_once()
        self.assertEqual(json.loads(Path(plans._path("test")).read_text())["value"], 90)


if __name__ == "__main__":
    unittest.main()
