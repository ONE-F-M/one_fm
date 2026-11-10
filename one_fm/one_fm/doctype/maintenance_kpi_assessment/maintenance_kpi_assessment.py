# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""A month's graded KPIs for one Maintenance KPI Master.

The Maintenance KPI Assessment Generation timer creates and grades one each month, through the
Create Monthly KPI Assessments script. The Maintenance KPI Assessment Lifecycle map submits it.
"""

from frappe.model.document import Document

from one_fm.one_fm.processa_rules import run_rule


class MaintenanceKPIAssessment(Document):
	def validate(self):
		# The penalty summary is derived, never entered: recalculated on every save, so it cannot be tampered with.
		run_rule("Calculate KPI Penalty", "calculate_penalty", self)
