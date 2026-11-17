# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-004748: HR is emailed once, three days after an Employee record is created."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, get_datetime, today

from one_fm import hooks
from one_fm.events import new_employee_notification as job

MODULE = "one_fm.events.new_employee_notification"
JOB_PATH = f"{MODULE}.send_new_employee_id_notifications"
HR = ["hr-wi4748@example.com", "hr-wi4748-two@example.com"]


def _employee(**overrides):
	row = frappe._dict(
		name="HR-EMP-WI4748",
		employee_name="Test Person",
		department="Operations - TST",
		designation="Guard",
		date_of_joining="2026-01-15",
		owner="Administrator",
		creation=get_datetime("2026-01-10 09:30:00"),
	)
	row.update(overrides)
	return row


class TestRegistration(FrappeTestCase):
	def test_the_job_is_in_the_daily_list_exactly_once(self):
		self.assertEqual(hooks.scheduler_events["daily"].count(JOB_PATH), 1)

	def test_the_job_path_resolves(self):
		self.assertTrue(callable(frappe.get_attr(JOB_PATH)))

	def test_the_recipient_setting_is_a_custom_field_on_hr_settings(self):
		from one_fm.custom.custom_field.hr_settings import get_hr_settings_custom_fields

		names = [f["fieldname"] for f in get_hr_settings_custom_fields()["HR Settings"]]
		self.assertEqual(names.count(job.RECIPIENTS_FIELD), 1)


class TestRecipients(FrappeTestCase):
	def _recipients_for(self, raw):
		with patch(f"{MODULE}.frappe.db.get_single_value", return_value=raw):
			return job.get_recipients()

	def test_nothing_configured_means_nobody(self):
		self.assertEqual(self._recipients_for(None), [])
		self.assertEqual(self._recipients_for("  "), [])

	def test_commas_and_new_lines_both_separate_and_junk_is_dropped(self):
		raw = f"{HR[0]}, not-an-email\n{HR[1]};{HR[0]}"
		self.assertEqual(self._recipients_for(raw), HR)


class TestMessage(FrappeTestCase):
	def test_every_template_field_is_present(self):
		message = job.build_message(_employee())
		for expected in (
			"Hi HR Team",
			"created 3 days ago",
			"Test Person",
			"HR-EMP-WI4748",
			"Operations - TST",
			"Guard",
			"Created By:",
			"System",
			"/app/employee/HR-EMP-WI4748",
		):
			self.assertIn(expected, message)

	def test_start_date_is_the_date_of_joining(self):
		message = job.build_message(_employee(date_of_joining="2026-02-20"))
		self.assertIn(frappe.utils.format_date("2026-02-20"), message)

	def test_a_missing_start_date_or_department_does_not_break_the_mail(self):
		message = job.build_message(_employee(date_of_joining=None, department=None, designation=None))
		self.assertIn("Not set", message)

	def test_the_creator_is_named_when_it_is_a_user(self):
		with patch(f"{MODULE}.frappe.db.get_value", return_value="Jane Doe"):
			self.assertEqual(job.creator_name("jane@example.com"), "Jane Doe")

	def test_automatic_creators_are_reported_as_system(self):
		self.assertEqual(job.creator_name("Administrator"), "System")
		self.assertEqual(job.creator_name(None), "System")


class TestTheJob(FrappeTestCase):
	def _run(self, employees, recipients=HR, notified=()):
		with patch(f"{MODULE}.get_recipients", return_value=recipients), patch(
			f"{MODULE}.get_employees_created_on", return_value=employees
		) as lookup, patch(f"{MODULE}.already_notified", side_effect=lambda n: n in notified), patch(
			f"{MODULE}.mark_notified"
		) as mark, patch(f"{MODULE}.sendemail") as send, patch(f"{MODULE}.frappe.db.commit"):
			job.send_new_employee_id_notifications()
		return lookup, mark, send

	def test_it_looks_at_the_day_three_days_ago(self):
		lookup, _mark, _send = self._run([])
		lookup.assert_called_once_with(add_days(today(), -3))

	def test_one_email_per_employee_to_the_configured_recipients(self):
		_lookup, mark, send = self._run([_employee(name="E1"), _employee(name="E2")])
		self.assertEqual(send.call_count, 2)
		kwargs = send.call_args_list[0].kwargs
		self.assertEqual(kwargs["recipients"], HR)
		self.assertEqual(kwargs["subject"], "New Employee ID Created")
		self.assertEqual(kwargs["reference_doctype"], "Employee")
		self.assertEqual(kwargs["reference_name"], "E1")
		self.assertTrue(kwargs["is_external_mail"])
		self.assertEqual([c.args[0] for c in mark.call_args_list], ["E1", "E2"])

	def test_an_employee_already_notified_is_skipped(self):
		_lookup, mark, send = self._run([_employee(name="E1"), _employee(name="E2")], notified=("E1",))
		self.assertEqual(send.call_count, 1)
		self.assertEqual(send.call_args.kwargs["reference_name"], "E2")
		mark.assert_called_once_with("E2")

	def test_no_recipients_means_nothing_is_looked_up_or_sent(self):
		lookup, mark, send = self._run([_employee()], recipients=[])
		lookup.assert_not_called()
		send.assert_not_called()
		mark.assert_not_called()

	def test_a_failed_send_is_not_marked_so_the_next_run_retries(self):
		with patch(f"{MODULE}.get_recipients", return_value=HR), patch(
			f"{MODULE}.get_employees_created_on", return_value=[_employee()]
		), patch(f"{MODULE}.already_notified", return_value=False), patch(
			f"{MODULE}.mark_notified"
		) as mark, patch(f"{MODULE}.sendemail", side_effect=Exception("smtp down")), patch(
			f"{MODULE}.frappe.log_error"
		) as log_error, patch(f"{MODULE}.frappe.db.commit"):
			job.send_new_employee_id_notifications()
		mark.assert_not_called()
		log_error.assert_called_once()
