# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002744: the expiry job's cancellation is owned by the GRD Operator, not the scheduler.

The Visa Cancellation map takes the first user task's assignee from the document's owner, so
a cancellation the background job inserts is owned by Administrator and only Administrator
can act on it.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.visa_management.doctype.visa_cancellation_request import (
	visa_cancellation_request as module,
)
from one_fm.visa_management.doctype.visa_cancellation_request.visa_cancellation_request import (
	COPIED_FROM_VISA_REQUEST,
	insert_as_grd_operator,
)

OPERATOR = "j.mathew@one-fm.com"
SCHEDULER = "Administrator"


class _Doc:
	"""Just enough document to record who was logged in when it was inserted."""

	def __init__(self, grd_operator=None):
		self.grd_operator = grd_operator
		self.inserted_as = None

	def get(self, fieldname):
		return getattr(self, fieldname, None)

	def insert(self, ignore_permissions=False):
		self.inserted_as = module.frappe.session.user


class _InsertTestCase(FrappeTestCase):
	def _insert(self, grd_operator=None):
		"""Run the real function with the session user swapped for a recordable one."""
		session = frappe._dict(user=SCHEDULER)
		original_session = module.frappe.session
		original_set_user = module.frappe.set_user
		module.frappe.session = session
		module.frappe.set_user = lambda user: session.update({"user": user})
		try:
			doc = _Doc(grd_operator)
			insert_as_grd_operator(doc)
			return doc, session
		finally:
			module.frappe.session = original_session
			module.frappe.set_user = original_set_user


class TestWhoOwnsIt(_InsertTestCase):
	def test_it_is_inserted_as_the_grd_operator(self):
		"""insert() overwrites owner with the session user, and the process instance
		starts on insert and reads owner then - so being them while it is written is the
		only thing that puts their name on the task."""
		doc, _session = self._insert(OPERATOR)
		self.assertEqual(doc.inserted_as, OPERATOR)

	def test_the_session_user_is_put_back(self):
		_doc, session = self._insert(OPERATOR)
		self.assertEqual(session.user, SCHEDULER)

	def test_it_is_put_back_even_if_the_insert_fails(self):
		session = frappe._dict(user=SCHEDULER)
		original_session = module.frappe.session
		original_set_user = module.frappe.set_user
		module.frappe.session = session
		module.frappe.set_user = lambda user: session.update({"user": user})

		doc = _Doc(OPERATOR)
		doc.insert = lambda ignore_permissions=False: (_ for _ in ()).throw(ValueError("nope"))
		try:
			with self.assertRaises(ValueError):
				insert_as_grd_operator(doc)
			self.assertEqual(session.user, SCHEDULER)
		finally:
			module.frappe.session = original_session
			module.frappe.set_user = original_set_user

	def test_a_record_naming_no_operator_is_inserted_as_before(self):
		"""There is nobody to be, so nothing changes for it."""
		doc, session = self._insert(None)
		self.assertEqual(doc.inserted_as, SCHEDULER)
		self.assertEqual(session.user, SCHEDULER)


class TestItIsWiredIn(FrappeTestCase):
	def setUp(self):
		self.source = frappe.read_file(
			frappe.get_app_path(
				"one_fm",
				"visa_management",
				"doctype",
				"visa_cancellation_request",
				"visa_cancellation_request.py",
			)
		)

	def test_the_expiry_job_uses_it(self):
		job = self.source.split("def cancel_expired_visas", 1)[1].split("\ndef ", 1)[0]
		self.assertIn("insert_as_grd_operator(doc)", job)

	def test_the_button_path_is_untouched(self):
		"""A cancellation somebody raises by hand is already owned by whoever raised it."""
		button = self.source.split("def create_from_visa_request", 1)[1].split("\ndef ", 1)[0]
		self.assertNotIn("insert_as_grd_operator", button)

	def test_the_operator_is_carried_over_from_the_visa_request(self):
		"""Without it there is no operator on the cancellation to own it."""
		self.assertIn("grd_operator", COPIED_FROM_VISA_REQUEST)

	def test_the_cancellation_carries_the_field(self):
		self.assertEqual(
			frappe.get_meta("Visa Cancellation Request").get_field("grd_operator").options,
			"User",
		)
