# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class OverlapError(frappe.ValidationError): pass
class CareerHistory(Document):
	def validate(self):
		set_totals_in_career_history_company(self)
		self.validate_date_in_promotions_salary_hikes()

	def validate_date_in_promotions_salary_hikes(self):
		if self.promotions:
			for promotion in self.promotions:
				validate_overlap(self, promotion, 'Promotions')

		if self.salary_hikes:
			for salary_hike in self.salary_hikes:
				validate_overlap(self, salary_hike, 'Salary Hikes')

def validate_overlap(doc, child_doc, table_label):
	query = """
		select
			name
		from
			`tab{0}`
		where
			name != %(name)s
		"""
	query += get_doc_condition()

	if not child_doc.name:
		# hack! if name is null, it could cause problems with !=
		child_doc.name = "New "+child_doc.doctype

	overlap_doc = frappe.db.sql(query.format(child_doc.doctype),{
			"start_date": child_doc.start_date,
			"end_date": child_doc.end_date,
			"name": child_doc.name,
			"company_name": child_doc.company_name,
			"parent": doc.name
		}, as_dict = 1)
	if overlap_doc:
		frappe.throw(_("Row {0}: Start Date and End Date of Career History ({1}) is overlapping with {2}")
			.format(child_doc.idx, table_label, overlap_doc[0].name), OverlapError)

def get_doc_condition():
	return """
		and company_name = %(company_name)s and (start_date between %(start_date)s and %(end_date)s
		or end_date between %(start_date)s and %(end_date)s
		or (start_date < %(start_date)s and end_date > %(end_date)s))
	"""

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
						if promotion.recruiter_validation_score:
							recruiter_validation_score_promotion += promotion.recruiter_validation_score
			if doc.salary_hikes:
				for salary_hike in doc.salary_hikes:
					if company.company_name == salary_hike.company_name:
						total_salary_hike += 1
						if salary_hike.recruiter_validation_score:
							recruiter_validation_score_salary_change += salary_hike.recruiter_validation_score
			company.total_promotions = total_promotion
			company.recruiter_validation_score_promotion = recruiter_validation_score_promotion
			company.total_salary_changes = total_salary_hike
			company.recruiter_validation_score_salary_change = recruiter_validation_score_salary_change
