# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import os
from unittest.mock import patch

import frappe
from frappe.core.doctype.file.utils import find_file_by_url
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.arrival_acknowledgement.arrival_acknowledgement import (
	acknowledge,
	attach_file_copy,
)


class TestArrivalAcknowledgement(FrappeTestCase):
	def test_acknowledge_sets_status_and_acknowledger(self):
		ard = frappe.new_doc("Arrival and Deployment")
		ard.flags.ignore_mandatory = True
		ard.insert()

		doc = frappe.new_doc("Arrival Acknowledgement")
		doc.arrival_and_deployment = ard.name
		doc.department = "Warehouse"
		doc.assigned_to = "Administrator"
		doc.owner = "Administrator"
		doc.insert()

		self.assertEqual(doc.status, "Not Acknowledged")

		acknowledge(doc.name)
		doc.reload()

		self.assertEqual(doc.status, "Acknowledged")
		self.assertEqual(doc.acknowledged_by, "Administrator")
		self.assertIsNotNone(doc.acknowledged_on)

		doc.delete()
		ard.delete()


class TestArrivalAcknowledgementList(FrappeTestCase):
	def test_list_shows_candidate_name_instead_of_the_arrival_link(self):
		list_fields = [
			df.fieldname for df in frappe.get_meta("Arrival Acknowledgement").fields if df.in_list_view
		]

		self.assertIn("candidate_name", list_fields)
		self.assertNotIn("arrival_and_deployment", list_fields)

	def test_transportation_gets_designation_and_visa(self):
		values = {
			"Arrival and Deployment": ("CCP-TEST", "/private/files/test-evisa.pdf"),
			"Candidate Country Process": "HR-APP-TEST",
			"Job Applicant": "Security Guard",
		}
		doc = frappe.new_doc("Arrival Acknowledgement")
		doc.arrival_and_deployment = "ARD-TEST"
		doc.department = "Transportation"

		metas = {doctype: frappe.get_meta(doctype) for doctype in values}

		def get_value(doctype, filters, fieldname, **kwargs):
			for field in [fieldname] if isinstance(fieldname, str) else fieldname:
				self.assertTrue(metas[doctype].has_field(field), f"{doctype} has no field {field}")
			return values[doctype]

		with patch.object(frappe.db, "get_value", side_effect=get_value):
			doc.set_candidate_job_details()

		self.assertEqual(doc.designation, "Security Guard")
		self.assertEqual(doc.visa_copy, "/private/files/test-evisa.pdf")


class TestArrivalDepartmentEmail(FrappeTestCase):
	def setUp(self):
		hiring_settings = frappe.get_single("Hiring Settings")
		hiring_settings.set(
			"arrival_department_emails",
			[
				{"department": "Finance", "email": "test_finance_mailbox@example.com"},
				{"department": "General Services", "email": "test_gs_mailbox@example.com"},
				{"department": "Warehouse", "email": "test_procurement_mailbox@example.com"},
			],
		)
		hiring_settings.save()
		self.ard = frappe.get_doc(
			{
				"doctype": "Arrival and Deployment",
				"candidate_name": "Test Mailbox Arrival",
				"arrival_date": frappe.utils.add_days(frappe.utils.today(), 3),
				"email_general_services_mailbox": 0,
			}
		).insert()

	def test_department_mailbox_gets_a_copy_only_when_ticked_on_the_arrival(self):
		finance = _make_acknowledgement(self.ard.name, "Finance")
		general_services = _make_acknowledgement(self.ard.name, "General Services")

		self.assertEqual(_queued_recipients(finance.name), ["test_finance_mailbox@example.com"])
		self.assertEqual(_queued_recipients(general_services.name), [])

	def test_warehouse_waits_for_operations_then_gets_only_the_project(self):
		warehouse = _make_acknowledgement(self.ard.name, "Warehouse")
		self.assertEqual(_queued_recipients(warehouse.name), [])

		operations = frappe.new_doc("Arrival Acknowledgement")
		operations.arrival_and_deployment = self.ard.name
		operations.department = "Operations"
		operations.site_allocation = "Test Site"
		operations.project = "Test Project"
		operations.orientation_date = frappe.utils.today()
		operations.share_project_with_warehouse()

		warehouse.reload()
		self.assertEqual(warehouse.project, "Test Project")
		self.assertIsNone(warehouse.site_allocation)
		self.assertIsNone(warehouse.orientation_date)
		self.assertEqual(_queued_recipients(warehouse.name), ["test_procurement_mailbox@example.com"])

	def test_visa_copy_opens_for_transportation_without_visa_request_access(self):
		user = "test_ack_transportation@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Transport", "send_welcome_email": 0}
			).insert()
		frappe.get_doc("User", user).add_roles("Transportation Manager")
		visa = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "test-evisa.txt",
				"content": b"test evisa",
				"is_private": 1,
				"attached_to_doctype": "Arrival and Deployment",
				"attached_to_name": self.ard.name,
			}
		).insert()
		transportation = _make_acknowledgement(self.ard.name, "Transportation")

		frappe.set_user(user)
		self.assertIsNone(find_file_by_url(visa.file_url))
		frappe.set_user("Administrator")
		attach_file_copy(visa.file_url, "Arrival Acknowledgement", transportation.name, "visa_copy")
		frappe.set_user(user)
		self.assertIsNotNone(find_file_by_url(visa.file_url))
		frappe.set_user("Administrator")

	def test_visa_missing_on_disk_is_skipped_instead_of_failing(self):
		visa = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "test-missing-evisa.txt",
				"content": b"missing evisa",
				"is_private": 1,
				"attached_to_doctype": "Arrival and Deployment",
				"attached_to_name": self.ard.name,
			}
		).insert()
		os.remove(visa.get_full_path())
		transportation = _make_acknowledgement(self.ard.name, "Transportation")

		self.assertFalse(
			attach_file_copy(visa.file_url, "Arrival Acknowledgement", transportation.name, "visa_copy")
		)
		self.assertFalse(frappe.db.exists("File", {"attached_to_name": transportation.name}))


def _make_acknowledgement(arrival_and_deployment, department):
	return frappe.get_doc(
		{
			"doctype": "Arrival Acknowledgement",
			"arrival_and_deployment": arrival_and_deployment,
			"department": department,
			"assigned_to": "Administrator",
		}
	).insert()


def _queued_recipients(acknowledgement):
	queues = frappe.get_all(
		"Email Queue",
		filters={"reference_doctype": "Arrival Acknowledgement", "reference_name": acknowledgement},
		pluck="name",
	)
	return frappe.get_all(
		"Email Queue Recipient", filters={"parent": ["in", queues or [""]]}, pluck="recipient"
	)
