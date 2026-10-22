from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.api.mobile import authentication as mobile_auth
from one_fm.api.v1 import authentication as v1_auth
from one_fm.api.v2 import authentication as v2_auth
from one_fm.processor import sendemail


class TestEmailOtpDelivery(FrappeTestCase):
	def test_otp_email_bypasses_the_company_email_filter(self):
		for module in (v1_auth, v2_auth, mobile_auth):
			with self.subTest(module=module.__name__), patch.object(
				module.frappe.db, "get_value", return_value="worker@example.com"
			), patch.object(module, "enqueue") as enqueue:
				self.assertTrue(module.send_token_via_email("worker@one-fm.com", 123456, "BASE32SECRET3232", "ONE FM"))

			kwargs = enqueue.call_args.kwargs
			self.assertIs(kwargs["method"], sendemail)
			self.assertEqual(kwargs["recipients"], "worker@example.com")
			self.assertIs(kwargs["is_external_mail"], True)
			self.assertNotIn("retry", kwargs)

	def test_forgot_password_by_email_refuses_without_a_personal_email(self):
		real_get_value = frappe.db.get_value

		def get_value(doctype, filters, fieldname, *args, **kwargs):
			return None if fieldname == "personal_email" else real_get_value(doctype, filters, fieldname, *args, **kwargs)

		with patch.object(v1_auth.frappe, "get_value", return_value="worker@one-fm.com"), patch.object(
			v1_auth.frappe.db, "get_value", side_effect=get_value
		), patch.object(v1_auth, "enqueue") as enqueue:
			v1_auth.forgot_password(employee_id="EMP-TEST-1", otp_source="email")

		self.assertEqual(frappe.local.response["http_status_code"], 400)
		self.assertEqual(frappe.local.response["message"], "No Email Address")
		enqueue.assert_not_called()
