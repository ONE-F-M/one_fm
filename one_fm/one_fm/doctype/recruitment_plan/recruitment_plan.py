# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

class RecruitmentPlan(Document):
	def validate(self):
		# Validate dates
		if self.planning_recruitment_start_date and self.planning_recruitment_end_date:
			if getdate(self.planning_recruitment_end_date) < getdate(self.planning_recruitment_start_date):
				frappe.throw(_("Planning Recruitment End Date cannot be before Planning Recruitment Start Date"))

		if self.actual_recruitment_start_date and self.actual_recruitment_end_date:
			if getdate(self.actual_recruitment_end_date) < getdate(self.actual_recruitment_start_date):
				frappe.throw(_("Actual Recruitment End Date cannot be before Actual Recruitment Start Date"))


@frappe.whitelist(methods=["GET"])
def get_autocomplete_options() -> dict:
	"""Fetch all Country and Nationality options for Recruitment Plan Autocomplete fields."""
	if not frappe.has_permission("Recruitment Plan", ptype="read"):
		frappe.throw(_("Not permitted to access recruitment plan details."), frappe.PermissionError)

	countries = frappe.get_list("Country", fields=["name"], order_by="name asc")
	nationalities = frappe.get_list("Nationality", fields=["name"], order_by="name asc")

	return {
		"countries": [c.name for c in countries if c.name],
		"nationalities": [n.name for n in nationalities if n.name]
	}
