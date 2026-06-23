# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.one_fm.doctype.recruitment_plan.recruitment_plan import get_autocomplete_options

class TestRecruitmentPlan(FrappeTestCase):
	def test_date_validation_planning(self):
		# Start date after end date should raise ValidationError
		doc = frappe.get_doc({
			"doctype": "Recruitment Plan",
			"planning_recruitment_start_date": "2026-06-25",
			"planning_recruitment_end_date": "2026-06-24",
		})
		self.assertRaises(frappe.ValidationError, doc.validate)

		# End date equal/after start date should not raise ValidationError
		doc2 = frappe.get_doc({
			"doctype": "Recruitment Plan",
			"planning_recruitment_start_date": "2026-06-24",
			"planning_recruitment_end_date": "2026-06-25",
		})
		try:
			doc2.validate()
		except frappe.ValidationError:
			self.fail("doc.validate() raised ValidationError unexpectedly for valid planning dates")

	def test_date_validation_actual(self):
		# Start date after end date should raise ValidationError
		doc = frappe.get_doc({
			"doctype": "Recruitment Plan",
			"actual_recruitment_start_date": "2026-06-25",
			"actual_recruitment_end_date": "2026-06-24",
		})
		self.assertRaises(frappe.ValidationError, doc.validate)

		# End date equal/after start date should not raise ValidationError
		doc2 = frappe.get_doc({
			"doctype": "Recruitment Plan",
			"actual_recruitment_start_date": "2026-06-24",
			"actual_recruitment_end_date": "2026-06-25",
		})
		try:
			doc2.validate()
		except frappe.ValidationError:
			self.fail("doc.validate() raised ValidationError unexpectedly for valid actual dates")

	def test_get_autocomplete_options_permissions(self):
		# Save current user to restore later
		original_user = frappe.session.user

		# 1. When session user is "Guest", should raise PermissionError
		frappe.set_user("Guest")
		self.assertRaises(frappe.PermissionError, get_autocomplete_options)

		# 2. When session user is "Administrator", should successfully fetch options
		frappe.set_user("Administrator")
		try:
			res = get_autocomplete_options()
			self.assertIn("countries", res)
			self.assertIn("nationalities", res)
		except frappe.PermissionError:
			self.fail("get_autocomplete_options raised PermissionError for Administrator")
		finally:
			# Restore user
			frappe.set_user(original_user)
