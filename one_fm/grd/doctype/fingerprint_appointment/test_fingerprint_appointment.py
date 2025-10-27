# -*- coding: utf-8 -*-
# Copyright (c) 2021, ONE FM and Contributors
# See license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
import unittest
from frappe.utils import today, add_days, getdate
from frappe.test_runner import make_test_records

class TestFingerprintAppointment(unittest.TestCase):
    def setUp(self):
        make_test_records("User", [dict(email="test_pro_user@example.com", first_name="Test PRO User", roles=[{"role": "System Manager"}])])
        make_test_records("Employee", [dict(employee_name="Test Employee", user_id="test_pro_user@example.com")])

    def test_validate_done_with_future_date(self):
        # Create a Fingerprint Appointment with a future date
        appointment = frappe.new_doc("Fingerprint Appointment")
        appointment.employee = "Test Employee"
        appointment.pro_user = "test_pro_user@example.com"
        appointment.date_and_time_confirmation = add_days(today(), 5)
        appointment.workflow_state = "Pending Confirmation"

        # Expect a validation error to be thrown
        with self.assertRaises(frappe.ValidationError) as cm:
            appointment.save()

        self.assertTrue("You are not allowed to confirm fingerprint capturing before the appointment date." in str(cm.exception))

    def tearDown(self):
        frappe.db.rollback()
