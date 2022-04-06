# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and Contributors
# See license.txt
from __future__ import unicode_literals
import frappe
import unittest
from frappe.utils import flt, getdate
import pandas as pd
import frappe, erpnext
from frappe.utils.user import get_users_with_role
from frappe.permissions import has_permission
from frappe.model.document import Document
from frappe import _
class TestPIFSSMonthlyDeduction(unittest.TestCase):
	pass

def test():
	e = frappe.db.get_value("Employee", {"one_fm_nationality":"Kuwaiti"})
	ee = frappe.db.get_value("Employee", {"name":"HR-EMP-00002","relieving_date":['=','']},["one_fm_nationality"])
	print("n = ",e)
	print("n&r = ",ee)