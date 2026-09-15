# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002024: the Overseas (Government) Action and the documents it opens."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.grd.doctype.preparation.preparation import (
	NEW_ACTION_DOCUMENTS,
	category_for_action,
	create_documents_for_row,
)
from one_fm.grd.doctype.residency.residency import (
	ACTIONS_HANDLED_ON_SUBMIT,
	MOI_CATEGORY_BY_ACTION,
)

ACTION = "Overseas (Government)"
SUB_DOCUMENTS = ("Work Permit", "Medical Insurance", "Residency", "PACI")


def _an_active_employee():
	"""An employee the GRD documents can be opened for.

	Work Permit refuses anyone inactive or with a relieving date, so the filter is not
	incidental. Taken from the site for the reason test_preparation_new_actions.py gives:
	Employee sits at MariaDB's row-size limit here.
	"""
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return frappe.get_doc("Employee", name)


class TestOverseasGovernmentAction(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()

	def test_the_action_is_an_option_on_the_preparation_row(self):
		options = frappe.get_meta("Preparation Record").get_field("renewal_or_extend").options
		self.assertIn(ACTION, options.split("\n"))

	def test_the_work_permit_type_is_an_option(self):
		options = frappe.get_meta("Work Permit").get_field("work_permit_type").options
		self.assertIn(ACTION, options.split("\n"))

	def test_a_fee_row_can_be_configured_for_the_action(self):
		# Without the option on the costing table there is no government rate to fetch.
		options = frappe.get_meta("GRD Renewal Extension Cost").get_field("renewal_or_extend").options
		self.assertIn(ACTION, options.split("\n"))

	def test_the_action_opens_the_same_four_documents_as_overseas(self):
		self.assertEqual(
			set(NEW_ACTION_DOCUMENTS[ACTION]),
			set(NEW_ACTION_DOCUMENTS["Overseas"]),
		)

	def test_the_work_permit_carries_the_government_type(self):
		self.assertEqual(NEW_ACTION_DOCUMENTS[ACTION]["work_permit"], ACTION)

	def test_residency_treats_it_as_a_first_residency(self):
		self.assertEqual(MOI_CATEGORY_BY_ACTION[ACTION], ("First Time", None))

	def test_preparation_owns_the_residency_rather_than_the_extend_branch(self):
		# The extend branch reads as "anything that is not a renewal is an extension", so
		# an Action missing from here gets a second Residency categorised as Extend.
		self.assertIn(ACTION, ACTIONS_HANDLED_ON_SUBMIT)

	def test_submitting_the_row_opens_all_four_documents(self):
		preparation = frappe.get_doc(
			{
				"doctype": "Preparation",
				"category": category_for_action(ACTION),
				"posting_date": nowdate(),
				"preparation_record": [{"employee": self.employee.name, "renewal_or_extend": ACTION}],
			}
		)
		preparation.flags.ignore_permissions = True
		preparation.insert()

		create_documents_for_row(preparation.preparation_record[0], preparation.name)

		for doctype in SUB_DOCUMENTS:
			self.assertTrue(
				frappe.db.exists(doctype, {"preparation": preparation.name, "employee": self.employee.name}),
				f"{doctype} was not opened for {ACTION}",
			)

		self.assertEqual(
			frappe.db.get_value(
				"Work Permit",
				{"preparation": preparation.name, "employee": self.employee.name},
				"work_permit_type",
			),
			ACTION,
		)
		self.assertEqual(
			frappe.db.get_value(
				"Medical Insurance",
				{"preparation": preparation.name, "employee": self.employee.name},
				"insurance_status",
			),
			"New",
		)
		self.assertEqual(
			frappe.db.get_value(
				"Residency",
				{"preparation": preparation.name, "employee": self.employee.name},
				"category",
			),
			"First Time",
		)
		self.assertEqual(
			frappe.db.get_value(
				"PACI",
				{"preparation": preparation.name, "employee": self.employee.name},
				"category",
			),
			"New Application",
		)
