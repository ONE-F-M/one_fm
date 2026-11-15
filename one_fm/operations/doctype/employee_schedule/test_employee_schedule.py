
# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate, add_days

class TestEmployeeSchedule(FrappeTestCase):
	def setUp(self):
		# Look for an existing test employee or create one
		existing_emp = frappe.db.get_value("Employee", {"first_name": "Test", "last_name": "Employee"}, "name")
		if existing_emp:
			self.employee = existing_emp
		else:
			doc = frappe.get_doc({
				"doctype": "Employee",
				"first_name": "Test",
				"last_name": "Employee",
				"one_fm_first_name_in_arabic": "اختبار",
				"one_fm_last_name_in_arabic": "موظف",
				"department": "All Departments",
				"one_fm_basic_salary": 1000,
				"status": "Active",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": nowdate()
			})
			doc.insert(ignore_permissions=True)
			self.employee = doc.name

	def test_block_change_from_ojt_to_working_with_linked_ojt(self):
		# Create Employee Schedule with OJT
		# We use a dummy name for OJT to avoid needing to create the record,
		# we'll use frappe.db.set_value to put it there if link validation fails on insert.

		schedule = frappe.get_doc({
			"doctype": "Employee Schedule",
			"employee": self.employee,
			"date": add_days(nowdate(), 20),
			"employee_availability": "On-the-job Training",
			"roster_type": "Basic"
		})
		schedule.insert(ignore_permissions=True)

		# Set the OJT field manually to bypass link validation if it exists
		frappe.db.set_value("Employee Schedule", schedule.name, "on_the_job_training", "OJT-MOCK-001")
		schedule.reload()

		# Try to change to Working
		schedule.employee_availability = "Working"

		expected_msg = "Cannot change availability to 'Working' while an OJT record is linked. To change to 'Working', please delete this schedule and create a new one through Roster."

		schedule.flags.ignore_links = True
		with self.assertRaises(frappe.ValidationError) as cm:
			schedule.save()

		self.assertIn(expected_msg, str(cm.exception))

	def test_allow_change_to_working_if_no_ojt_linked(self):
		# Create Employee Schedule without OJT
		schedule = frappe.get_doc({
			"doctype": "Employee Schedule",
			"employee": self.employee,
			"date": add_days(nowdate(), 21),
			"employee_availability": "On-the-job Training",
			"roster_type": "Basic"
		})
		schedule.insert(ignore_permissions=True)

		# Try to change to Working
		schedule.employee_availability = "Working"
		schedule.save() # Should not throw
		self.assertEqual(schedule.employee_availability, "Working")

	def test_allow_change_from_other_to_working_even_with_ojt_linked(self):
		# Create Employee Schedule with OJT but from Day Off
		schedule = frappe.get_doc({
			"doctype": "Employee Schedule",
			"employee": self.employee,
			"date": add_days(nowdate(), 22),
			"employee_availability": "Day Off",
			"roster_type": "Basic"
		})
		schedule.insert(ignore_permissions=True)

		# Set the OJT field manually
		frappe.db.set_value("Employee Schedule", schedule.name, "on_the_job_training", "OJT-MOCK-001")
		schedule.reload()

		# Try to change to Working
		schedule.employee_availability = "Working"
		schedule.flags.ignore_links = True
		schedule.save() # Should not throw as per requirement 1
		self.assertEqual(schedule.employee_availability, "Working")

	def test_client_day_off_blocked_when_monthly_quota_not_met(self):
		# Create test employee for quotas
		frappe.db.set_value("Employee", self.employee, "day_off_category", "Monthly")
		frappe.db.set_value("Employee", self.employee, "number_of_days_off", 2)
		# Clear existing day off schedules
		frappe.db.delete("Employee Schedule", {"employee": self.employee, "employee_availability": "Day Off"})
		
		from one_fm.one_fm.page.roster.roster import check_client_day_off_eligibility
		eligible, msg = check_client_day_off_eligibility(self.employee, nowdate())
		self.assertFalse(eligible)
		self.assertIn("Total day off for this calendar month has not been utilized fully", msg)

	def test_client_day_off_allowed_when_monthly_quota_met(self):
		frappe.db.set_value("Employee", self.employee, "day_off_category", "Monthly")
		frappe.db.set_value("Employee", self.employee, "number_of_days_off", 1)
		
		# Create 1 Day Off schedule
		schedule = frappe.get_doc({
			"doctype": "Employee Schedule",
			"employee": self.employee,
			"date": nowdate(),
			"employee_availability": "Day Off",
			"roster_type": "Basic"
		})
		schedule.insert(ignore_permissions=True)
		
		from one_fm.one_fm.page.roster.roster import check_client_day_off_eligibility
		eligible, msg = check_client_day_off_eligibility(self.employee, nowdate())
		self.assertTrue(eligible)
		self.assertIsNone(msg)
		
		# cleanup
		schedule.delete()

	def test_client_day_off_blocked_when_weekly_quota_not_met(self):
		# Create test employee for quotas
		frappe.db.set_value("Employee", self.employee, "day_off_category", "Weekly")
		frappe.db.set_value("Employee", self.employee, "number_of_days_off", 1)
		# Clear existing day off schedules
		frappe.db.delete("Employee Schedule", {"employee": self.employee, "employee_availability": "Day Off"})
		
		from one_fm.one_fm.page.roster.roster import check_client_day_off_eligibility
		eligible, msg = check_client_day_off_eligibility(self.employee, nowdate())
		self.assertFalse(eligible)
		self.assertIn("Total day off for this week has not been utilized fully", msg)

	def test_client_day_off_allowed_when_weekly_quota_met(self):
		frappe.db.set_value("Employee", self.employee, "day_off_category", "Weekly")
		frappe.db.set_value("Employee", self.employee, "number_of_days_off", 1)
		
		# Create 1 Day Off schedule exactly today to guarantee it's in the current week
		schedule = frappe.get_doc({
			"doctype": "Employee Schedule",
			"employee": self.employee,
			"date": nowdate(),
			"employee_availability": "Day Off",
			"roster_type": "Basic"
		})
		schedule.insert(ignore_permissions=True)
		
		from one_fm.one_fm.page.roster.roster import check_client_day_off_eligibility
		eligible, msg = check_client_day_off_eligibility(self.employee, nowdate())
		self.assertTrue(eligible)
		self.assertIsNone(msg)
		
		# cleanup
		schedule.delete()


class TestEmployeeScheduleRelievingFields(FrappeTestCase):
	"""Meta-only checks for the Relieving Details section (no Employee fixture needed)."""

	def test_new_relieving_fields_exist(self):
		meta = frappe.get_meta("Employee Schedule")
		for fieldname in ("relieving_details_section", "is_day_off_reliever", "is_weekend_reliever",
				"is_annual_leave_reliever", "leave_application"):
			self.assertIsNotNone(meta.get_field(fieldname), fieldname)
		self.assertEqual(meta.get_field("relieving_details_section").label, "Relieving Details")
		self.assertEqual(meta.get_field("relieving_details_section").fieldtype, "Section Break")

	def test_reliever_checks_are_read_only(self):
		meta = frappe.get_meta("Employee Schedule")
		for fieldname in ("is_day_off_reliever", "is_weekend_reliever", "is_annual_leave_reliever"):
			field = meta.get_field(fieldname)
			self.assertEqual(field.fieldtype, "Check")
			self.assertEqual(field.read_only, 1, fieldname)
			self.assertEqual(str(field.default), "0", fieldname)

	def test_leave_application_links_to_leave_application(self):
		field = frappe.get_meta("Employee Schedule").get_field("leave_application")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Leave Application")

	def test_relieving_fields_sit_under_relieving_details_section(self):
		meta = frappe.get_meta("Employee Schedule")
		fieldnames = [f.fieldname for f in meta.fields]
		start = fieldnames.index("relieving_details_section")
		end = fieldnames.index("attendance_status_section")
		section = fieldnames[start + 1:end]
		for fieldname in ("is_relieving_schedule", "relieving_employee_schedule", "is_day_off_reliever",
				"is_weekend_reliever", "is_annual_leave_reliever", "leave_application"):
			self.assertIn(fieldname, section)
			self.assertEqual(fieldnames.count(fieldname), 1)

	def test_patch_drops_field_order_setter_so_section_is_populated(self):
		from frappe.custom.doctype.property_setter.property_setter import make_property_setter

		from one_fm.patches.v15_0 import drop_employee_schedule_field_order_property_setter as patch

		# The production setter: the old order, with the two relieving fields after end_datetime.
		moved = ("is_relieving_schedule", "relieving_employee_schedule")
		old_order = [f.fieldname for f in frappe.get_meta("Employee Schedule").fields if f.fieldname not in moved]
		at = old_order.index("end_datetime") + 1
		old_order[at:at] = list(moved)
		make_property_setter(
			"Employee Schedule", None, "field_order", frappe.as_json(old_order), "Data", for_doctype=True
		)
		frappe.clear_cache(doctype="Employee Schedule")
		with self.assertRaises(AssertionError):
			self.test_relieving_fields_sit_under_relieving_details_section()

		patch.execute()

		self.assertFalse(
			frappe.db.exists(
				"Property Setter",
				{"doc_type": "Employee Schedule", "doctype_or_field": "DocType", "property": "field_order"},
			)
		)
		self.test_relieving_fields_sit_under_relieving_details_section()
	def test_annual_leave_reliever_requires_leave_application(self):
		schedule = frappe.get_doc({
			"doctype": "Employee Schedule",
			"roster_type": "Basic",
			"employee_availability": "Working",
			"is_annual_leave_reliever": 1,
		})
		with self.assertRaisesRegex(frappe.ValidationError, "Leave Application is required"):
			schedule.validate()
