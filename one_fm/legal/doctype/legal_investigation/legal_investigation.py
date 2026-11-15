# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder import DocType


# The Initiate Legal Investigation process owns the lifecycle: the supervisor notice, the
# lead check, states, session check, outcome and the Penalty on Penalty Applied.
class LegalInvestigation(Document):
	pass


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def filter_employees(doctype, txt, searchfield, start, page_len, filters):
	frappe.has_permission("Legal Investigation", "read", throw=True)
	Employees = DocType("Legal Investigation Employees")
	return (
		frappe.qb.from_(Employees)
		.select(Employees.employee_id, Employees.employee_name)
		.where(
			(Employees.parent == filters.get("name"))
			& (Employees.parenttype == filters.get("doctype"))
			& (Employees.employee_id.like(f"%{txt}%") | Employees.employee_name.like(f"%{txt}%"))
		)
		.limit(page_len)
		.offset(start)
	).run()
