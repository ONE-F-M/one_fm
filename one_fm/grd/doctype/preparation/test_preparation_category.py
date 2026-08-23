# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002101: what a Preparation's Category names it, and which Actions it may carry."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.grd.doctype.preparation.preparation import (
	CATEGORIES,
	get_actions_for_category,
)

EXPECTED_PREFIXES = {
	"Onboarding": "PRE-ONB-",
	"Offboarding": "PRE-OFFB-",
	"Renewal": "PRE-REN-",
}


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestPreparationCategory(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()

	def _a_preparation(self, category, action=None):
		rows = [{"employee": self.employee, "renewal_or_extend": action}] if action else []
		preparation = frappe.get_doc({
			"doctype": "Preparation",
			"category": category,
			"posting_date": nowdate(),
			"preparation_record": rows,
		})
		preparation.flags.ignore_permissions = True
		preparation.insert()
		return preparation

	# ── naming ────────────────────────────────────────────────────────────────────

	def test_each_category_names_its_own_series(self):
		for category, prefix in EXPECTED_PREFIXES.items():
			with self.subTest(category=category):
				preparation = self._a_preparation(category)
				self.assertTrue(
					preparation.name.startswith(prefix),
					f"{preparation.name} is not in the {prefix} series",
				)

	def test_the_series_carries_the_year(self):
		preparation = self._a_preparation("Renewal")
		self.assertIn(nowdate()[:4], preparation.name)

	def test_a_category_is_required(self):
		with self.assertRaises(frappe.ValidationError):
			self._a_preparation(None)

	# ── the Actions each category may carry ───────────────────────────────────────

	def test_the_allowed_actions_are_the_field_s_own_options(self):
		"""WI-002101 spells two of them differently from the field. A value the field does
		not offer could never be selected, so the field's spelling wins."""
		options = frappe.get_meta("Preparation Record").get_field("renewal_or_extend").options.split("\n")
		for category, rules in CATEGORIES.items():
			for action in rules["actions"]:
				with self.subTest(category=category, action=action):
					self.assertIn(action, options)

	def test_every_action_belongs_to_exactly_one_category(self):
		seen = [action for rules in CATEGORIES.values() for action in rules["actions"]]
		self.assertEqual(len(seen), len(set(seen)))

	def test_the_form_is_told_what_a_category_may_carry(self):
		self.assertEqual(
			get_actions_for_category("Offboarding"),
			["Cancellation"],
		)
		self.assertEqual(
			get_actions_for_category("Onboarding"),
			["Overseas", "Overseas (Government)", "Local Transfer", "New Kuwaiti"],
		)
		self.assertEqual(get_actions_for_category("Nonsense"), [])

	def test_an_action_from_its_own_category_is_accepted(self):
		for category, rules in CATEGORIES.items():
			for action in rules["actions"]:
				with self.subTest(category=category, action=action):
					preparation = self._a_preparation(category, action)
					self.assertEqual(preparation.preparation_record[0].renewal_or_extend, action)

	def test_an_action_from_another_category_is_refused(self):
		"""The dropdown narrows; the rule is enforced here, because rows also arrive from the
		monthly schedule, from imports and from the API."""
		for category, action in (
			("Onboarding", "Cancellation"),
			("Offboarding", "Overseas"),
			("Renewal", "New Kuwaiti"),
		):
			with self.subTest(category=category, action=action):
				with self.assertRaises(frappe.ValidationError):
					self._a_preparation(category, action)

	def test_a_row_with_no_action_yet_is_left_alone(self):
		"""The Action is filled in by HR after the batch is built, so an empty row must save."""
		preparation = self._a_preparation("Renewal")
		preparation.append("preparation_record", {"employee": self.employee})
		preparation.save()

		self.assertFalse(preparation.preparation_record[0].renewal_or_extend)
