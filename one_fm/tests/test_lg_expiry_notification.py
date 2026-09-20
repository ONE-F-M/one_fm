# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002449: a week's notice before a PAM Licence letter of guarantee expires.

Who is told is configured in GRD Settings - the first row addressed, the rest copied in -
and the body is laid out the way the assignment rules lay one out.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from one_fm.grd.lg_expiry import (
	NOTICE_DAYS,
	RECIPIENTS_FIELD,
	SETTINGS,
	expiring_licenses,
	notification_recipients,
	send_lg_expiry_alert,
)

SEEDED = "WI-002449-LICENCE-"
USERS = ["Administrator"]


def _clear():
	frappe.db.delete("PAM License Details", {"name": ["like", SEEDED + "%"]})
	frappe.db.delete("Action User", {"parenttype": SETTINGS, "parentfield": RECIPIENTS_FIELD})


def _licence(suffix, lg_expiry_date, lg_number="LG-001"):
	"""A licence row written without running the controller: PAM License Details
	recalculates every sector figure on validate, and none of that is under test."""
	doc = frappe.new_doc("PAM License Details")
	doc.name = SEEDED + suffix
	doc.label_name = SEEDED + suffix
	doc.license_name = "WI-002449 Licence"
	doc.civil_id_number_for_licensing = "999" + suffix
	doc.issuing_authority = "PAM"
	doc.lg_number = lg_number
	doc.lg_expiry_date = lg_expiry_date
	doc.db_insert()
	return doc.name


def _set_recipients(users):
	"""Write the settings table directly - GRD Settings is a Single and saving it would
	drag in every other setting on it."""
	frappe.db.delete("Action User", {"parenttype": SETTINGS, "parentfield": RECIPIENTS_FIELD})
	for idx, user in enumerate(users, 1):
		row = frappe.new_doc("Action User")
		row.parent = SETTINGS
		row.parenttype = SETTINGS
		row.parentfield = RECIPIENTS_FIELD
		row.idx = idx
		row.user = user
		row.db_insert()


def _real_users(count):
	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "name": ["not in", ["Administrator", "Guest"]]},
		pluck="name",
		limit=count,
	)
	return users if len(users) == count else None


class TestWhoIsTold(FrappeTestCase):
	def setUp(self):
		_clear()

	def tearDown(self):
		_clear()

	def test_nobody_configured_means_nobody_is_addressed(self):
		self.assertEqual(notification_recipients(), (None, []))

	def test_the_first_row_is_the_recipient_and_the_rest_are_copied(self):
		users = _real_users(3)
		if not users:
			self.skipTest("needs three enabled users on this site")
		_set_recipients(users)

		to, cc = notification_recipients()

		self.assertEqual(to, users[0])
		self.assertEqual(cc, users[1:])

	def test_one_row_is_a_recipient_with_nobody_copied(self):
		users = _real_users(1)
		if not users:
			self.skipTest("needs an enabled user on this site")
		_set_recipients(users)

		self.assertEqual(notification_recipients(), (users[0], []))

	def test_the_order_is_the_order_they_were_entered(self):
		"""Row order is the whole rule - it decides who is addressed."""
		users = _real_users(3)
		if not users:
			self.skipTest("needs three enabled users on this site")
		_set_recipients(list(reversed(users)))

		to, cc = notification_recipients()

		self.assertEqual(to, users[2])
		self.assertEqual(cc, [users[1], users[0]])

	def test_administrator_is_dropped(self):
		"""sendemail strips it from recipients but not from cc, which would leave a copy
		going nowhere."""
		users = _real_users(1)
		if not users:
			self.skipTest("needs an enabled user on this site")
		_set_recipients(["Administrator", users[0]])

		self.assertEqual(notification_recipients(), (users[0], []))

	def test_a_repeated_user_is_not_copied_to_twice(self):
		users = _real_users(2)
		if not users:
			self.skipTest("needs two enabled users on this site")
		_set_recipients([users[0], users[1], users[0]])

		self.assertEqual(notification_recipients(), (users[0], [users[1]]))


class TestWhichLicencesAreFound(FrappeTestCase):
	def setUp(self):
		_clear()

	def tearDown(self):
		_clear()

	def test_a_licence_expiring_in_a_week_is_found(self):
		name = _licence("A", add_days(today(), NOTICE_DAYS))

		self.assertIn(name, [row.name for row in expiring_licenses()])

	def test_a_day_either_side_is_not(self):
		"""An exact date, so a licence is announced once rather than every day for a week."""
		_licence("B", add_days(today(), NOTICE_DAYS - 1))
		_licence("C", add_days(today(), NOTICE_DAYS + 1))

		found = [row.name for row in expiring_licenses()]

		self.assertNotIn(SEEDED + "B", found)
		self.assertNotIn(SEEDED + "C", found)

	def test_a_licence_with_no_expiry_date_is_not_found(self):
		_licence("D", None)

		self.assertNotIn(SEEDED + "D", [row.name for row in expiring_licenses()])

	def test_the_notice_is_the_one_the_story_asks_for(self):
		self.assertEqual(NOTICE_DAYS, 7)

	def test_it_carries_what_the_email_has_to_print(self):
		"""AC: the notification and email must include the LG Number and Expiry Date."""
		_licence("E", add_days(today(), NOTICE_DAYS), lg_number="LG-WI-002449")

		row = next(r for r in expiring_licenses() if r.name == SEEDED + "E")

		self.assertEqual(row.lg_number, "LG-WI-002449")
		self.assertIsNotNone(row.lg_expiry_date)


class TestTheAlertItself(FrappeTestCase):
	def setUp(self):
		_clear()
		self.users = _real_users(2)
		if not self.users:
			self.skipTest("needs two enabled users on this site")
		_licence("F", add_days(today(), NOTICE_DAYS), lg_number="LG-WI-002449")
		self.licence = next(r for r in expiring_licenses() if r.name == SEEDED + "F")
		self.sent = []

	def tearDown(self):
		frappe.db.delete("Notification Log", {"document_name": ["like", SEEDED + "%"]})
		_clear()

	def _send(self):
		"""sendemail is replaced: what is under test is who it is called for, and the
		test site should not queue mail."""
		import one_fm.grd.lg_expiry as lg_expiry

		original = lg_expiry.sendemail
		lg_expiry.sendemail = lambda **kwargs: self.sent.append(kwargs)
		try:
			send_lg_expiry_alert(self.licence, self.users[0], self.users[1:])
		finally:
			lg_expiry.sendemail = original

		return self.sent[0]

	def test_the_first_user_is_addressed_and_the_rest_copied(self):
		call = self._send()

		self.assertEqual(call["recipients"], [self.users[0]])
		self.assertEqual(call["cc"], self.users[1:])

	def test_the_body_prints_the_lg_number_and_expiry_date(self):
		call = self._send()

		self.assertIn("LG-WI-002449", call["content"])
		self.assertIn("LG Number", call["content"])
		self.assertIn("LG Expiry Date", call["content"])

	def test_the_body_follows_the_assignment_rule_layout(self):
		"""The same opening line and the same Label/Value table the assignment rules send
		(overrides/assignment_rule.get_assignment_rule_description)."""
		content = self._send()["content"]

		self.assertIn("requires your attention/action", content)
		self.assertIn('<th style="padding: 10px; text-align: left; background-color: #f2f2f2;">Label</th>', content)
		self.assertIn('<th style="padding: 10px; text-align: left; background-color: #f2f2f2;">Value</th>', content)
		self.assertIn('<table cellpadding="0" cellspacing="0" border="1" style="border-collapse: collapse;">', content)

	def test_the_subject_names_the_lg(self):
		self.assertIn("LG-WI-002449", self._send()["subject"])

	def test_everyone_told_gets_it_on_the_bell(self):
		"""A copied-in reader has the same reason to see it as the one addressed."""
		self._send()

		told = frappe.get_all(
			"Notification Log",
			filters={"document_type": "PAM License Details", "document_name": SEEDED + "F"},
			pluck="for_user",
		)

		self.assertEqual(sorted(told), sorted(self.users))

	def test_the_email_is_tied_back_to_the_licence(self):
		call = self._send()

		self.assertEqual(call["reference_doctype"], "PAM License Details")
		self.assertEqual(call["reference_name"], SEEDED + "F")

	def test_the_copy_is_written_as_a_real_cc_header(self):
		"""email_body.make() writes "To: <!--recipient-->" and no Cc header at all unless
		expose_recipients is "header" - so a copied-in reader got the mail but it arrived
		looking as though it were addressed to them alone, and the recipient could not see
		who else had been told. That is what came back from testing."""
		self.assertEqual(self._send()["expose_recipients"], "header")

	def test_the_notification_log_does_not_send_its_own_email(self):
		"""Notification Log's after_insert emails through the new_notification template
		unless the type is one Frappe never emails. Without this everybody got two emails
		for one licence, and the one they opened was that one - no Cc, addressed to them."""
		self._send()

		types = frappe.get_all(
			"Notification Log",
			filters={"document_type": "PAM License Details", "document_name": SEEDED + "F"},
			pluck="type",
		)

		self.assertEqual(set(types), {"Alert"})

	def test_alert_is_still_the_type_frappe_never_emails(self):
		"""The behaviour the line above depends on, asked of Frappe rather than assumed -
		if this ever changes, the duplicate comes back silently."""
		from frappe.desk.doctype.notification_settings.notification_settings import (
			is_email_notifications_enabled_for_type,
		)

		self.assertFalse(is_email_notifications_enabled_for_type(self.users[0], "Alert"))


class TestTheSettingsField(FrappeTestCase):
	def test_grd_settings_carries_the_recipient_table(self):
		field = frappe.get_meta(SETTINGS).get_field(RECIPIENTS_FIELD)

		self.assertIsNotNone(field, "run bench migrate")
		self.assertEqual(field.fieldtype, "Table MultiSelect")
		self.assertEqual(field.options, "Action User")

	def test_the_job_is_scheduled_daily(self):
		from one_fm import hooks

		self.assertIn("one_fm.grd.lg_expiry.notify_lg_expiry", hooks.scheduler_events["daily"])
