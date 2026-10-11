# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

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
