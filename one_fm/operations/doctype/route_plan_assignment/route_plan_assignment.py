# Copyright (c) 2026, oneaborance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RoutePlanAssignment(Document):
	pass


def on_doctype_update():
	"""The board reads a plan one vehicle at a time and places a card once per plan.

	The unique key allows any number of rows with no route_plan, so it can be added on
	the sync that runs before the patch links the old child rows to their plan.
	"""
	frappe.db.add_index("Route Plan Assignment", ["route_plan", "vehicle"])
	frappe.db.add_unique("Route Plan Assignment", ["route_plan", "card_id"])
