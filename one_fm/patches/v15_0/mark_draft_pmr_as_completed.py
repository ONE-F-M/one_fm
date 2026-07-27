# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import create_batch


def execute():
	"""Mark all Project Manpower Requests currently in Draft as Completed.

	In the PMR workflow the "Completed" state maps to docstatus 1 (submitted),
	while every "Draft" state maps to docstatus 0, so we update both fields.

	We write directly via frappe.db.set_value to bypass the controller's
	validate_completion() check (which requires linked employees) since this is
	an administrative bulk state correction.
	"""
	names = frappe.get_all(
		"Project Manpower Request",
		filters={"workflow_state": "Draft"},
		pluck="name",
	)

	if not names:
		return

	for batch in create_batch(names, 100):
		for name in batch:
			frappe.db.set_value(
				"Project Manpower Request",
				name,
				{
					"workflow_state": "Completed",
					"docstatus": 1,
				},
				update_modified=False,
			)
		frappe.db.commit()
