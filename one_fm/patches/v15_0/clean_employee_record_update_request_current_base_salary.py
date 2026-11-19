import re

import frappe

NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


def execute():
	"""current_base_salary moves from Data to Currency; MariaDB refuses the ALTER while any row holds non-numeric text."""
	doctype = "Employee Record Update Request"
	if not frappe.db.has_column(doctype, "current_base_salary"):
		return

	for row in frappe.get_all(doctype, fields=["name", "current_base_salary"]):
		if row.current_base_salary is None:
			continue
		value = row.current_base_salary.replace(",", "").strip()
		cleaned = value if NUMBER.match(value) else None
		if cleaned != row.current_base_salary:
			frappe.db.set_value(doctype, row.name, "current_base_salary", cleaned, update_modified=False)
