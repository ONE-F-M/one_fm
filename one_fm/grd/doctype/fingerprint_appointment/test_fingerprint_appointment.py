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

    def tearDown(self):
        frappe.db.rollback()
