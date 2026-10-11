# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.arrival_acknowledgement.arrival_acknowledgement import acknowledge


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
		list_fields = [df.fieldname for df in frappe.get_meta("Arrival Acknowledgement").fields if df.in_list_view]

		self.assertIn("candidate_name", list_fields)
		self.assertNotIn("arrival_and_deployment", list_fields)

	def test_transportation_gets_designation_project_and_visa(self):
		values = {
			"Arrival and Deployment": "CCP-TEST",
			"Candidate Country Process": "HR-APP-TEST",
			"Job Applicant": ("Security Guard", "Test Project"),
			"Visa Stamping": "/private/files/test-visa.pdf",
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

		self.assertEqual((doc.designation, doc.project), ("Security Guard", "Test Project"))
		self.assertEqual(doc.visa_copy, "/private/files/test-visa.pdf")


class TestArrivalDepartmentEmail(FrappeTestCase):
	def test_department_mailbox_gets_a_copy_only_when_use_is_ticked(self):
		hiring_settings = frappe.get_single("Hiring Settings")
		hiring_settings.set("arrival_department_emails", [
			{"department": "Warehouse", "email": "test_warehouse_mailbox@example.com", "use": 1},
			{"department": "General Services", "email": "test_gs_mailbox@example.com", "use": 0},
		])
		hiring_settings.save()
		ard = frappe.get_doc({
			"doctype": "Arrival and Deployment",
			"candidate_name": "Test Mailbox Arrival",
			"arrival_date": frappe.utils.add_days(frappe.utils.today(), 3),
		}).insert()

		warehouse = _make_acknowledgement(ard.name, "Warehouse")
		general_services = _make_acknowledgement(ard.name, "General Services")

		self.assertEqual(_queued_recipients(warehouse.name), ["test_warehouse_mailbox@example.com"])
		self.assertEqual(_queued_recipients(general_services.name), [])


def _make_acknowledgement(arrival_and_deployment, department):
	return frappe.get_doc({
		"doctype": "Arrival Acknowledgement",
		"arrival_and_deployment": arrival_and_deployment,
		"department": department,
		"assigned_to": "Administrator",
	}).insert()


def _queued_recipients(acknowledgement):
	queues = frappe.get_all(
		"Email Queue",
		filters={"reference_doctype": "Arrival Acknowledgement", "reference_name": acknowledgement},
		pluck="name",
	)
	return frappe.get_all("Email Queue Recipient", filters={"parent": ["in", queues or [""]]}, pluck="recipient")
