# Copyright (c) 2026, oneaborance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RoutePlanAssignment(Document):
	def validate(self):
		# The board save judges the whole set it writes and flags each record it has
		# checked; anything else (the Desk form, Data Import) is judged here, one record
		# at a time, against the same plan-wide rules.
		if not self.flags.plan_checked:
			from one_fm.operations.doctype.route_plan.route_plan import check_plan_rows

			check_plan_rows(self.route_plan, [self])


def on_doctype_update():
	"""The board reads a plan one vehicle at a time and places a card once per plan.

	The unique key allows any number of rows with no route_plan, so it can be added on
	the sync that runs before the patch links the old child rows to their plan.
	"""
	frappe.db.add_index("Route Plan Assignment", ["route_plan", "vehicle"])
	frappe.db.add_unique("Route Plan Assignment", ["route_plan", "card_id"])
