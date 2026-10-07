# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today


class TestClientInterviewShortlist(FrappeTestCase):
	def test_project_required_without_prospective_client(self):
		shortlist = make_client_interview_shortlist(project=None)
		self.assertRaises(frappe.ValidationError, shortlist.validate)

	def test_prospective_client_required_when_flagged(self):
		shortlist = make_client_interview_shortlist(is_prospective_client=1, prospective_client=None)
		self.assertRaises(frappe.ValidationError, shortlist.validate)

	def test_prospective_client_clears_project(self):
		shortlist = make_client_interview_shortlist(
			project="Any Project", is_prospective_client=1, prospective_client="Any Opportunity"
		)
		shortlist.validate()
		self.assertIsNone(shortlist.project)

	def test_project_clears_prospective_client(self):
		shortlist = make_client_interview_shortlist(
			project="Any Project", prospective_client="Any Opportunity", customer_name="Any Customer"
		)
		shortlist.validate()
		self.assertIsNone(shortlist.prospective_client)
		self.assertIsNone(shortlist.customer_name)


class TestClientInterviewShortlistProcessaHandover(FrappeTestCase):
	def test_assignment_rules_are_removed(self):
		from one_fm.patches.v15_0.remove_client_interview_shortlist_assignment_rules import (
			ASSIGNMENT_RULES,
			execute,
		)

		execute()
		execute()
		for rule in ASSIGNMENT_RULES:
			self.assertFalse(frappe.db.exists("Assignment Rule", rule))
		self.assertFalse(
			frappe.db.exists(
				"Process Task",
				{
					"erp_document": "Client Interview Shortlist",
					"task": "Review and Approve Client Interview Shortlist",
					"is_active": 1,
				},
			)
		)

	def test_frappe_workflow_is_inactive(self):
		from frappe.model.workflow import get_workflow_name

		from one_fm.patches.v15_0.deactivate_client_interview_shortlist_workflow import execute

		execute()
		execute()
		self.assertFalse(get_workflow_name("Client Interview Shortlist"))


def make_client_interview_shortlist(**kwargs):
	return frappe.get_doc(
		{
			"doctype": "Client Interview Shortlist",
			"interview_date": add_days(today(), 1),
			"client_interview_employee": [],
			**kwargs,
		}
	)
