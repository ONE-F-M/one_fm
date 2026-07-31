# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for Employee Response and Refusal Proof on the penalty (WI-001796).

The criteria name four responses and say a refusal carries proof - "Refuse (with valid
refusal_proof attached)" - so the proof is mandatory for that one answer and hidden for
the others.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

DOCTYPE = "Penalty And Investigation"

# The four answers the criteria use, in the words they use.
RESPONSES = ["Accept", "Refuse", "Not Return from Vacation", "Request Investigation"]

# The responses that, per the criteria, send the penalty straight to payroll and must
# not trigger an HR or Legal investigation.
STRAIGHT_TO_PAYROLL = {"Accept", "Refuse", "Not Return from Vacation"}

WHEN_REFUSED = 'eval:doc.employee_response == "Refuse"'


class TestEmployeeResponse(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.meta = frappe.get_meta(DOCTYPE)

	def test_the_field_exists_as_a_choice_of_answers(self):
		field = self.meta.get_field("employee_response")
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Select")

	def test_it_offers_exactly_the_responses_the_criteria_name(self):
		options = [o for o in (self.meta.get_field("employee_response").options or "").split("\n") if o]
		self.assertEqual(options, RESPONSES)

	def test_no_answer_is_the_default(self):
		# A penalty starts with no response recorded; the employee supplies one.
		self.assertFalse(self.meta.get_field("employee_response").default)
		self.assertFalse(self.meta.get_field("employee_response").reqd)

	def test_every_response_that_skips_investigation_is_an_offered_option(self):
		options = set(o for o in (self.meta.get_field("employee_response").options or "").split("\n") if o)
		self.assertEqual(STRAIGHT_TO_PAYROLL - options, set())
		# Request Investigation is the only one that routes to HR or Legal.
		self.assertEqual(options - STRAIGHT_TO_PAYROLL, {"Request Investigation"})


class TestRefusalProof(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.meta = frappe.get_meta(DOCTYPE)

	def test_it_is_an_attachment(self):
		field = self.meta.get_field("refusal_proof")
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Attach")

	def test_it_is_required_only_when_the_penalty_is_refused(self):
		field = self.meta.get_field("refusal_proof")
		self.assertEqual(field.mandatory_depends_on, WHEN_REFUSED)
		# Never unconditionally mandatory: the other three answers carry no proof.
		self.assertFalse(field.reqd)

	def test_it_is_shown_only_when_the_penalty_is_refused(self):
		self.assertEqual(self.meta.get_field("refusal_proof").depends_on, WHEN_REFUSED)

	def test_the_condition_reads_the_response_field(self):
		# Guards against the two drifting apart if either is renamed.
		self.assertIn("employee_response", WHEN_REFUSED)
		self.assertIsNotNone(self.meta.get_field("employee_response"))


class TestBothSitWithTheEmployeesRemark(FrappeTestCase):
	def test_they_are_ordered_before_the_rejection_remark(self):
		# The answer, then its proof, then the remark that explains it.
		order = frappe.get_meta(DOCTYPE).get("field_order") or [
			f.fieldname for f in frappe.get_meta(DOCTYPE).fields
		]
		for earlier, later in (
			("employee_response", "refusal_proof"),
			("refusal_proof", "employee_rejection_remarks"),
		):
			self.assertLess(order.index(earlier), order.index(later), msg=f"{earlier} < {later}")
