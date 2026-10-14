# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and Contributors
# See license.txt
"""Accommodation Checkin Checkout carries the Operations Shift of its employee."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from one_fm.patches.v15_0.backfill_checkin_operations_shift import execute as backfill
from one_fm.tests.utils import get_test_employee

DOCTYPE = "Accommodation Checkin Checkout"


def make_operations_shift():
	shift = frappe.get_doc({"doctype": "Operations Shift"})
	shift.flags.ignore_mandatory = True
	shift.flags.ignore_links = True
	shift.insert(ignore_permissions=True)
	return shift.name


def make_checkin(employee, type="IN"):
	doc = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"type": type,
			"employee": employee,
			"full_name": "Test Tenant",
			"tenant_category": "Paid Service",
			"checkin_checkout_date_time": now_datetime(),
		}
	)
	# No bed: the shift is what is under test, not the bed bookkeeping.
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	return doc


class TestAccommodationCheckinCheckout(FrappeTestCase):
	def setUp(self):
		self.employee = get_test_employee().name
		self.shift = make_operations_shift()
		self.other_shift = make_operations_shift()
		frappe.db.set_value("Employee", self.employee, "shift", self.shift)

	def test_the_field_follows_the_employees_shift(self):
		field = frappe.get_meta(DOCTYPE).get_field("operations_shift")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Operations Shift")
		self.assertEqual(field.fetch_from, "employee.shift")
		self.assertTrue(field.read_only)
		self.assertTrue(field.in_standard_filter)

	def test_inserting_an_in_record_sets_the_operations_shift(self):
		doc = make_checkin(self.employee)
		self.assertEqual(doc.operations_shift, self.shift)
		self.assertEqual(frappe.db.get_value(DOCTYPE, doc.name, "operations_shift"), self.shift)

	def test_saving_again_follows_the_new_shift(self):
		doc = make_checkin(self.employee)
		frappe.db.set_value("Employee", self.employee, "shift", self.other_shift)

		doc = frappe.get_doc(DOCTYPE, doc.name)
		doc.flags.ignore_mandatory = True
		doc.save(ignore_permissions=True)

		self.assertEqual(frappe.db.get_value(DOCTYPE, doc.name, "operations_shift"), self.other_shift)

	def test_the_patch_fills_only_the_open_in_rows(self):
		open_in = make_checkin(self.employee)
		closed_in = make_checkin(self.employee)
		out = make_checkin(self.employee, type="OUT")
		# Put the rows back as they were before the field existed.
		frappe.db.set_value(DOCTYPE, closed_in.name, "checked_out", 1)
		checkin = frappe.qb.DocType(DOCTYPE)
		frappe.qb.update(checkin).set(checkin.operations_shift, None).where(
			checkin.name.isin([open_in.name, closed_in.name, out.name])
		).run()

		backfill()

		value = lambda name: frappe.db.get_value(DOCTYPE, name, "operations_shift")
		self.assertEqual(value(open_in.name), self.shift)
		self.assertFalse(value(closed_in.name))
		self.assertFalse(value(out.name))
