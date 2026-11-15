import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase

from one_fm.overrides.email_queue import get_subject, prepare_email_content


class FakeQueueBuilder:
	"""Minimal stand-in for QueueBuilder, exposing only what
	prepare_email_content() reads."""

	def __init__(self, in_reply_to=None, reference_doctype=None, subject="Hello"):
		self.in_reply_to = in_reply_to
		self.reference_doctype = reference_doctype
		self.reference_name = "TICKET-001"
		self.subject = subject
		self.sender = "support@example.com"
		self.reply_to = None
		self.bcc = None
		self.expose_recipients = None
		self.inline_images = []
		self.header = None
		self.message_id = "msg-1@example.com"
		self.is_notification = False
		self.read_receipt = False
		self._attachments = []

	def final_recipients(self):
		return ["customer@example.com"]

	def final_cc(self):
		return []

	def email_html_content(self):
		return "<p>body</p>"

	def email_text_content(self):
		return "body"

	def get_outgoing_email_account(self):
		# An unsaved Email Account is enough: EMail only reads sender/signature
		# settings off it, and the test site has no default outgoing account.
		account = frappe.new_doc("Email Account")
		account.email_id = "support@example.com"
		return account


class TestEmailQueueThreading(FrappeTestCase):
	"""Ticket 1831836: helpdesk replies opened a second Gmail conversation
	because the outgoing subject carried the ticket name and no References
	header was sent."""

	def test_subject_keeps_customer_thread_subject(self):
		doc = FakeQueueBuilder(subject="Re: Task: Process Owner Review")
		self.assertEqual(get_subject(doc), "Re: Task: Process Owner Review")

	def test_subject_does_not_append_ticket_name(self):
		doc = FakeQueueBuilder(subject="Re: Server is down")
		self.assertNotIn(doc.reference_name, get_subject(doc))

	def test_subject_gets_re_prefix_when_missing(self):
		doc = FakeQueueBuilder(subject="Server is down")
		self.assertEqual(get_subject(doc), "Re: Server is down")

	def test_subject_prefix_not_duplicated(self):
		for existing in ("Re: Hi", "Fwd: Hi", "FW: Hi", "re: Hi"):
			with self.subTest(existing=existing):
				self.assertEqual(get_subject(FakeQueueBuilder(subject=existing)), existing)

	def test_subject_falls_back_to_ticket_subject(self):
		doc = FakeQueueBuilder(subject=None)
		with patch.object(frappe.db, "get_value", return_value="Printer jammed"):
			self.assertEqual(get_subject(doc), "Re: Printer jammed")

	def test_subject_empty_when_nothing_to_use(self):
		doc = FakeQueueBuilder(subject=None)
		with patch.object(frappe.db, "get_value", return_value=None):
			self.assertEqual(get_subject(doc), "")

	def test_references_header_set_on_reply(self):
		doc = FakeQueueBuilder(in_reply_to="parent-msg@example.com")
		mail = prepare_email_content(doc)
		self.assertEqual(mail.msg_root["References"], "parent-msg@example.com")
		self.assertEqual(mail.msg_root["In-Reply-To"], "parent-msg@example.com")

	def test_no_references_header_on_fresh_email(self):
		mail = prepare_email_content(FakeQueueBuilder())
		self.assertIsNone(mail.msg_root["References"])

	def test_non_ticket_subject_untouched(self):
		"""Processor and BPMN emails carry no reference_doctype, so their
		subject must pass through verbatim."""
		doc = FakeQueueBuilder(subject="Task: Process Owner Review - vhmeplm65f")
		mail = prepare_email_content(doc)
		# EMail only writes the Subject header in make(); read it off the object.
		self.assertEqual(mail.subject, "Task: Process Owner Review - vhmeplm65f")
