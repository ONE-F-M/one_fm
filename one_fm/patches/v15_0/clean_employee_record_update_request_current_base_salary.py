import re

import frappe

NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


def execute():
	"""current_base_salary moves from Data to Currency, which is `decimal not null default 0`.
	MariaDB refuses that ALTER while any row holds NULL, an empty string or non-numeric text."""
	doctype = "Employee Record Update Request"
	if not frappe.db.has_column(doctype, "current_base_salary"):
		return

	for row in frappe.get_all(doctype, fields=["name", "current_base_salary"]):
		value = str(row.current_base_salary or "").replace(",", "").strip()
		cleaned = value if NUMBER.match(value) else "0"
		if cleaned != row.current_base_salary:
			frappe.db.set_value(doctype, row.name, "current_base_salary", cleaned, update_modified=False)
