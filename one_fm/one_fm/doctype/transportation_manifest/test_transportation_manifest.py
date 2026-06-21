# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

class TestTransportationManifest(FrappeTestCase):
	def setUp(self):
		# Fetch existing active employees to avoid mandatory field validation errors
		employees = frappe.get_all("Employee", filters={"status": "Active"}, limit=3, fields=["name"])
		if len(employees) < 3:
			frappe.throw("At least 3 active Employee records are required in the database to run these tests.")
		
		self.employee1 = employees[0].name
		self.employee2 = employees[1].name
		self.reliever = employees[2].name

		# Set reliever flag on reliever employee
		frappe.db.set_value("Employee", self.reliever, "custom_is_rambo_reliever", 1)

	def tearDown(self):
		# Reset custom reliever flag
		frappe.db.set_value("Employee", self.reliever, "custom_is_rambo_reliever", 0)
		frappe.db.rollback()

	def test_qoa_fail_requires_reason(self):
		# Present + Fail QOA without reason must raise ValidationError
		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = frappe.get_all("Vehicle", limit=1)[0].name if frappe.get_all("Vehicle", limit=1) else None
		doc.schedule_date = today()
		doc.append("transportation_manifest_details", {
			"stop_name": "Test Stop",
			"employee": self.employee1,
			"attendance_status": "Present",
			"qoa_status": "Fail",
			"scheduled_time": "08:00:00"
		})
		self.assertRaises(frappe.ValidationError, doc.save)

		# Present + Fail QOA with reason must pass
		doc.transportation_manifest_details[0].qoa_reason = "Grooming"
		doc.save()

	def test_absent_clears_qoa(self):
		# Absent clears QOA status and reason
		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = frappe.get_all("Vehicle", limit=1)[0].name if frappe.get_all("Vehicle", limit=1) else None
		doc.schedule_date = today()
		doc.append("transportation_manifest_details", {
			"stop_name": "Test Stop",
			"employee": self.employee1,
			"attendance_status": "Absent",
			"qoa_status": "Fail",
			"qoa_reason": "Grooming",
			"scheduled_time": "08:00:00"
		})
		doc.save()
		self.assertEqual(doc.transportation_manifest_details[0].qoa_status, None)
		self.assertEqual(doc.transportation_manifest_details[0].qoa_reason, None)

	def test_reliever_replacement_validation(self):
		# Assign reliever employee
		doc1 = frappe.new_doc("Transportation Manifest")
		doc1.vehicle_no = frappe.get_all("Vehicle", limit=1)[0].name if frappe.get_all("Vehicle", limit=1) else None
		doc1.schedule_date = today()
		doc1.append("transportation_manifest_details", {
			"stop_name": "Test Stop 1A",
			"employee": self.employee1,
			"attendance_status": "Absent",
			"reliever_employee": self.reliever,
			"scheduled_time": "08:00:00"
		})
		doc1.append("transportation_manifest_details", {
			"stop_name": "Test Stop 1B",
			"employee": self.employee1,
			"attendance_status": "Present",
			"scheduled_time": "09:00:00"
		})
		doc1.save()
		# check requires_reliever flag was set to 1
		self.assertEqual(doc1.transportation_manifest_details[0].requires_reliever, 1)

		# Try to use the same reliever in another overlapping manifest vehicle on the same date
		doc2 = frappe.new_doc("Transportation Manifest")
		vehicles = frappe.get_all("Vehicle")
		doc2.vehicle_no = vehicles[1].name if len(vehicles) > 1 else vehicles[0].name
		doc2.schedule_date = today()
		doc2.append("transportation_manifest_details", {
			"stop_name": "Test Stop 2A",
			"employee": self.employee2,
			"attendance_status": "Absent",
			"reliever_employee": self.reliever,
			"scheduled_time": "08:30:00"  # overlapping time
		})
		doc2.append("transportation_manifest_details", {
			"stop_name": "Test Stop 2B",
			"employee": self.employee2,
			"attendance_status": "Present",
			"scheduled_time": "09:30:00"
		})
		self.assertRaises(frappe.ValidationError, doc2.save)

	def test_replaced_reliever_validation(self):
		# Flag reliever as replaced by making them absent/replaced on another manifest on the same date
		doc1 = frappe.new_doc("Transportation Manifest")
		doc1.vehicle_no = frappe.get_all("Vehicle", limit=1)[0].name if frappe.get_all("Vehicle", limit=1) else None
		doc1.schedule_date = today()
		doc1.append("transportation_manifest_details", {
			"stop_name": "Test Stop 1",
			"employee": self.reliever,
			"attendance_status": "Absent",
			"scheduled_time": "08:00:00"
		})
		doc1.save()

		# Try to select the same reliever for employee1 in another manifest
		doc2 = frappe.new_doc("Transportation Manifest")
		vehicles = frappe.get_all("Vehicle")
		doc2.vehicle_no = vehicles[1].name if len(vehicles) > 1 else vehicles[0].name
		doc2.schedule_date = today()
		doc2.append("transportation_manifest_details", {
			"stop_name": "Test Stop 2",
			"employee": self.employee1,
			"attendance_status": "Absent",
			"reliever_employee": self.reliever,
			"scheduled_time": "12:00:00"
		})
		self.assertRaises(frappe.ValidationError, doc2.save)
