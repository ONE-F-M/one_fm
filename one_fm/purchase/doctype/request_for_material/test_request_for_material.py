# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
from frappe.tests.utils import FrappeTestCase


class TestRequestforMaterial(FrappeTestCase):
	def make_rfm(self, **row):
		# Unsaved on purpose: only validate_refundable_margins() is under test.
		return frappe.get_doc({
			"doctype": "Request for Material",
			"items": [dict({"doctype": "Request for Material Item", "idx": 1}, **row)],
		})

	def test_refundable_without_margin_known_raises(self):
		rfm = self.make_rfm(is_refundable=1)
		self.assertRaises(frappe.ValidationError, rfm.validate_refundable_margins)

	def test_margin_known_yes_without_type_raises(self):
		rfm = self.make_rfm(is_refundable=1, margin_known="Yes", margin_rate_or_amount=5)
		self.assertRaises(frappe.ValidationError, rfm.validate_refundable_margins)

	def test_margin_known_yes_without_rate_raises(self):
		rfm = self.make_rfm(is_refundable=1, margin_known="Yes", margin_type="Percentage")
		self.assertRaises(frappe.ValidationError, rfm.validate_refundable_margins)

	def test_margin_known_yes_with_percentage_and_zero_passes(self):
		rfm = self.make_rfm(is_refundable=1, margin_known="Yes", margin_type="Percentage", margin_rate_or_amount=0)
		rfm.validate_refundable_margins()

	def test_margin_known_no_without_type_passes(self):
		rfm = self.make_rfm(is_refundable=1, margin_known="No")
		rfm.validate_refundable_margins()

	def test_non_refundable_row_is_ignored(self):
		rfm = self.make_rfm(is_refundable=0)
		rfm.validate_refundable_margins()

	def make_header(self, **header):
		return frappe.get_doc(dict({"doctype": "Request for Material", "items": []}, **header))

	def test_refundable_project_without_margin_known_raises(self):
		rfm = self.make_header(type="Project", is_refundable=1)
		self.assertRaises(frappe.ValidationError, rfm.validate_refundable_margins)

	def test_refundable_project_margin_known_yes_without_type_or_rate_raises(self):
		for header in ({"margin_rate_or_amount": 5}, {"margin_type": "Amount"}):
			rfm = self.make_header(type="Project", is_refundable=1, margin_known="Yes", **header)
			self.assertRaises(frappe.ValidationError, rfm.validate_refundable_margins)

	def test_refundable_project_with_margin_passes(self):
		self.make_header(
			type="Project", is_refundable=1, margin_known="Yes", margin_type="Amount", margin_rate_or_amount=0
		).validate_refundable_margins()
		self.make_header(type="Project", is_refundable=1, margin_known="No").validate_refundable_margins()

	def test_header_rule_applies_to_project_only(self):
		self.make_header(type="Stock", is_refundable=1).validate_refundable_margins()
		self.make_header(type="Project", is_refundable=0).validate_refundable_margins()
