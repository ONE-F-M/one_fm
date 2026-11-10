"""Regression tests for the outgoing-mail burst that produced
"Invalid Outgoing Mail Server or Port: Connection unexpectedly closed".

Two separate defects fed that error:

1. ``one_fm.processor.sendemail`` defaulted to ``delayed=False``, which
   ``frappe.sendmail`` translates into ``now=True``: the SMTP conversation then
   happened inside the user's request, so a transport failure became a blocking
   "Incorrect Configuration" dialog on top of the document being saved.

2. ``one_fm.events.email_queue.after_insert`` enqueued one send job per queued
   mail, so a notification burst opened dozens of SMTP connections per minute
   and the relay throttled them.

These tests pin both behaviours. They are plain unittest + mock: no site or
database is touched.
"""

import unittest
from unittest.mock import MagicMock, patch


class TestSendemailQueuesByDefault(unittest.TestCase):
	def setUp(self):
		# sendemail is whitelisted, and the whitelist wrapper reads
		# frappe.local.flags before the call reaches our patched module. Give it
		# something to read so the test runs without a site.
		import frappe

		if not getattr(frappe.local, "flags", None):
			frappe.local.flags = frappe._dict(in_test=False)

	def test_default_is_delayed(self):
		"""sendemail must queue, never open SMTP inside the caller's request."""
		from one_fm import processor

		with patch.object(processor, "frappe") as mock_frappe:
			mock_frappe.db.get_single_value.return_value = 1
			# is_external_mail skips the per-recipient notification-settings
			# lookup, which would need a database.
			processor.sendemail(
				recipients=["someone@one-fm.com"], subject="Hi", content="Body", is_external_mail=True
			)

			mock_frappe.sendmail.assert_called_once()
			self.assertTrue(mock_frappe.sendmail.call_args.kwargs["delayed"])

	def test_send_priority_is_passed_through(self):
		"""Verification codes must be able to lead the flush batch."""
		from one_fm import processor

		with patch.object(processor, "frappe") as mock_frappe:
			mock_frappe.db.get_single_value.return_value = 1
			processor.sendemail(
				recipients=["someone@one-fm.com"],
				subject="Code",
				content="123456",
				is_external_mail=True,
				send_priority=2,
			)

			self.assertEqual(mock_frappe.sendmail.call_args.kwargs["send_priority"], 2)

	def test_default_priority_is_normal(self):
		from one_fm import processor

		with patch.object(processor, "frappe") as mock_frappe:
			mock_frappe.db.get_single_value.return_value = 1
			processor.sendemail(
				recipients=["someone@one-fm.com"], subject="Hi", content="Body", is_external_mail=True
			)

			self.assertEqual(mock_frappe.sendmail.call_args.kwargs["send_priority"], 1)

	def test_explicit_delayed_false_still_honoured(self):
		"""A caller that really needs an inline send can still ask for one."""
		from one_fm import processor

		with patch.object(processor, "frappe") as mock_frappe:
			mock_frappe.db.get_single_value.return_value = 1
			processor.sendemail(
				recipients=["someone@one-fm.com"],
				subject="Hi",
				content="Body",
				delayed=False,
				is_external_mail=True,
			)

			self.assertFalse(mock_frappe.sendmail.call_args.kwargs["delayed"])


class TestEmailQueueAfterInsert(unittest.TestCase):
	def _doc(self, recipient_count=1):
		doc = MagicMock()
		doc.recipients = [MagicMock() for _ in range(recipient_count)]
		return doc

	def test_enqueues_a_single_deduplicated_flush(self):
		"""One flush job per burst, not one send job per mail."""
		from one_fm.events import email_queue

		with patch.object(email_queue, "frappe") as mock_frappe:
			mock_frappe.flags.amp_html = None
			email_queue.after_insert(self._doc(), None)

			mock_frappe.enqueue.assert_called_once()
			kwargs = mock_frappe.enqueue.call_args.kwargs
			self.assertEqual(kwargs["job_id"], email_queue.FLUSH_JOB_ID)
			self.assertTrue(kwargs["deduplicate"])
			self.assertTrue(kwargs["enqueue_after_commit"])
			# The old signature passed the queue row name; the flush takes none.
			self.assertNotIn("name", kwargs)

	def test_bulk_mail_is_left_to_the_scheduler(self):
		from one_fm.events import email_queue

		with patch.object(email_queue, "frappe") as mock_frappe:
			mock_frappe.flags.amp_html = None
			email_queue.after_insert(self._doc(recipient_count=20), None)

			mock_frappe.enqueue.assert_not_called()


if __name__ == "__main__":
	unittest.main()
