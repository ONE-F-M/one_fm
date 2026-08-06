# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001824: what the New Kuwaiti and Overseas Actions generate on submit."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from one_fm.grd.doctype.preparation.preparation import (
	NEW_ACTION_DOCUMENTS,
	create_documents_for_row,
)
from one_fm.grd.doctype.residency.residency import create_moi_record

SUB_DOCUMENTS = ("Work Permit", "Medical Insurance", "Residency", "PACI")


def _an_active_employee():
	"""An employee the GRD documents can be opened for.

	Work Permit refuses anyone inactive or with a relieving date, so the filter is not
	incidental. Taken from the site rather than created: Employee sits at MariaDB's
	row-size limit here and a fixture would need a Company, a Fiscal Year and a
	Designation before it inserted.
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


class TestNewActionDocuments(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()

	def _preparation_with(self, action):
		"""A draft Preparation carrying one row with the given Action."""
		preparation = frappe.get_doc(
			{
				"doctype": "Preparation",
				"posting_date": nowdate(),
				"preparation_record": [
					{"employee": self.employee.name, "renewal_or_extend": action}
				],
			}
		).insert(ignore_permissions=True)

		return preparation

	def _opened_for(self, preparation_name):
		"""{doctype: [names]} of everything opened against this Preparation."""
		return {
			doctype: frappe.get_all(
				doctype, filters={"preparation": preparation_name}, pluck="name"
			)
			for doctype in SUB_DOCUMENTS
		}

	def test_the_action_field_offers_both_new_actions(self):
		options = frappe.get_meta("Preparation Record").get_field("renewal_or_extend").options
		for action in NEW_ACTION_DOCUMENTS:
			self.assertIn(action, options.split("\n"))

	def test_new_kuwaiti_opens_only_a_work_permit(self):
		preparation = self._preparation_with("New Kuwaiti")

		create_documents_for_row(preparation.preparation_record[0], preparation.name)

		opened = self._opened_for(preparation.name)
		self.assertEqual(len(opened["Work Permit"]), 1)
		# A Kuwaiti has no residency, no civil ID application and no medical insurance
		# process, so the other three must not be opened.
		for doctype in ("Medical Insurance", "Residency", "PACI"):
			self.assertEqual(opened[doctype], [], f"{doctype} should not be opened")

		work_permit = frappe.get_doc("Work Permit", opened["Work Permit"][0])
		self.assertEqual(work_permit.work_permit_type, "New Kuwaiti")

	def test_overseas_opens_all_four_with_their_categories(self):
		preparation = self._preparation_with("Overseas")

		create_documents_for_row(preparation.preparation_record[0], preparation.name)

		opened = self._opened_for(preparation.name)
		for doctype in SUB_DOCUMENTS:
			self.assertEqual(len(opened[doctype]), 1, f"{doctype} was not opened exactly once")

		# The government classification each document is opened under (WI-001881).
		self.assertEqual(
			frappe.db.get_value("Work Permit", opened["Work Permit"][0], "work_permit_type"),
			"Overseas",
		)
		self.assertEqual(
			frappe.db.get_value(
				"Medical Insurance", opened["Medical Insurance"][0], "insurance_status"
			),
			"New",
		)
		self.assertEqual(
			frappe.db.get_value("Residency", opened["Residency"][0], "category"),
			"First Time",
		)
		self.assertEqual(
			frappe.db.get_value("PACI", opened["PACI"][0], "category"),
			"New Application",
		)

	def test_a_first_application_is_dated_the_day_it_is_opened(self):
		"""No residency to count back from, unlike a renewal or an extension."""
		preparation = self._preparation_with("Overseas")

		create_documents_for_row(preparation.preparation_record[0], preparation.name)

		opened = self._opened_for(preparation.name)
		for doctype in ("Work Permit", "Residency", "PACI"):
			self.assertEqual(
				str(frappe.db.get_value(doctype, opened[doctype][0], "date_of_application")),
				nowdate(),
				f"{doctype} is not dated today",
			)

	def test_the_extend_and_renewal_categories_still_date_off_the_residency(self):
		"""Guards the mapping the Overseas category was added to.

		The three existing categories used to be an if/if/if chain ending in "anything
		that is not a renewal or a transfer is an extension"; they now come from a dict,
		and this pins that the dates they are applied for did not move.
		"""
		employee = frappe.get_doc(
			"Employee",
			frappe.db.get_value(
				"Employee",
				{"status": "Active", "relieving_date": ["is", "not set"], "residency_expiry_date": ["is", "set"]},
				"name",
			),
		)
		expiry = getdate(employee.residency_expiry_date)

		for action, category, expected_date in (
			("Renewal (Non-Kuwaiti)", "Renewal", add_days(expiry, -14)),
			("Extend 2 months", "Extend", add_days(expiry, -7)),
			("Transfer", "Transfer", getdate(nowdate())),
		):
			with self.subTest(action=action):
				create_moi_record(employee, action)
				residency = frappe.get_last_doc("Residency", filters={"employee": employee.name})
				self.assertEqual(residency.category, category)
				self.assertEqual(getdate(residency.date_of_application), getdate(expected_date))

	def test_the_documents_carry_their_preparation(self):
		"""The link WI-001973 put on the form has to be filled in by this path too."""
		preparation = self._preparation_with("Overseas")

		create_documents_for_row(preparation.preparation_record[0], preparation.name)

		opened = self._opened_for(preparation.name)
		for doctype in SUB_DOCUMENTS:
			self.assertEqual(
				frappe.db.get_value(doctype, opened[doctype][0], "preparation"),
				preparation.name,
			)
