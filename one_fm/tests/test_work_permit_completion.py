# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Completing a Local Transfer that was raised by hand, with no Transfer Paper behind it."""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestCompletingATransferWithoutATransferPaper(FrappeTestCase):
	def a_local_transfer(self):
		name = frappe.db.get_value(
			"Work Permit",
			{"work_permit_type": "Local Transfer"},
			"name",
			order_by="creation desc",
		)
		if not name:
			self.skipTest("no Local Transfer Work Permit on this instance")
		return frappe.get_doc("Work Permit", name)

	def test_it_does_not_look_for_transfer_paper_none(self):
		"""Reported from testing: Pending By Operator -> Done threw "Transfer Paper None
		not found". Only permits created from a Preparation record have one."""
		doc = self.a_local_transfer()
		doc.transfer_paper = None

		doc.update_wp_child_table_in_transfer_paper()

	def test_the_other_side_of_the_same_call_skips_too(self):
		doc = self.a_local_transfer()
		doc.transfer_paper = None

		doc.update_work_permit_details_in_tp()
