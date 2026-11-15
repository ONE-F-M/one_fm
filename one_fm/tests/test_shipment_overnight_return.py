# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The bus home from a shift that crosses midnight carries last night's crew.

A 20:00-08:00 shift ends this morning, so its Return card is built from yesterday's
roster, while its Outward card (tonight) and every day shift follow today's.
"""

from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from one_fm.one_fm.doctype.transportation_shipment import shipment_generator as gen
from one_fm.tests.test_shipment_rider_reconcile import DEMAND, _roster

NIGHT = dict(DEMAND, group_token="OVERNIGHT-TEST|N", start_time=timedelta(hours=20), end_time=timedelta(hours=8))
DAY = dict(DEMAND, group_token="OVERNIGHT-TEST|D", start_time=timedelta(hours=8), end_time=timedelta(hours=20))


class TestOvernight(FrappeTestCase):
	def test_which_shifts_cross_midnight(self):
		self.assertTrue(gen._overnight(NIGHT))
		self.assertFalse(gen._overnight(DAY))
		# Midnight is a real end time, not a blank one.
		self.assertTrue(gen._overnight(dict(DEMAND, start_time=timedelta(hours=16), end_time=timedelta(0))))
		self.assertFalse(gen._overnight(DEMAND))


class TestTheBusHome(FrappeTestCase):
	def _targets(self, today_demands, yesterday_demands, skipped_today=None):
		"""Run the generator up to _reconcile and return the targets it was handed."""
		yesterday = add_days(today(), -1)

		def grouped(skipped=None, on_date=None):
			if skipped is not None:
				skipped.update(skipped_today or {})
			return {"day": yesterday if on_date == yesterday else "today"}

		def build(nested, skipped=None):
			return yesterday_demands if nested["day"] == yesterday else today_demands

		with patch.object(gen, "get_grouped_employees_by_accommodation", side_effect=grouped), \
				patch.object(gen, "build_demand_descriptors", side_effect=build), \
				patch.object(gen, "reliever_context", side_effect=lambda on_date=None: {"date": on_date}), \
				patch.object(gen, "_pins", return_value={}), \
				patch.object(gen, "_expire_single_day_rows", return_value=0), \
				patch.object(gen, "_report") as report, \
				patch.object(gen, "_reconcile") as reconcile, \
				patch.object(gen.frappe.db, "commit"):
			gen.generate_transportation_shipments()
		self.skipped = report.call_args.args[1]
		if not reconcile.called:
			return None
		return {
			(demand["group_token"], direction): ([e["id"] for e in roster], relievers)
			for demand, direction, roster, _pair, relievers in reconcile.call_args.args[0].values()
		}

	def test_tonight_goes_out_and_last_night_comes_home(self):
		targets = self._targets(
			[dict(NIGHT, employees=_roster("T1", "T2"))],
			[dict(NIGHT, employees=_roster("Y1", "Y2"))],
		)
		self.assertEqual(targets[("OVERNIGHT-TEST|N", "Outward")][0], ["T1", "T2"])
		self.assertEqual(targets[("OVERNIGHT-TEST|N", "Return")][0], ["Y1", "Y2"])
		# The reliever tag on the bus home is yesterday's.
		self.assertEqual(targets[("OVERNIGHT-TEST|N", "Return")][1], {"date": add_days(today(), -1)})
		self.assertEqual(targets[("OVERNIGHT-TEST|N", "Outward")][1], {"date": None})

	def test_day_shifts_still_follow_today(self):
		targets = self._targets(
			[dict(DAY, employees=_roster("T1"))],
			[dict(DAY, employees=_roster("Y1"))],
		)
		self.assertEqual(targets[("OVERNIGHT-TEST|D", "Outward")][0], ["T1"])
		self.assertEqual(targets[("OVERNIGHT-TEST|D", "Return")][0], ["T1"])

	def test_nobody_worked_last_night_means_no_bus_home(self):
		targets = self._targets([dict(NIGHT, employees=_roster("T1"))], [])
		self.assertNotIn(("OVERNIGHT-TEST|N", "Return"), targets)

	def test_off_today_but_riding_home_is_not_reported_as_unplaced(self):
		self._targets(
			[dict(DAY, employees=_roster("T1"))],
			[dict(NIGHT, employees=_roster("Y1"))],
			skipped_today={"Y1": "Not rostered to work today", "Z1": "Not rostered to work today"},
		)
		self.assertNotIn("Y1", self.skipped)
		self.assertIn("Z1", self.skipped)

	def test_no_demand_today_still_touches_no_card(self):
		# Last night's crew alone must not open the prune on an empty roster.
		self.assertIsNone(self._targets([], [dict(NIGHT, employees=_roster("Y1"))]))


class TestRidingHomeTwice(FrappeTestCase):
	def test_both_new_cards_are_kept(self):
		# E1 worked last night and works a day shift today: two Return cards, one rider.
		targets = {}
		for demand in (NIGHT, DAY):
			key, pair = gen._generation_key(demand, "Return")
			targets[key] = (demand, "Return", _roster("E1"), pair, {})

		with patch.object(gen, "_live_cards", return_value={}), \
				patch.object(gen, "_prune_stale", return_value=0) as prune:
			summary = {"created": 0, "updated": 0, "refreshed": 0, "deleted": 0, "errors": 0,
					   "repaired": 0, "overflowed": 0, "flagged": 0, "pruned": False}
			gen._reconcile(targets, set(targets), summary, {})

		created = frappe.get_all("Transportation Shipment", filters={"generation_key": ["in", list(targets)]}, pluck="name")
		self.assertEqual(len(created), 2)
		self.assertTrue(set(created) <= prune.call_args.kwargs["keep"])
