# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Marking a Local Transfer's Medical Insurance Done opens the employee's MOI.

Reported from testing on MI-2026-00343: submitting threw

    AttributeError: module 'one_fm.grd.doctype.residency.residency' has no
    attribute 'create_moi_for_transfer'. Did you mean: 'creat_moi_for_transfer'?

The call site was corrected when the module was renamed from moi_residency_jawazat
to residency; the function itself was not.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.medical_insurance.medical_insurance import MedicalInsurance
from one_fm.grd.doctype.residency.residency import create_moi_for_transfer


class TestTheCallResolves(FrappeTestCase):
	def test_the_name_the_caller_uses_exists(self):
		"""The whole bug: two spellings, and nothing joined them up."""
		from one_fm.grd.doctype.residency import residency

		self.assertTrue(callable(getattr(residency, "create_moi_for_transfer", None)))

	def test_the_caller_still_calls_it_by_that_name(self):
		"""Pinned on the source: correcting one side and not the other is what broke
		this in the first place."""
		import inspect

		source = inspect.getsource(MedicalInsurance.recall_create_moi_transfer)

		self.assertIn("residency.create_moi_for_transfer", source)

	def test_the_misspelling_is_gone_rather_than_aliased(self):
		from one_fm.grd.doctype.residency import residency

		self.assertFalse(hasattr(residency, "creat_moi_for_transfer"))


class TestItOpensTheMoi(FrappeTestCase):
	"""End to end from a real Local Transfer Work Permit, rolled back by the suite."""

	def setUp(self):
		self.work_permit = frappe.db.get_value(
			"Work Permit", {"work_permit_type": "Local Transfer", "employee": ["is", "set"]},
			"name", order_by="creation desc",
		)
		if not self.work_permit:
			self.skipTest("no Local Transfer Work Permit on this instance")
		self.employee = frappe.db.get_value("Work Permit", self.work_permit, "employee")

	def moi_names(self):
		return set(frappe.get_all("Residency", {"employee": self.employee}, pluck="name"))

	def test_a_transfer_moi_is_raised_for_the_permits_employee(self):
		before = self.moi_names()

		create_moi_for_transfer(self.work_permit)

		new = self.moi_names() - before
		self.assertEqual(len(new), 1)

		moi = frappe.get_doc("Residency", new.pop())
		self.assertEqual(moi.employee, self.employee)
		self.assertEqual(moi.category, "Transfer")
		self.assertEqual(moi.renewal_or_extend, "Transfer")

	def test_it_is_dated_today_rather_than_counted_back_from_an_expiry(self):
		"""A transfer has no expiry to count back from - MOI_CATEGORY_BY_ACTION gives
		"Transfer" no offset, so the application is dated the day it is raised."""
		before = self.moi_names()

		create_moi_for_transfer(self.work_permit)

		moi = frappe.get_doc("Residency", (self.moi_names() - before).pop())
		self.assertEqual(str(moi.date_of_application), frappe.utils.today())
