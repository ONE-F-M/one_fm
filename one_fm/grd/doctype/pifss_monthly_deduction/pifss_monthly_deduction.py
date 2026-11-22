# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt
"""A month's PIFSS social security deduction.

The PIFSS Monthly Deduction Lifecycle process imports the CSV, moves it through its states and
makes the Additional Salaries. The PIFSS Monthly Deduction Creation process opens one each month.
"""

from frappe.model.document import Document

from one_fm.one_fm import processa_rules

RULES = "Calculate PIFSS Monthly Deduction Totals"


class PIFSSMonthlyDeduction(Document):
	def validate(self):
		processa_rules.run_rule(RULES, "recount", self)
