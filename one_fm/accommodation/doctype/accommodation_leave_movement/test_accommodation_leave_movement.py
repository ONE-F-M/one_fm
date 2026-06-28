# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today
from one_fm.accommodation.doctype.accommodation_leave_movement.accommodation_leave_movement import (
	get_latest_contiguous_leave,
	has_active_checkout_for_contiguous_chain,
	has_linked_checkin,
	make_checkin_from_checkout,
)


# Use a known active employee from the site to avoid custom mandatory field issues
TEST_EMPLOYEE = None


def get_test_employee():
	"""Fetch a real active employee to use in tests, avoiding custom mandatory field issues."""
	global TEST_EMPLOYEE
	if TEST_EMPLOYEE:
		return TEST_EMPLOYEE

	emp = frappe.db.get_value("Employee", {"status": "Active"}, "name")
	if not emp:
		frappe.throw("No active employee found in the system. Cannot run tests.")
	TEST_EMPLOYEE = emp
	return TEST_EMPLOYEE


def make_leave_application(employee, from_date, to_date, resumption_date, leave_type="Annual Leave", do_submit=True):
	"""Create a test leave application using db_insert to bypass complex validations."""
	la = frappe.get_doc({
		"doctype": "Leave Application",
		"employee": employee,
		"leave_type": leave_type,
		"from_date": from_date,
		"to_date": to_date,
		"resumption_date": resumption_date,
		"status": "Approved",
		"leave_approver": "Administrator",
		"posting_date": today(),
	})
	# Use db_insert to bypass custom overrides/validations (leave overlap, balance, etc.)
	la.docstatus = 1 if do_submit else 0
	la.db_insert()
	if la.docstatus == 1:
		la.run_method("on_update")
	return la.name


def make_alm(employee, movement_type, leave_application=None, checkin_reference=None, docstatus=0):
	"""Create a test Accommodation Leave Movement record using db_insert."""
	doc = frappe.get_doc({
		"doctype": "Accommodation Leave Movement",
		"type": movement_type,
		"employee": employee,
		"checkin_checkout_date_time": frappe.utils.now_datetime(),
		"full_name": "Test Employee",
		"leave_application": leave_application,
		"checkin_reference": checkin_reference,
	})
	doc.docstatus = docstatus
	doc.db_insert()
	return doc


class TestAccommodationLeaveMovement(FrappeTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.employee = get_test_employee()

	def tearDown(self):
		# Clean up all test ALMs and Leave Applications created by these tests.
		# Use direct SQL delete to avoid controller side-effects.
		frappe.db.delete("Accommodation Leave Movement", {
			"employee": self.employee,
			"full_name": "Test Employee",
		})
		frappe.db.delete("Leave Application", {
			"employee": self.employee,
			"leave_approver": "Administrator",
			"posting_date": today(),
		})
		frappe.db.commit()

	# ── Existing tests ────────────────────────────────────────────────

	def test_has_linked_checkin_for_draft_and_submitted_records(self):
		checkout = make_alm(self.employee, "OUT", docstatus=1)
		self.assertFalse(has_linked_checkin(checkout.name))

		draft_checkin = make_alm(self.employee, "IN", checkin_reference=checkout.name)
		self.assertTrue(has_linked_checkin(checkout.name))

		frappe.db.delete("Accommodation Leave Movement", {"name": draft_checkin.name})
		submitted_checkin = make_alm(self.employee, "IN", checkin_reference=checkout.name, docstatus=1)
		self.assertTrue(has_linked_checkin(checkout.name))

	def test_make_checkin_from_checkout_prevents_duplicate_linked_checkin(self):
		checkout = make_alm(self.employee, "OUT", docstatus=1)
		make_alm(self.employee, "IN", checkin_reference=checkout.name)

		with self.assertRaises(frappe.ValidationError):
			make_checkin_from_checkout(checkout.name)

	# ── Contiguous leave chain tests ──────────────────────────────────

	def test_get_latest_contiguous_leave_single(self):
		"""No contiguous leave exists → returns the original leave."""
		la = make_leave_application(
			self.employee,
			from_date="2027-08-05",
			to_date="2027-08-10",
			resumption_date="2027-08-11",
		)
		result = get_latest_contiguous_leave(self.employee, la)
		self.assertEqual(result, la)

	def test_get_latest_contiguous_leave_two_leaves(self):
		"""L1 → L2 contiguous chain → returns L2."""
		l1 = make_leave_application(
			self.employee,
			from_date="2027-08-05",
			to_date="2027-08-10",
			resumption_date="2027-08-11",
		)
		l2 = make_leave_application(
			self.employee,
			from_date="2027-08-11",
			to_date="2027-08-18",
			resumption_date="2027-08-19",
			leave_type="Leave Without Pay",
		)
		result = get_latest_contiguous_leave(self.employee, l1)
		self.assertEqual(result, l2)

	def test_get_latest_contiguous_leave_three_leaves(self):
		"""L1 → L2 → L3 chain → returns L3."""
		l1 = make_leave_application(
			self.employee,
			from_date="2027-08-05",
			to_date="2027-08-10",
			resumption_date="2027-08-11",
		)
		l2 = make_leave_application(
			self.employee,
			from_date="2027-08-11",
			to_date="2027-08-18",
			resumption_date="2027-08-19",
			leave_type="Leave Without Pay",
		)
		l3 = make_leave_application(
			self.employee,
			from_date="2027-08-19",
			to_date="2027-08-20",
			resumption_date="2027-08-21",
			leave_type="Leave Without Pay",
		)
		result = get_latest_contiguous_leave(self.employee, l1)
		self.assertEqual(result, l3)

	def test_get_latest_contiguous_leave_with_gap(self):
		"""L1 and L2 have a gap → returns L1 (no chain)."""
		l1 = make_leave_application(
			self.employee,
			from_date="2027-08-05",
			to_date="2027-08-10",
			resumption_date="2027-08-11",
		)
		# L2 starts on 2027-08-13 (gap of 2 days — not contiguous)
		l2 = make_leave_application(
			self.employee,
			from_date="2027-08-13",
			to_date="2027-08-18",
			resumption_date="2027-08-19",
			leave_type="Leave Without Pay",
		)
		result = get_latest_contiguous_leave(self.employee, l1)
		self.assertEqual(result, l1)

	def test_get_latest_contiguous_leave_cancelled(self):
		"""L2 is cancelled (docstatus=2) → chain is broken → returns L1."""
		l1 = make_leave_application(
			self.employee,
			from_date="2027-08-05",
			to_date="2027-08-10",
			resumption_date="2027-08-11",
		)
		l2 = make_leave_application(
			self.employee,
			from_date="2027-08-11",
			to_date="2027-08-18",
			resumption_date="2027-08-19",
			leave_type="Leave Without Pay",
		)
		# Cancel L2 directly via db_set to avoid controller side-effects
		frappe.db.set_value("Leave Application", l2, "docstatus", 2)

		result = get_latest_contiguous_leave(self.employee, l1)
		self.assertEqual(result, l1)

	def test_has_active_checkout_for_chain_with_active_out(self):
		"""OUT exists on L1, checking L2 → returns True."""
		l1 = make_leave_application(
			self.employee,
			from_date="2027-08-05",
			to_date="2027-08-10",
			resumption_date="2027-08-11",
		)
		l2 = make_leave_application(
			self.employee,
			from_date="2027-08-11",
			to_date="2027-08-18",
			resumption_date="2027-08-19",
			leave_type="Leave Without Pay",
		)
		# Create submitted OUT for L1
		make_alm(self.employee, "OUT", leave_application=l1, docstatus=1)

		# Check from L2's perspective — should find the active OUT on L1
		result = has_active_checkout_for_contiguous_chain(self.employee, l2)
		self.assertTrue(result)

	def test_has_active_checkout_for_chain_no_out(self):
		"""No OUT exists in chain → returns False (admin can create one)."""
		l1 = make_leave_application(
			self.employee,
			from_date="2027-08-05",
			to_date="2027-08-10",
			resumption_date="2027-08-11",
		)
		l2 = make_leave_application(
			self.employee,
			from_date="2027-08-11",
			to_date="2027-08-18",
			resumption_date="2027-08-19",
			leave_type="Leave Without Pay",
		)

		result = has_active_checkout_for_contiguous_chain(self.employee, l2)
		self.assertFalse(result)

	def test_has_active_checkout_for_chain_returned_out(self):
		"""OUT exists on L1 but already returned (checked_out=1) → returns False."""
		l1 = make_leave_application(
			self.employee,
			from_date="2027-08-05",
			to_date="2027-08-10",
			resumption_date="2027-08-11",
		)
		l2 = make_leave_application(
			self.employee,
			from_date="2027-08-11",
			to_date="2027-08-18",
			resumption_date="2027-08-19",
			leave_type="Leave Without Pay",
		)
		# Create OUT for L1 and mark as returned
		out_doc = make_alm(self.employee, "OUT", leave_application=l1, docstatus=1)
		frappe.db.set_value("Accommodation Leave Movement", out_doc.name, "checked_out", 1)

		result = has_active_checkout_for_contiguous_chain(self.employee, l2)
		self.assertFalse(result)

	def test_make_checkin_populates_latest_contiguous_leave(self):
		"""Check-In from L1 OUT should auto-populate the latest contiguous leave.

		Uses past dates so that today is after L1.to_date, triggering the
		normal (non-early) check-in path that resolves to L2.
		"""
		l1 = make_leave_application(
			self.employee,
			from_date="2025-06-05",
			to_date="2025-06-10",
			resumption_date="2025-06-11",
		)
		l2 = make_leave_application(
			self.employee,
			from_date="2025-06-11",
			to_date="2025-06-18",
			resumption_date="2025-06-19",
			leave_type="Leave Without Pay",
		)
		# Create submitted OUT for L1
		out_doc = make_alm(self.employee, "OUT", leave_application=l1, docstatus=1)

		# Create IN from the OUT record
		in_doc = make_checkin_from_checkout(out_doc.name)

		# Today is after L1.to_date — should resolve to L2
		self.assertEqual(in_doc.leave_application, l2)
		self.assertEqual(in_doc.checkin_reference, out_doc.name)
		self.assertEqual(in_doc.type, "IN")

	def test_make_checkin_three_leave_chain_populates_last(self):
		"""L1 → L2 → L3 chain. Check-In from L1 OUT should resolve to L3."""
		l1 = make_leave_application(
			self.employee,
			from_date="2025-06-05",
			to_date="2025-06-10",
			resumption_date="2025-06-11",
		)
		l2 = make_leave_application(
			self.employee,
			from_date="2025-06-11",
			to_date="2025-06-18",
			resumption_date="2025-06-19",
			leave_type="Leave Without Pay",
		)
		l3 = make_leave_application(
			self.employee,
			from_date="2025-06-19",
			to_date="2025-06-20",
			resumption_date="2025-06-21",
			leave_type="Leave Without Pay",
		)
		out_doc = make_alm(self.employee, "OUT", leave_application=l1, docstatus=1)
		in_doc = make_checkin_from_checkout(out_doc.name)

		# Should resolve to L3 (the last in the chain)
		self.assertEqual(in_doc.leave_application, l3)

	def test_make_checkin_cancelled_leave_breaks_chain(self):
		"""L2 cancelled → Check-In from L1 OUT should resolve to L1."""
		l1 = make_leave_application(
			self.employee,
			from_date="2025-06-05",
			to_date="2025-06-10",
			resumption_date="2025-06-11",
		)
		l2 = make_leave_application(
			self.employee,
			from_date="2025-06-11",
			to_date="2025-06-18",
			resumption_date="2025-06-19",
			leave_type="Leave Without Pay",
		)
		# Cancel L2
		frappe.db.set_value("Leave Application", l2, "docstatus", 2)

		out_doc = make_alm(self.employee, "OUT", leave_application=l1, docstatus=1)
		in_doc = make_checkin_from_checkout(out_doc.name)

		# Chain is broken — should stay on L1
		self.assertEqual(in_doc.leave_application, l1)

	def test_make_checkin_early_checkin_binds_to_original_leave(self):
		"""Early check-in during L1 period → IN should bind to L1, not L2.

		Uses future dates so that today is within L1's period, triggering
		the early check-in path.
		"""
		l1 = make_leave_application(
			self.employee,
			from_date="2027-08-05",
			to_date="2027-08-30",
			resumption_date="2027-08-31",
		)
		l2 = make_leave_application(
			self.employee,
			from_date="2027-08-31",
			to_date="2027-09-10",
			resumption_date="2027-09-11",
			leave_type="Leave Without Pay",
		)
		out_doc = make_alm(self.employee, "OUT", leave_application=l1, docstatus=1)
		in_doc = make_checkin_from_checkout(out_doc.name)

		# Today is before L1.to_date — early check-in — should stay on L1
		self.assertEqual(in_doc.leave_application, l1)
		# Should also have the early check-in warning
		self.assertTrue(hasattr(in_doc, "_early_checkin_warning"))
		self.assertIn("contiguous leave", in_doc._early_checkin_warning)

