from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from one_fm import processor


class TestSendemailBcc(FrappeTestCase):
	def test_bcc_reaches_frappe_sendmail(self):
		with patch.object(processor.frappe, "sendmail") as sendmail:
			processor.sendemail(
				recipients=["a@example.com"],
				subject="Hi",
				cc=["c@example.com"],
				bcc=["b1@example.com", "b2@example.com"],
				is_external_mail=True,
			)
		kwargs = sendmail.call_args.kwargs
		self.assertEqual(kwargs["bcc"], ["b1@example.com", "b2@example.com"])
		self.assertEqual(kwargs["recipients"], ["a@example.com"])
		self.assertEqual(kwargs["cc"], ["c@example.com"])

	def test_callers_without_bcc_send_as_before(self):
		with patch.object(processor.frappe, "sendmail") as sendmail:
			processor.sendemail("a@example.com", "Hi", is_external_mail=True)
		self.assertIsNone(sendmail.call_args.kwargs["bcc"])
