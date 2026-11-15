import frappe


def execute():
	# The Penalty Issuance employee picker filters Shift Assignment by shift and date.
	frappe.db.add_index("Shift Assignment", ["shift", "start_date"], "shift_start_date")
