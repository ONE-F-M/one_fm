# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002016: the monthly penalty report email to the departments."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from one_fm.legal.penalty_report_email import (
	EMAIL_COLUMNS,
	build_message,
	cell_value,
	get_cycle,
	get_recipients,
	send_penalty_report_for_cycle,
)

# The reporter's notification template, in its order.
EXPECTED_COLUMNS = [
	"Violation Date", "ERP ID", "Issued by", "Serial No.", "Employee ID",
	"Employee Name", "Location", "Violation Category", "Penalty", "Status",
]


def _a_user():
	name = frappe.db.get_value("User", {"enabled": 1, "email": ["is", "set"]}, "name")
	if not name:
		raise frappe.DoesNotExistError("No enabled user with an email on this site")
	return name


class TestPenaltyReportEmail(FrappeTestCase):
	def setUp(self):
		self.user = _a_user()
		self.settings = frappe.get_doc("HR Settings")
		self.settings.set("penalty_email_recipients", [])
		self.settings.flags.ignore_permissions = True
		self.settings.save()
		frappe.clear_cache(doctype="HR Settings")

	def _configure(self, rows):
		self.settings = frappe.get_doc("HR Settings")
		self.settings.set("penalty_email_recipients", [])
		for row_type, user in rows:
			self.settings.append("penalty_email_recipients", {"type": row_type, "user_id": user})
		self.settings.flags.ignore_permissions = True
		self.settings.save()
		frappe.clear_cache(doctype="HR Settings")

	# ------------------------------------------------------------------- cycle

	def test_the_cycle_runs_from_the_23rd_to_the_22nd(self):
		from_date, to_date = get_cycle("2026-08-22")

		self.assertEqual(str(to_date), "2026-08-22")
		self.assertEqual(str(from_date), "2026-07-23")

	def test_the_cycle_is_a_whole_month_across_a_year_boundary(self):
		from_date, to_date = get_cycle("2027-01-22")

		self.assertEqual(str(from_date), "2026-12-23")
		self.assertEqual(str(to_date), "2027-01-22")

	def test_february_still_starts_on_the_23rd(self):
		from_date, to_date = get_cycle("2027-03-22")

		self.assertEqual(str(from_date), "2027-02-23")
		self.assertEqual(str(to_date), "2027-03-22")

	def test_the_default_cycle_ends_on_the_22nd_of_this_month(self):
		_from_date, to_date = get_cycle()

		self.assertEqual(getdate(to_date).day, 22)

	def test_the_cycle_is_a_closed_range_of_31_days_of_dates(self):
		from_date, to_date = get_cycle("2026-08-22")

		self.assertEqual((getdate(to_date) - getdate(from_date)).days, 30)

	# -------------------------------------------------------------- recipients

	def test_to_and_cc_are_separated(self):
		second = frappe.db.get_value(
			"User", {"enabled": 1, "email": ["is", "set"], "name": ["!=", self.user]}, "name"
		)
		if not second:
			self.skipTest("Only one enabled user with an email on this site")
		self._configure([("TO", self.user), ("CC", second)])

		to_addresses, cc_addresses = get_recipients()

		self.assertEqual(to_addresses, [frappe.db.get_value("User", self.user, "email")])
		self.assertEqual(cc_addresses, [frappe.db.get_value("User", second, "email")])

	def test_no_rows_means_no_addresses(self):
		self.assertEqual(get_recipients(), ([], []))

	def test_the_type_field_offers_only_to_and_cc(self):
		options = frappe.get_meta("Penalty Email Recipient").get_field("type").options

		self.assertEqual(options.split("\n"), ["TO", "CC"])

	def test_the_user_field_links_strictly_to_user(self):
		field = frappe.get_meta("Penalty Email Recipient").get_field("user_id")

		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "User")
		self.assertTrue(field.reqd)

	# ------------------------------------------------- halting, not broadcasting

	def test_with_no_recipients_nothing_is_sent(self):
		before = frappe.db.count("Email Queue")

		send_penalty_report_for_cycle()

		self.assertEqual(frappe.db.count("Email Queue"), before)

	def test_with_no_recipients_the_reason_is_logged(self):
		before = frappe.db.count("Error Log")

		send_penalty_report_for_cycle()

		self.assertGreater(frappe.db.count("Error Log"), before)

	def test_an_empty_cycle_sends_nothing(self):
		self._configure([("TO", self.user)])
		before = frappe.db.count("Email Queue")

		# A cycle far enough back that this site has no penalties in it.
		send_penalty_report_for_cycle(end_date="2015-08-22")

		self.assertEqual(frappe.db.count("Email Queue"), before)

	def test_an_empty_cycle_is_logged(self):
		self._configure([("TO", self.user)])
		before = frappe.db.count("Error Log")

		send_penalty_report_for_cycle(end_date="2015-08-22")

		self.assertGreater(frappe.db.count("Error Log"), before)

	def test_the_cc_row_is_visible_as_cc_not_just_delivered(self):
		"""Frappe delivers CC recipients either way, but only writes the CC header when
		expose_recipients is "header" - so without it a department lead receives the report
		with no idea who else was told. Asserted on the queued email rather than on the call,
		because it is the header on the wire that was missing.
		"""
		second = frappe.db.get_value(
			"User", {"enabled": 1, "email": ["is", "set"], "name": ["!=", self.user]}, "name"
		)
		if not second:
			self.skipTest("Only one enabled user with an email on this site")
		self._configure([("TO", self.user), ("CC", second)])

		before = frappe.db.count("Email Queue")
		send_penalty_report_for_cycle()
		if frappe.db.count("Email Queue") == before:
			self.skipTest("No penalties in the current cycle to send")

		queued = frappe.get_all(
			"Email Queue", fields=["name", "expose_recipients", "show_as_cc"],
			order_by="creation desc", limit_page_length=1,
		)[0]

		self.assertEqual(queued.expose_recipients, "header")
		self.assertIn(
			frappe.db.get_value("User", second, "email"), queued.show_as_cc or ""
		)

	# ------------------------------------------------------------------- table

	def test_the_table_carries_the_reporter_s_columns_in_order(self):
		self.assertEqual([label for label, _fieldname in EMAIL_COLUMNS], EXPECTED_COLUMNS)

	def test_the_table_renders_a_row_per_penalty(self):
		rows = [
			frappe._dict(violation_date=getdate("2026-08-01"), issuer="HR-EMP-1",
			             issuer_name="A Supervisor", penalty_serial_no="1890",
			             employee_id_number="2607005IN000", employee_name="An Employee",
			             operations_site="Opera", penalty_name="Absent Without Excuse",
			             penalty="Deduct 1 day", employee_response="Accepted"),
			frappe._dict(violation_date=getdate("2026-08-02"), penalty="Warning"),
		]

		html = build_message("2026-07-23", "2026-08-22", rows)

		self.assertEqual(html.count("<tr>"), len(rows) + 1)  # + the header row
		self.assertIn("Deduct 1 day", html)
		self.assertIn("An Employee", html)
		self.assertIn("1890", html)

	def test_the_covering_note_names_the_cycle(self):
		html = build_message("2026-07-23", "2026-08-22", [frappe._dict(penalty="Warning")])

		self.assertIn("Dear Team,", html)
		self.assertIn("Penalties submitted from", html)

	def test_a_value_carrying_markup_cannot_break_out_of_its_cell(self):
		rows = [frappe._dict(employee_name="<script>alert(1)</script>", penalty="Warning")]

		html = build_message("2026-07-23", "2026-08-22", rows)

		self.assertNotIn("<script>", html)

	def test_a_missing_value_renders_as_an_empty_cell(self):
		self.assertEqual(cell_value(frappe._dict(), "employee_name"), "")
		self.assertEqual(cell_value(frappe._dict(employee_name=None), "employee_name"), "")

	def test_a_whole_number_does_not_render_as_a_decimal(self):
		self.assertEqual(cell_value(frappe._dict(deductions=1.0), "deductions"), "1")

	def test_the_message_is_a_fragment_for_the_house_template_to_wrap(self):
		# sendemail already supplies the logo, signature and confidentiality notice.
		html = build_message("2026-07-23", "2026-08-22", [frappe._dict(penalty="Warning")])

		self.assertNotIn("<html", html.lower())
		self.assertNotIn("one-fm.com", html)
