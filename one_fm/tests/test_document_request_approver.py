# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""Who approves a Document Request.

The approver comes from get_approver_user, so an employee holding the super
user role and reporting to nobody approves their own request.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.document_request import document_request as module
from one_fm.one_fm.doctype.document_request.document_request import get_requester_defaults
from one_fm.tests.test_document_request_inputs import DocumentRequestInputFixtures


def _super_user_without_a_manager():
	"""An employee holding the super user role and reporting to nobody, or None."""
	for name, user_id in frappe.get_all(
		"Employee",
		filters={"status": "Active", "reports_to": ["in", ["", None]], "user_id": ["is", "set"]},
		fields=["name", "user_id"],
		limit=200,
		as_list=True,
	):
		if frappe.db.get_value("Employee", {"user_id": user_id}, "name") != name:
			continue
		if module.get_approver_user(name) == user_id:
			return name, user_id
	return None


class TestApproverResolution(DocumentRequestInputFixtures, FrappeTestCase):
	def _request(self, **overrides):
		"""The sibling fixture's request, saved as the signed-in user."""
		doc = super()._request(**overrides)
		doc.flags.pop("ignore_permissions", None)
		return doc

	def test_a_line_manager_is_still_the_approver(self):
		manager_user = frappe.db.get_value(
			"Employee", frappe.db.get_value("Employee", self.requester, "reports_to"), "user_id"
		)
		if not manager_user:
			self.skipTest("the requester's line manager has no user")

		doc = self._request()
		doc.insert()

		self.assertEqual(doc.approver_user, manager_user)

	def test_a_super_user_with_no_line_manager_approves_their_own(self):
		"""The case that used to be refused outright."""
		who = _super_user_without_a_manager()
		if not who:
			self.skipTest("no active employee with the super user role and no line manager")
		requester, requester_user = who

		doc = self._request(requester=requester)
		doc.insert()

		self.assertEqual(doc.approver_user, requester_user)

	def test_an_unresolvable_approver_is_refused(self):
		with patch.object(module, "get_approver_user", return_value=None):
			doc = self._request()
			with self.assertRaises(frappe.ValidationError) as caught:
				doc.insert()

		self.assertIn("Could not resolve an approver", str(caught.exception))

	def test_an_approver_set_deliberately_is_left_alone(self):
		doc = self._request(approver_user=self.requester_user)
		doc.insert()

		self.assertEqual(doc.approver_user, self.requester_user)

	def test_the_form_offers_what_the_save_records(self):
		frappe.set_user(self.requester_user)
		try:
			shown = get_requester_defaults()
		finally:
			frappe.set_user("Administrator")

		doc = self._request()
		doc.insert()

		self.assertEqual(shown.get("approver_user"), doc.approver_user)
		self.assertNotIn("approver", shown)

	def test_the_doctype_no_longer_carries_an_approver_field(self):
		self.assertIsNone(frappe.get_meta("Document Request").get_field("approver"))
