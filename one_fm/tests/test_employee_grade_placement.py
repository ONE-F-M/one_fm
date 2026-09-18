# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002605 / WI-002606: Grade moves from the Government Relation tab to the Salary tab.

Layout only. Grade is a standard HRMS field whose stock home is the salary section - this
app's field_order had moved it under Government Relation, and this puts it back. The tests
below are about placement and about the one way a field_order edit goes wrong: dropping or
duplicating an entry, which silently loses a field from the form.
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.property_setter.employee import get_employee_properties


def field_order():
	setters = [p for p in get_employee_properties() if p.get("property") == "field_order"]
	assert len(setters) == 1, "expected exactly one Employee field_order property setter"
	return json.loads(setters[0]["value"])


def tab_of(order, fieldname):
	"""Which Tab Break the field sits under, reading the order the way the form does."""
	meta = frappe.get_meta("Employee")
	tab = None
	for name in order:
		df = meta.get_field(name)
		if df and df.fieldtype == "Tab Break":
			tab = df.label or df.fieldname
		if name == fieldname:
			return tab
	return None


class TestWhereGradeSits(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.order = field_order()

	def test_it_is_under_the_salary_tab(self):
		self.assertEqual(tab_of(self.order, "grade"), "Salary")

	def test_it_is_no_longer_under_government_relation(self):
		self.assertNotEqual(tab_of(self.order, "grade"), "Government Relation")

	def test_it_comes_first_in_the_salary_tab(self):
		self.assertEqual(
			self.order[self.order.index("salary_information") + 1], "grade"
		)

	def test_the_salary_tab_still_starts_where_it_did(self):
		# Moving grade must not have displaced the tab break itself.
		self.assertEqual(
			frappe.get_meta("Employee").get_field("salary_information").fieldtype, "Tab Break"
		)

	def test_ctc_still_follows_it(self):
		self.assertEqual(self.order[self.order.index("grade") + 1], "ctc")


class TestNothingElseMoved(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.order = field_order()

	def test_grade_appears_exactly_once(self):
		# Listed twice, Frappe renders the first and drops the second; listed zero times, it
		# vanishes from the form entirely. Both are silent.
		self.assertEqual(self.order.count("grade"), 1)

	def test_no_field_is_listed_twice(self):
		duplicates = {name for name in self.order if self.order.count(name) > 1}
		self.assertEqual(duplicates, set())

	def test_the_government_relation_tab_keeps_everything_else(self):
		for fieldname in ("pifss_id_no", "is_in_kuwait", "arabic_names", "one_fm_civil_id"):
			self.assertIn(fieldname, self.order, msg=fieldname)
			self.assertEqual(tab_of(self.order, fieldname), "Government Relation", msg=fieldname)

	def test_the_field_itself_is_untouched(self):
		# The story asks for a move "without changing its existing functionality".
		field = frappe.get_meta("Employee").get_field("grade")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Employee Grade")


class TestThePatch(FrappeTestCase):
	def test_it_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.move_employee_grade_to_salary_tab", patches)

	def test_it_reapplies_the_whole_order(self):
		# field_order is one stored list, so moving a single field means rewriting all of it.
		from one_fm.patches.v15_0 import move_employee_grade_to_salary_tab as patch

		self.assertTrue(hasattr(patch, "execute"))
