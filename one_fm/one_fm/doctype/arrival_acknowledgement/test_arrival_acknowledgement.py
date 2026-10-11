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
