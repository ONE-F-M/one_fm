# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.arrival_acknowledgement.arrival_acknowledgement import acknowledge


class TestArrivalAcknowledgement(FrappeTestCase):
	def test_acknowledge_sets_status_and_acknowledger(self):
		doc = frappe.new_doc("Arrival Acknowledgement")
		doc.arrival_and_deployment = "ARD-TEST-001"
		doc.department = "Warehouse"
		doc.assigned_to = "Administrator"
		doc.owner = "Administrator"
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.status, "Not Acknowledged")

		acknowledge(doc.name)
		doc.reload()

		self.assertEqual(doc.status, "Acknowledged")
		self.assertEqual(doc.acknowledged_by, "Administrator")
		self.assertIsNotNone(doc.acknowledged_on)

		doc.delete(ignore_permissions=True)
