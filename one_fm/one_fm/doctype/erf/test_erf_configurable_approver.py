# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002316: nothing in the code should decide who approves an ERF.

The approver was chosen by matching Reason for Request against the literal "UnPlanned".
That is the hard-coded logic the story is about: rename or remove that option - which the
business analyst has already done - and every ERF routes to the general approver while
"Unplanned ERF Approver" becomes unreachable, with nothing raised to say so.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.erf.erf import (
	DEFAULT_ERF_APPROVER_ROLE,
	get_erf_approver_role,
)

UNPLANNED_REASON = "UnPlanned"
UNPLANNED_ROLE = "Unplanned ERF Approver"


def _settings(rules=None, default=DEFAULT_ERF_APPROVER_ROLE):
	settings = frappe.get_doc("Hiring Settings")
	settings.default_erf_approver_role = default
	settings.set("erf_approver_rules", [])
	for reason, role in (rules or []):
		settings.append("erf_approver_rules", {"reason_for_request": reason, "approver_role": role})
	settings.flags.ignore_mandatory = True
	settings.flags.ignore_permissions = True
	settings.save()
	frappe.clear_cache(doctype="Hiring Settings")


class TestTheRoutingIsConfigured(FrappeTestCase):
	def tearDown(self):
		frappe.clear_cache(doctype="Hiring Settings")

	def test_a_configured_reason_goes_to_its_role(self):
		_settings(rules=[(UNPLANNED_REASON, UNPLANNED_ROLE)])

		self.assertEqual(get_erf_approver_role(UNPLANNED_REASON), UNPLANNED_ROLE)

	def test_an_unconfigured_reason_goes_to_the_default(self):
		_settings(rules=[(UNPLANNED_REASON, UNPLANNED_ROLE)])

		self.assertEqual(get_erf_approver_role("Staffing Plan"), DEFAULT_ERF_APPROVER_ROLE)

	def test_a_reason_nobody_has_configured_yet_still_routes(self):
		"""The point of the story: a reason added to the field needs no code change.

		"Other" and "Client ERF Hire" are the two the analyst has added; neither exists in
		any code, and both have to reach an approver.
		"""
		_settings(rules=[(UNPLANNED_REASON, UNPLANNED_ROLE)])

		for reason in ("Other", "Client ERF Hire"):
			with self.subTest(reason=reason):
				self.assertEqual(get_erf_approver_role(reason), DEFAULT_ERF_APPROVER_ROLE)

	def test_a_new_reason_can_be_given_its_own_role(self):
		"""And configuring one is all it takes."""
		_settings(rules=[("Client ERF Hire", UNPLANNED_ROLE)])

		self.assertEqual(get_erf_approver_role("Client ERF Hire"), UNPLANNED_ROLE)
		self.assertEqual(get_erf_approver_role(UNPLANNED_REASON), DEFAULT_ERF_APPROVER_ROLE)

	def test_an_empty_reason_routes_to_the_default(self):
		_settings(rules=[(UNPLANNED_REASON, UNPLANNED_ROLE)])

		for reason in (None, ""):
			with self.subTest(reason=reason):
				self.assertEqual(get_erf_approver_role(reason), DEFAULT_ERF_APPROVER_ROLE)

	def test_a_site_with_nothing_configured_still_routes(self):
		"""Hiring Settings is a Single that a site may never have opened."""
		_settings(rules=[], default=None)

		self.assertEqual(get_erf_approver_role("anything"), DEFAULT_ERF_APPROVER_ROLE)

	def test_a_rule_with_no_role_is_ignored_rather_than_obeyed(self):
		"""A half-filled row must not route an ERF to nobody."""
		settings = frappe.get_doc("Hiring Settings")
		settings.default_erf_approver_role = DEFAULT_ERF_APPROVER_ROLE
		settings.set("erf_approver_rules", [])
		row = settings.append("erf_approver_rules", {"reason_for_request": UNPLANNED_REASON})
		row.approver_role = None
		settings.flags.ignore_mandatory = True
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_cache(doctype="Hiring Settings")

		self.assertEqual(get_erf_approver_role(UNPLANNED_REASON), DEFAULT_ERF_APPROVER_ROLE)


class TestNothingInTheCodeNamesAnOption(FrappeTestCase):
	def tearDown(self):
		frappe.clear_cache(doctype="Hiring Settings")

	def test_unplanned_is_no_longer_special_in_the_code(self):
		"""The story's whole point, proved by behaviour rather than by reading the source.

		With no rule configured for it, "UnPlanned" has to route exactly where every other
		reason routes. If the old branch were still there it would return the specialised
		role regardless of what Hiring Settings says.
		"""
		_settings(rules=[])

		self.assertEqual(get_erf_approver_role(UNPLANNED_REASON), DEFAULT_ERF_APPROVER_ROLE)
		self.assertEqual(
			get_erf_approver_role(UNPLANNED_REASON), get_erf_approver_role("Staffing Plan")
		)

	def test_settings_can_send_unplanned_anywhere(self):
		"""And it is configuration, not code, that decides otherwise."""
		_settings(rules=[(UNPLANNED_REASON, DEFAULT_ERF_APPROVER_ROLE), ("New Project", UNPLANNED_ROLE)])

		self.assertEqual(get_erf_approver_role(UNPLANNED_REASON), DEFAULT_ERF_APPROVER_ROLE)
		self.assertEqual(get_erf_approver_role("New Project"), UNPLANNED_ROLE)

	def test_the_roles_it_falls_back_to_exist(self):
		self.assertTrue(frappe.db.exists("Role", DEFAULT_ERF_APPROVER_ROLE))


class TestTheDeploymentDateMayBeEmpty(FrappeTestCase):
	"""The analyst has made Expected Date of Deployment optional. getdate() reads an empty
	date as today, so the old check measured an ERF's own initiation date against today and
	could refuse to save it."""

	def _erf(self, **fields):
		doc = frappe.new_doc("ERF")
		doc.update(fields)
		return doc

	def test_no_date_is_not_checked(self):
		doc = self._erf(erf_initiation=frappe.utils.add_days(frappe.utils.today(), 5))
		doc.validate_date()

	def test_a_date_before_the_initiation_is_still_refused(self):
		doc = self._erf(
			erf_initiation=frappe.utils.add_days(frappe.utils.today(), 10),
			expected_date_of_deployment=frappe.utils.add_days(frappe.utils.today(), 5),
		)
		with self.assertRaises(frappe.ValidationError):
			doc.validate_date()

	def test_a_date_in_the_past_is_still_refused(self):
		doc = self._erf(
			erf_initiation=frappe.utils.add_days(frappe.utils.today(), -20),
			expected_date_of_deployment=frappe.utils.add_days(frappe.utils.today(), -1),
		)
		with self.assertRaises(frappe.ValidationError):
			doc.validate_date()

	def test_a_future_date_is_accepted(self):
		doc = self._erf(
			erf_initiation=frappe.utils.today(),
			expected_date_of_deployment=frappe.utils.add_days(frappe.utils.today(), 30),
		)
		doc.validate_date()
