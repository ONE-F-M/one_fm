# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The Visa Extension Expiry Date on Residency."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from one_fm.grd.doctype.preparation.preparation import RESIDENCY_ONLY_ACTIONS

FIELD_LABEL = "Visa Extension Expiry Date"


def _an_active_employee():
	"""An employee a Residency can be opened for, taken from the site rather than created
	(same reason as test_residency_damj.py)."""
	name = frappe.db.get_value("Employee", {"status": "Active"}, "name", order_by="creation asc")
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestResidencyVisaExtensionExpiryDate(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()

	def _residency(self, category, action, **kwargs):
		residency = frappe.get_doc(
			{
				"doctype": "Residency",
				"employee": self.employee,
				"category": category,
				"renewal_or_extend": action,
				"date_of_application": today(),
				"invoice_attachment": "/files/invoice.pdf",
				**kwargs,
			}
		)
		residency.flags.ignore_permissions = True
		return residency

	def test_meta_has_the_field_right_after_new_residency_expiry_date(self):
		meta = frappe.get_meta("Residency")
		field = meta.get_field("visa_extension_expiry_date")

		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Date")
		self.assertEqual(field.label, FIELD_LABEL)
		self.assertEqual(field.depends_on, "eval:doc.category == 'Extend'")
		self.assertFalse(field.reqd)
		self.assertFalse(field.read_only)
		self.assertFalse(field.mandatory_depends_on)

		order = [df.fieldname for df in meta.fields]
		self.assertEqual(
			order.index("visa_extension_expiry_date"),
			order.index("new_residency_expiry_date") + 1,
		)

	def test_extension_cannot_be_completed_without_the_date(self):
		for action in RESIDENCY_ONLY_ACTIONS:
			residency = self._residency("Extend", action)
			residency.insert()
			with self.assertRaises(frappe.ValidationError):
				residency.submit()

	def test_draft_extension_saves_without_the_date(self):
		# Not mandatory at save time: the operator fills it at the end of the process.
		residency = self._residency("Extend", RESIDENCY_ONLY_ACTIONS[0])
		residency.insert()
		self.assertFalse(residency.visa_extension_expiry_date)

	def test_extension_completes_with_the_date_alone(self):
		# The extension date replaces the Updated Residency Expiry Date for these actions.
		residency_expiry_date = frappe.db.get_value("Employee", self.employee, "residency_expiry_date")
		for action in RESIDENCY_ONLY_ACTIONS:
			residency = self._residency(
				"Extend", action, visa_extension_expiry_date=add_days(today(), 30)
			)
			residency.insert()
			residency.submit()
			self.assertEqual(residency.docstatus, 1)
			self.assertFalse(residency.new_residency_expiry_date)
		self.assertEqual(
			frappe.db.get_value("Employee", self.employee, "residency_expiry_date"),
			residency_expiry_date,
		)

	def test_renewal_expat_does_not_ask_for_the_date(self):
		residency = self._residency(
			"Renewal", "Renewal Expat", new_residency_expiry_date=add_days(today(), 365)
		)
		residency.validate_mandatory_fields_on_submit()

	def test_renewal_expat_still_needs_the_updated_residency_expiry_date(self):
		residency = self._residency("Renewal", "Renewal Expat")
		with self.assertRaises(frappe.ValidationError):
			residency.validate_mandatory_fields_on_submit()

	def test_cancellation_does_not_ask_for_the_date(self):
		# Cancellation rows open category Extend, so the check must key on the action.
		residency = self._residency(
			"Extend", "Cancellation", new_residency_expiry_date=add_days(today(), 365)
		)
		residency.validate_mandatory_fields_on_submit()
