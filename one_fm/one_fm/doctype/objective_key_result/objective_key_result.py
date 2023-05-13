# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
import datetime
from datetime import timedelta
from frappe.utils import getdate
# bench execute --args "{'2021-01-01', '2021-03-31'}" one_fm.one_fm.doctype.objective_key_result.objective_key_result.get_objectives

class ObjectiveKeyResult(Document):
	def validate(self):
		self.validate_employee_okr()
		self.validate_company_goal()
		self.validate_okr_with_same_combination()

	def validate_employee_okr(self):
		if self.employee and self.okr_for != 'Quarterly':
			frappe.throw(_("Employee can create OKR for Quarterly only"))

	def validate_company_goal(self):
		if self.is_company_goal:
			self.employee = ""
			self.company_objective = False
			self.quarter = ""
			exists_okr = frappe.db.exists('Objective Key Result',
				{
					'name': ['!=', self.name],
					'is_company_goal': True
				}
			)
			if exists_okr:
				frappe.throw(_("A Company Goal '{0}' exists!".format(exists_okr)))

	def validate_okr_with_same_combination(self):
		if self.company_objective:
			self.employee = ""
			self.is_company_goal = False
		if self.employee:
			self.company_objective = False
			self.is_company_goal = False
		if self.okr_for == "Yearly":
			self.quarter = ""
		exists_okr = frappe.db.exists('Objective Key Result',
			{
				'name': ['!=', self.name],
				'year': self.year,
				'quarter': self.quarter,
				'company_objective': self.company_objective,
				'employee': self.employee
			}
		)
		if exists_okr:
			frappe.throw(_("An OKR '{0}' exists for the same combination!".format(exists_okr)))

@frappe.whitelist()
def get_objectives(start_date,end_date):
	query = """
		select
			*
		from
			`tabOKR Performance Profile Objective`
		where
			from_date >= %(start_date)s and to_date<=%(end_date)s
	"""
	return frappe.db.sql(query , {
		"start_date": start_date,
		"end_date": end_date
	} ,as_dict=True)
