# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002180: an amended Work Permit owes PAM no second invoice.

PAM charges nothing to revise a permit it is already holding, so there is no invoice to
attach - and every place that demanded one was a state the amended permit could not leave.
"""

import frappe
from frappe.tests.utils import FrappeTestCase


def _a_permit(amendment_no=0, **fields):
	"""An unsaved permit, which is all the invoice rule reads.

	Built rather than inserted because the rule under test is a pure function of two fields
	and inserting a real permit drags in an employee, a Preparation and the whole workflow.
	"""
	permit = frappe.new_doc("Work Permit")
	permit.update(fields)
	permit.amendment_no = amendment_no
	return permit


class TestInvoiceRequired(FrappeTestCase):
	def test_a_permit_that_was_never_amended_still_owes_an_invoice(self):
		"""AC1: at Amendment No 0 nothing changes."""
		self.assertTrue(_a_permit(amendment_no=0).invoice_required())

	def test_an_unpopulated_amendment_no_still_owes_an_invoice(self):
		self.assertTrue(_a_permit(amendment_no=None).invoice_required())

	def test_an_amended_permit_owes_none(self):
		"""AC2: and it stays exempt however many times it goes back."""
		for amendment_no in (1, 2, 3):
			with self.subTest(amendment_no=amendment_no):
				self.assertFalse(_a_permit(amendment_no=amendment_no).invoice_required())

	def test_the_exemption_is_not_just_the_moment_of_amending(self):
		"""is_being_amended is the transition; this outlives it.

		A permit amended last week is sitting in some later state with no unsaved change to
		read, so a rule keyed on the transition would demand an invoice again.
		"""
		permit = _a_permit(amendment_no=1, workflow_state="Pending By PAM")
		self.assertFalse(permit.is_being_amended())
		self.assertFalse(permit.invoice_required())


class TestTheInvoiceIsNotDemandedOfAnAmendedPermit(FrappeTestCase):
	"""Every site that demands the invoice has to honour the exemption - three of four is
	not an exemption, it is a permit stuck one state further along."""

	def test_no_state_check_demands_it(self):
		permit = _a_permit(amendment_no=1, workflow_state="Pending By PAM", name="WP-TEST")
		# The state check reads the stored state, and an unsaved permit has none, so it is
		# the invoice clause alone that is exercised here.
		permit.validate_workflow_state_fields()

	def test_completion_does_not_demand_it(self):
		permit = _a_permit(
			amendment_no=1,
			workflow_state="Completed",
			work_permit_type="Renewal Non Kuwaiti",
			new_work_permit_expiry_date=None,
		)
		with self.assertRaises(frappe.ValidationError) as raised:
			permit.on_submit()
		# Still asked for the expiry date, which an amendment does not exempt - but not for
		# the invoice.
		self.assertNotIn("Invoice", str(raised.exception))

	def test_completion_of_an_unamended_permit_still_demands_it(self):
		permit = _a_permit(
			amendment_no=0,
			workflow_state="Completed",
			work_permit_type="Renewal Non Kuwaiti",
		)
		with self.assertRaises(frappe.ValidationError) as raised:
			permit.on_submit()
		self.assertIn("Invoice", str(raised.exception))


class TestTheFieldIsHidden(FrappeTestCase):
	def test_upload_payment_invoice_is_hidden_once_amended(self):
		"""AC2: the field is not on the form of an amended permit."""
		field = frappe.get_meta("Work Permit").get_field("attach_invoice")
		self.assertEqual(field.depends_on, "eval:!doc.amendment_no")

	def test_it_is_still_in_the_payment_details_section(self):
		"""The section is hidden by workflow state, not by the amendment - unchanged."""
		meta = frappe.get_meta("Work Permit")
		order = meta.get("field_order") or [f.fieldname for f in meta.fields]
		self.assertLess(
			order.index("payment_details_section_section"), order.index("attach_invoice")
		)
