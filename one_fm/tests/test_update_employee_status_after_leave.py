# -*- coding: utf-8 -*-
# Copyright (c) 2025, ONE-F-M and Contributors
# See license.txt
from __future__ import unicode_literals
import frappe
import unittest
from frappe.utils import today, add_days, getdate
from one_fm.overrides.employee import NOT_RETURNED_FROM_LEAVE
from one_fm.overrides.leave_application import update_employee_status_after_leave


class TestLeaveResumption(unittest.TestCase):
    def setUp(self):
        frappe.flags.in_test = 1
        frappe.set_user("Administrator")
        frappe.flags.in_import = True
        frappe.flags.ignore_permissions = True

        self.cleanup_test_data()

        self.company = frappe.db.get_value("Company", {"is_group": 0}, "name") or "Test Company"

        if not frappe.db.exists("Department", "Test Department"):
            self.department = frappe.get_doc({
                "doctype": "Department",
                "department_name": "Test Department",
                "company": self.company
            }).insert(ignore_permissions=True)
        else:
            self.department = frappe.get_doc("Department", "Test Department")

        if not frappe.db.exists("Leave Type", "Annual Leave"):
            self.leave_type = frappe.get_doc({
                "doctype": "Leave Type",
                "leave_type_name": "Annual Leave",
                "is_annual_leave": 1,
                "allow_negative": 0,
                "include_holiday": 0
            }).insert(ignore_permissions=True)
        else:
            self.leave_type = frappe.get_doc("Leave Type", "Annual Leave")

        self.non_shift_employee = self.create_employee("Non Shift Employee", shift_working=0, accommodation=0)
        self.shift_no_accommodation_employee = self.create_employee("Shift No Accommodation", shift_working=1, accommodation=0)
        self.shift_with_accommodation_employee = self.create_employee("Shift With Accommodation", shift_working=1, accommodation=1)
        self.shift_with_accommodation_checkin_employee = self.create_employee("Shift With Checkin", shift_working=1, accommodation=1)

        frappe.db.commit()

    def cleanup_test_data(self):
        frappe.db.sql("DELETE FROM `tabLeave Allocation` WHERE employee LIKE 'HR-EMP-%'")
        frappe.db.sql("DELETE FROM `tabLeave Application` WHERE employee LIKE 'HR-EMP-%'")
        frappe.db.sql("DELETE FROM `tabAccommodation Checkin Checkout` WHERE employee LIKE 'HR-EMP-%'")
        frappe.db.sql("DELETE FROM `tabComment` WHERE reference_doctype = 'Employee' AND reference_name LIKE 'HR-EMP-%'")

        test_employees = frappe.get_all("Employee",
            filters={"employee_name": ["in", ["Non Shift Employee", "Shift No Accommodation", 
                                              "Shift With Accommodation", "Shift With Checkin"]]},
            pluck="name")
        for emp in test_employees:
            frappe.delete_doc("Employee", emp, force=1, ignore_permissions=True)

        if frappe.db.exists("Department", "Test Department"):
            frappe.delete_doc("Department", "Test Department", force=1, ignore_permissions=True)

        frappe.db.commit()

    def create_employee(self, name, shift_working=0, accommodation=0):
        employee = frappe.get_doc({
            "doctype": "Employee",
            "first_name": name,
            "employee_name": name,
            "one_fm_first_name_in_arabic": "اسم",
            "one_fm_last_name_in_arabic": "عائلة",
            "status": "Vacation",
            "date_of_birth": "1990-01-01",
            "date_of_joining": add_days(today(), -365),
            "gender": "Male",
            "company": self.company,
            "department": self.department.name,
            "annual_leave_balance": 30,
            "day_off_category": "Weekly",
            "number_of_days_off": 1,
            "one_fm_basic_salary": 100,
            "shift_working": shift_working,
            "one_fm_provide_accommodation_by_company": accommodation,
            "create_user_permission": 0
        }).insert(ignore_permissions=True)

        leave_allocation = frappe.get_doc({
            "doctype": "Leave Allocation",
            "employee": employee.name,
            "leave_type": self.leave_type.name,
            "from_date": add_days(today(), -365),
            "to_date": add_days(today(), 365),
            "new_leaves_allocated": 30
        }).insert(ignore_permissions=True)
        leave_allocation.submit()

        return employee

    def create_leave_application(self, employee, resumption_date):
        leave_app = frappe.get_doc({
            "doctype": "Leave Application",
            "employee": employee,
            "leave_type": self.leave_type.name,
            "from_date": add_days(resumption_date, -5),
            "to_date": add_days(resumption_date, -1),
            "resumption_date": resumption_date,
            "status": "Approved"
        }).insert(ignore_permissions=True)
        leave_app.submit()
        return leave_app

    def create_accommodation_checkin(self, employee, check_in_date):
        # Fetch employee to derive full_name
        employee_doc = frappe.get_doc("Employee", employee)

        # Ensure there is a Bed record to link
        bed_name = None
        existing_beds = frappe.get_all("Bed", fields=["name"], limit=1)
        if existing_beds:
            bed_name = existing_beds[0]["name"]
        else:
            bed_doc = frappe.get_doc({
                "doctype": "Bed",
                "bed_number": "Test Bed"
            }).insert(ignore_permissions=True)
            bed_name = bed_doc.name

        checkin = frappe.get_doc({
            "doctype": "Accommodation Checkin Checkout",
            "employee": employee,
            "full_name": employee_doc.employee_name,
            "type": "IN",
            "tenant_category": "Granted Service",
            "bed": bed_name,
            "checkin_checkout_date_time": check_in_date,
            "accommodation": "Test Accommodation"
        }).insert(ignore_permissions=True)
        return checkin
    def test_non_shift_worker_set_to_active(self):
        today_date = getdate(today())
        self.create_leave_application(self.non_shift_employee.name, today_date)

        frappe.db.commit()

        update_employee_status_after_leave()

        self.non_shift_employee.reload()
        self.assertEqual(self.non_shift_employee.status, "Active", 
                        "Non-shift worker should be set to Active")

        comment = frappe.get_all("Comment",
            filters={
                "reference_doctype": "Employee",
                "reference_name": self.non_shift_employee.name
            })
        self.assertTrue(comment, "Comment should be created for status change")

    def test_shift_worker_no_accommodation_not_returned(self):
        today_date = getdate(today())
        self.create_leave_application(self.shift_no_accommodation_employee.name, today_date)

        frappe.db.commit()

        update_employee_status_after_leave()

        self.shift_no_accommodation_employee.reload()
        self.assertEqual(self.shift_no_accommodation_employee.status, NOT_RETURNED_FROM_LEAVE,
                        "Shift worker without accommodation should not be marked as returned")

    def test_shift_worker_with_accommodation_no_checkin_not_returned(self):
        today_date = getdate(today())
        self.create_leave_application(self.shift_with_accommodation_employee.name, today_date)

        frappe.db.commit()

        update_employee_status_after_leave()

        self.shift_with_accommodation_employee.reload()
        self.assertEqual(self.shift_with_accommodation_employee.status, NOT_RETURNED_FROM_LEAVE,
                        "Shift worker with accommodation but no check-in should not be marked as returned")

    def test_shift_worker_with_accommodation_with_checkin_active(self):
        today_date = getdate(today())
        leave_app = self.create_leave_application(self.shift_with_accommodation_checkin_employee.name, today_date)

        self.create_accommodation_checkin(
            self.shift_with_accommodation_checkin_employee.name,
            add_days(leave_app.from_date, 1)
        )

        frappe.db.commit()

        update_employee_status_after_leave()

        self.shift_with_accommodation_checkin_employee.reload()
        self.assertEqual(self.shift_with_accommodation_checkin_employee.status, "Active",
                        "Shift worker with accommodation and check-in should be Active")

    def test_only_today_resumption_processed(self):
        tomorrow = add_days(getdate(today()), 1)
        self.create_leave_application(self.non_shift_employee.name, tomorrow)

        frappe.db.commit()

        update_employee_status_after_leave()

        self.non_shift_employee.reload()
        self.assertEqual(self.non_shift_employee.status, "Vacation",
                        "Employee with tomorrow's resumption date should not be processed")

    def test_no_change_if_already_correct_status(self):
        today_date = getdate(today())
        frappe.db.set_value("Employee", self.non_shift_employee.name, "status", "Active")
        self.create_leave_application(self.non_shift_employee.name, today_date)

        frappe.db.commit()

        comments_before = len(frappe.get_all("Comment",
            filters={
                "reference_doctype": "Employee",
                "reference_name": self.non_shift_employee.name
            }))

        update_employee_status_after_leave()

        comments_after = len(frappe.get_all("Comment",
            filters={
                "reference_doctype": "Employee",
                "reference_name": self.non_shift_employee.name
            }))

        self.assertEqual(comments_before, comments_after,
                        "No comment should be created if status unchanged")

    def test_only_approved_leave_processed(self):
        today_date = getdate(today())
        frappe.get_doc({
            "doctype": "Leave Application",
            "employee": self.non_shift_employee.name,
            "leave_type": self.leave_type.name,
            "from_date": add_days(today_date, -5),
            "to_date": add_days(today_date, -1),
            "resumption_date": today_date,
            "status": "Open"
        }).insert(ignore_permissions=True)

        frappe.db.commit()

        update_employee_status_after_leave()

        self.non_shift_employee.reload()
        self.assertEqual(self.non_shift_employee.status, "Vacation",
                        "Unapproved leave should not trigger status change")

    def tearDown(self):
        frappe.db.sql("DELETE FROM `tabLeave Allocation` WHERE employee IN %s",
                     ([self.non_shift_employee.name, self.shift_no_accommodation_employee.name,
                       self.shift_with_accommodation_employee.name, self.shift_with_accommodation_checkin_employee.name],))

        frappe.db.sql("DELETE FROM `tabLeave Application` WHERE employee IN %s",
                     ([self.non_shift_employee.name, self.shift_no_accommodation_employee.name,
                       self.shift_with_accommodation_employee.name, self.shift_with_accommodation_checkin_employee.name],))

        frappe.db.sql("DELETE FROM `tabAccommodation Checkin Checkout` WHERE employee IN %s",
                     ([self.non_shift_employee.name, self.shift_no_accommodation_employee.name,
                       self.shift_with_accommodation_employee.name, self.shift_with_accommodation_checkin_employee.name],))

        frappe.db.sql("DELETE FROM `tabComment` WHERE reference_doctype = 'Employee' AND reference_name IN %s",
                     ([self.non_shift_employee.name, self.shift_no_accommodation_employee.name,
                       self.shift_with_accommodation_employee.name, self.shift_with_accommodation_checkin_employee.name],))

        for emp in [self.non_shift_employee, self.shift_no_accommodation_employee,
                   self.shift_with_accommodation_employee, self.shift_with_accommodation_checkin_employee]:
            if frappe.db.exists("Employee", emp.name):
                frappe.delete_doc("Employee", emp.name, force=1)

        if frappe.db.exists("Department", "Test Department"):
            frappe.delete_doc("Department", "Test Department", force=1)

        frappe.db.commit()