# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""HD-1892786: the Helpdesk reminders go to a configured list of addresses, not one.

The ticket was reported as an access problem - night-shift operators "not receiving"
the reminder emails. It was never access: HR Settings held a single ``helpdesk_email``
and both jobs sent there and nowhere else. These tests pin the replacement: a table of
Helpdesk Notification Email rows read by both jobs, and nothing sent at all when the
table is empty.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.events.issue import send_open_hd_ticket_count_to_helpdesk_team
from one_fm.overrides.leave_application import remind_annual_leave_employees_to_helpdesk_user

SETTINGS = "HR Settings"
RECIPIENTS_FIELD = "helpdesk_notification_emails"
RECIPIENT_DOCTYPE = "Helpdesk Notification Email"
OLD_FIELD_NAME = "helpdesk_email"

SEEDED = ["hd-1892786-one@example.com", "hd-1892786-two@example.com"]


def _clear():
	frappe.db.delete(RECIPIENT_DOCTYPE, {"parenttype": SETTINGS, "parentfield": RECIPIENTS_FIELD})


def _set_recipients(emails):
	"""Write the settings table directly - HR Settings is a Single and saving it would
	drag in every other setting on it."""
	_clear()
	for idx, email in enumerate(emails, 1):
		row = frappe.new_doc(RECIPIENT_DOCTYPE)
		row.parent = SETTINGS
		row.parenttype = SETTINGS
		row.parentfield = RECIPIENTS_FIELD
		row.idx = idx
		row.email_id = email
		row.db_insert()


def _configured_recipients():
	return frappe.get_all(
		RECIPIENT_DOCTYPE,
		filters={"parenttype": SETTINGS, "parentfield": RECIPIENTS_FIELD},
		pluck="email_id",
		order_by="idx asc",
	)


class TestWhoIsTold(FrappeTestCase):
	def setUp(self):
		_clear()

	def tearDown(self):
		_clear()

	def test_nobody_configured_means_nobody_is_addressed(self):
		self.assertEqual(_configured_recipients(), [])

	def test_more_than_one_address_can_be_configured(self):
		"""The whole point of the ticket - the old field could hold exactly one."""
		_set_recipients(SEEDED)
		self.assertEqual(_configured_recipients(), SEEDED)

	def test_the_rows_keep_the_order_they_were_entered_in(self):
		_set_recipients(list(reversed(SEEDED)))
		self.assertEqual(_configured_recipients(), list(reversed(SEEDED)))

	def test_an_address_is_validated_as_an_email(self):
		row = frappe.new_doc(RECIPIENT_DOCTYPE)
		row.parent = SETTINGS
		row.parenttype = SETTINGS
		row.parentfield = RECIPIENTS_FIELD
		row.email_id = "not-an-email"
		self.assertRaises(frappe.ValidationError, row.insert)


class TestTheJobsSendNothingWhenUnconfigured(FrappeTestCase):
	"""Both jobs kept the single field's bargain: no recipients means no email rather
	than a broadcast to nobody. Neither may throw on the way to that."""

	def setUp(self):
		_clear()

	def tearDown(self):
		_clear()

	def test_the_open_ticket_count_sends_nothing(self):
		before = frappe.db.count("Email Queue")
		send_open_hd_ticket_count_to_helpdesk_team("<b>3 open tickets</b>")
		self.assertEqual(frappe.db.count("Email Queue"), before)

	def test_the_leave_reminder_sends_nothing(self):
		before = frappe.db.count("Email Queue")
		remind_annual_leave_employees_to_helpdesk_user()
		self.assertEqual(frappe.db.count("Email Queue"), before)


class TestTheField(FrappeTestCase):
	def test_the_setting_is_a_table_of_helpdesk_notification_emails(self):
		field = frappe.get_doc("Custom Field", {"dt": SETTINGS, "fieldname": RECIPIENTS_FIELD})
		self.assertEqual(field.fieldtype, "Table")
		self.assertEqual(field.options, RECIPIENT_DOCTYPE)

	def test_the_row_holds_an_email_and_nothing_else(self):
		"""No User link - the ticket asked for plain addresses, so that a recipient does
		not have to be a system user at all."""
		meta = frappe.get_meta(RECIPIENT_DOCTYPE)
		fields = [f for f in meta.fields if f.fieldtype not in ("Section Break", "Column Break")]
		self.assertEqual([f.fieldname for f in fields], ["email_id"])
		self.assertEqual(fields[0].fieldtype, "Data")
		self.assertEqual(fields[0].options, "Email")

	def test_the_single_address_field_is_gone(self):
		"""Two sources of truth for who is told is the bug coming back."""
		self.assertFalse(
			frappe.db.exists("Custom Field", {"dt": SETTINGS, "fieldname": OLD_FIELD_NAME})
		)
