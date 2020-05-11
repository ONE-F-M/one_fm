# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document

class CareerHistory(Document):
	def validate(self):
		set_totals_in_career_history_company(self)

def set_totals_in_career_history_company(doc):
	if doc.career_history_company:
		for company in doc.career_history_company:
			total_promotion = 0
			total_salary_hike = 0
			recruiter_validation_score_promotion = 0
			recruiter_validation_score_salary_change = 0
			if doc.promotions:
				for promotion in doc.promotions:
					if company.company_name == promotion.company_name:
						total_promotion += 1
						recruiter_validation_score_promotion += promotion.recruiter_validation_score
			if doc.salary_hikes:
				for salary_hike in doc.salary_hikes:
					if company.company_name == salary_hike.company_name:
						total_salary_hike += 1
						recruiter_validation_score_salary_change += salary_hike.recruiter_validation_score
			company.total_promotions = total_promotion
			company.recruiter_validation_score_promotion = recruiter_validation_score_promotion
			company.total_salary_changes = total_salary_hike
			company.recruiter_validation_score_salary_change = recruiter_validation_score_salary_change
