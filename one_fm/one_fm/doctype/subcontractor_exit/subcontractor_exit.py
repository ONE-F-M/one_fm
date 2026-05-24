# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SubcontractorExit(Document):
	def before_insert(self):
		"""Auto-populate requested_by with the current user."""
		self.requested_by = frappe.session.user

	def validate(self):
		self.validate_penalty_remarks()

	def validate_penalty_remarks(self):
		"""Enforce that Supervisor Remarks is filled when Penalize the Employee is checked."""
		for row in self.get("subcontract_exit_employee", []):
			if row.penalize_the_employee and not row.supervisor_remarks:
				frappe.throw(
					_("Row {0}: Supervisor Remarks is mandatory when Penalize the Employee is checked for Employee {1}.").format(
						row.idx, row.employee_id or row.employee_name or row.idx
					)
				)


@frappe.whitelist()
def fetch_subcontractor_employees(subcontractor_name: str, operations_site: str):
	"""Fetch employees matching the given Subcontractor and Operations Site.

	Filters Employee Master for:
	- status = Active
	- employment_type = Subcontractor
	- custom_subcontractor_name = <subcontractor_name>
	- site = <operations_site>

	Returns:
		list[dict]: List of dicts with employee (name) and employee_name.
	"""
	if not subcontractor_name or not operations_site:
		frappe.throw(_("Please select both Subcontractor Name and Operations Site before fetching employees."))

	employees = frappe.get_list(
		"Employee",
		filters={
			"status": "Active",
			"employment_type": "Subcontractor",
			"custom_subcontractor_name": subcontractor_name,
			"site": operations_site,
		},
		fields=["name", "employee_name"],
	)

	return employees
