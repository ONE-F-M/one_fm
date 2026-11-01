# Copyright (c) 2025, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from one_fm.patches.v15_0.remove_daily_employee_action_check import METHOD, execute


class TestRemoveDailyEmployeeActionCheck(FrappeTestCase):
	def test_patch_removes_the_scheduling_records(self):
		if not frappe.db.exists("Method", METHOD):
			frappe.get_doc(
				{"doctype": "Method", "method": METHOD, "document_type": "Employee Daily Action", "description": "probe"}
			).insert()
		if not frappe.db.exists("Scheduled Job Type", {"method": METHOD}):
			frappe.get_doc(
				{"doctype": "Scheduled Job Type", "method": METHOD, "frequency": "Cron", "cron_format": "0 4 * * *"}
			).insert()

		execute()

		self.assertFalse(frappe.db.exists("Scheduled Job Type", {"method": METHOD}))
		self.assertFalse(frappe.db.exists("Process Task", {"method": METHOD}))
		self.assertFalse(frappe.db.exists("Method", METHOD))


class TestEmployeeDailyActionController(FrappeTestCase):
	def test_saving_leaves_plans_and_reports_to_to_the_process_map(self):
		employee = frappe.get_all(
			"Employee", filters={"status": "Active", "user_id": ["is", "set"]}, fields=["name", "user_id", "company"], limit=1
		)[0]
		frappe.get_doc({"doctype": "ToDo", "allocated_to": employee.user_id, "date": today(), "description": "plan probe"}).insert()

		eda = frappe.get_doc({
			"doctype": "Employee Daily Action",
			"company_name": employee.company,
			"employee": employee.name,
			"date": today(),
			"number_of_read_emails": "0",
			"number_of_unread_emails": "0",
			"number_of_open_drive_comments": "0",
		}).insert()

		self.assertEqual(eda.todays_plan_and_accomplishments, [])


class TestTodaysPlanReferenceValidation(FrappeTestCase):
	"""HD-1879549: the `reference` column of Todays Plan and Accomplishments holds a
	document name copied from ToDo.reference_name, not a person's name.

	It was once a Data field with `options = "Name"`, which makes Frappe run
	`frappe.utils.validate_name()` over it (see BaseDocument._validate_data_fields).
	That validator only accepts letters, digits, underscore, apostrophe, hyphen and
	single spaces, so any ToDo pointing at a Contract, a Roster Employee Action or a
	Default Shift Checker blocked the whole Employee Daily Action from being saved
	with "<name> is not a valid Name".

	Do not give this field a `options` validator again.
	"""

	# real production document names that the "Name" validator rejected
	DOCUMENT_NAMES = [
		"Reem Hotel Management & Real Estate Service Co. W.L.L.-Reem Hotel - Alshuwaikh-",
		"WTE O&M Kuwait Sewage Treatment S.P.C.-WTE - 1820-",
		"2026-11-01|2026-11-30|HR-EMP-03965-1884253",
	]

	def test_reference_field_has_no_name_validator(self):
		reference = frappe.get_meta("Todays Plan and Accomplishments").get_field("reference")
		self.assertFalse(
			reference.options,
			"`reference` holds a document name — an `options` validator rejects legitimate names",
		)

	def test_document_names_are_rejected_by_the_name_validator(self):
		"""Pins why the fix matters: every name above fails `validate_name()`, so
		re-adding the validator brings the save blocker straight back."""
		for document_name in self.DOCUMENT_NAMES:
			with self.subTest(document_name=document_name):
				self.assertFalse(frappe.utils.validate_name(document_name))

	def test_document_names_pass_validation(self):
		for document_name in self.DOCUMENT_NAMES:
			with self.subTest(document_name=document_name):
				row = frappe.new_doc("Todays Plan and Accomplishments")
				row.reference_type = "Contracts"
				row.reference = document_name
				row._validate_data_fields()
