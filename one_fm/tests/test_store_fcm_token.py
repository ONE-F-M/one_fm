# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""v1.user.store_fcm_token saves or clears the caller's own push token only."""

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.api.v1 import user as user_api

OWNER = "owner@example.com"


class TestStoreFcmToken(FrappeTestCase):
	def _call(self, fcm_token, session_user=OWNER):
		employee = MagicMock(user_id=OWNER)
		employee.as_dict.return_value = {}
		get_value = frappe.db.get_value

		def fake_get_value(doctype, *args, **kwargs):
			return "EMP-TEST" if doctype == "Employee" else get_value(doctype, *args, **kwargs)

		frappe.local.response = frappe._dict()
		with patch.object(frappe.db, "get_value", side_effect=fake_get_value), \
			patch.object(frappe, "get_doc", return_value=employee), \
			patch.object(frappe.db, "commit"), \
			patch.object(frappe, "session", frappe._dict(user=session_user)):
			user_api.store_fcm_token(employee_id="TEST-1", fcm_token=fcm_token, device_os="web")
		return employee, frappe.local.response.get("http_status_code")

	def _stored_token(self, employee):
		return {c.args[0]: c.args[1] for c in employee.db_set.call_args_list}.get("fcm_token", "unset")

	def test_token_is_saved(self):
		employee, status = self._call("abc:123")
		self.assertEqual(status, 201)
		self.assertEqual(self._stored_token(employee), "abc:123")

	def test_empty_token_clears(self):
		for value in (None, "", "null"):
			employee, status = self._call(value)
			self.assertEqual(status, 201)
			self.assertIsNone(self._stored_token(employee), value)

	def test_other_users_token_is_refused(self):
		employee, status = self._call("abc:123", session_user="someone.else@example.com")
		self.assertEqual(status, 403)
		employee.db_set.assert_not_called()
