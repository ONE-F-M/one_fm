from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.overrides.email_queue import prepare_email_content


class TestHelpdeskEmailSubject(FrappeTestCase):
	def _subject_sent(self, reference_doctype="HD Ticket"):
		builder = MagicMock(reference_doctype=reference_doctype, reference_name="256363", subject="Process Owner Review")
		with (
			patch("one_fm.overrides.email_queue.get_outgoing_support_email", return_value=False),
			patch("one_fm.overrides.email_queue.get_subject", return_value="Re: test 123 256363"),
			patch("one_fm.overrides.email_queue.get_email") as get_email,
		):
			prepare_email_content(builder)
		return get_email.call_args.kwargs["subject"]

	def tearDown(self):
		frappe.flags.keep_email_subject = None

	def test_ticket_email_gets_the_ticket_subject(self):
		self.assertEqual(self._subject_sent(), "Re: test 123 256363")

	def test_process_map_email_keeps_its_subject(self):
		frappe.flags.keep_email_subject = True
		self.assertEqual(self._subject_sent(), "Process Owner Review")

	def test_other_doctypes_keep_their_subject(self):
		self.assertEqual(self._subject_sent("ToDo"), "Process Owner Review")
