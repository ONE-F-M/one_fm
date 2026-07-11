# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate


class TestAttendanceCheckAction(FrappeTestCase):
	def _new(self, **kwargs):
		doc = frappe.new_doc("Attendance Check Action")
		doc.update(kwargs)
		return doc

	def test_grace_period_computes_deadline(self):
		# Grace Period -> Deadline Date (Start Date + Grace Period)
		doc = self._new(start_date="2026-01-01", grace_period=14)
		doc.set_grace_and_deadline()
		self.assertEqual(getdate(doc.deadline_date), getdate("2026-01-15"))

	def test_deadline_computes_grace(self):
		# Deadline Date -> Grace Period (Deadline Date - Start Date)
		doc = self._new(start_date="2026-01-01", deadline_date="2026-01-15")
		doc.set_grace_and_deadline()
		self.assertEqual(doc.grace_period, 14)

	def test_self_purchase_defaults_grace_to_14(self):
		doc = self._new(start_date="2026-01-01", purchasing_method="Self Purchase")
		doc.set_grace_and_deadline()
		self.assertEqual(doc.grace_period, 14)
		self.assertEqual(getdate(doc.deadline_date), getdate("2026-01-15"))

	def test_company_loan_defaults_grace_to_14(self):
		doc = self._new(start_date="2026-01-01", purchasing_method="Company Loan")
		doc.set_grace_and_deadline()
		self.assertEqual(doc.grace_period, 14)

	def test_explicit_grace_is_not_overridden_by_method(self):
		# A grace period already entered must be respected, not reset to 14.
		doc = self._new(start_date="2026-01-01", purchasing_method="Self Purchase", grace_period=7)
		doc.set_grace_and_deadline()
		self.assertEqual(doc.grace_period, 7)
		self.assertEqual(getdate(doc.deadline_date), getdate("2026-01-08"))

	def test_negative_grace_period_rejected(self):
		# Deadline before Start Date implies a negative grace period.
		doc = self._new(start_date="2026-01-15", deadline_date="2026-01-01")
		with self.assertRaises(frappe.ValidationError):
			doc.set_grace_and_deadline()
