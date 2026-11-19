# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""A plan ten times the size loads and saves one card in about the same time.

Timing asserts are flaky on shared runners, so this only runs when asked:

	ONE_FM_SCALE_TESTS=1 bench run-tests --app one_fm --module one_fm.tests.test_route_plan_scale

It needs a default Route Plan with real assignments (a restored production copy).
"""

import os
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.operations.doctype.route_plan import benchmark_route_plan as bench

LIMIT = 2.5


@unittest.skipUnless(os.environ.get("ONE_FM_SCALE_TESTS"), "set ONE_FM_SCALE_TESTS to run")
class TestTenTimesThePlan(FrappeTestCase):
	def test_load_and_a_one_card_save_stay_within_the_limit(self):
		plan = bench._default_plan()
		if not plan or not frappe.db.count("Route Plan Assignment", {"route_plan": plan}):
			self.skipTest("needs a default Route Plan with assignments")

		base = bench.run(plan, runs=3)
		big = bench.run(bench.make_synthetic_plan(rows=10 * base["rows"], source=plan), runs=3)

		self.assertLessEqual(big["load_seconds"], LIMIT * base["load_seconds"], (base, big))
		self.assertLessEqual(
			big["save_one_card_seconds"], LIMIT * base["save_one_card_seconds"], (base, big)
		)
