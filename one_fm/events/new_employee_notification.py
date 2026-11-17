# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""WI-004748: tell HR, three days after an Employee record is created, to check it.

A daily job finds every Employee whose ``creation`` falls on the calendar day three days
ago - whoever or whatever created it (a user, an import, an onboarding flow) - and sends
the HR team one email per employee asking them to verify the profile and employee folder.

Who is "the HR email group"? Nothing in one_fm names one. The nearest existing settings are
single-purpose (``payroll_notifications_email`` is payroll, ``helpdesk_notification_emails``
is Helpdesk, ``custom_hr_manager`` is one user), so this adds its own
``HR Settings > new_employee_notification_emails`` - a list of addresses, which can be a
group mailbox. It is blank until HR fills it in; with nothing configured the job sends
nothing rather than inventing an address.

Duplicate guard: after a successful send the job writes an Info comment on the Employee.
A second run on the same day (or a retry) finds the comment and skips that employee. If
sending fails nothing is written, so the next run retries.
"""

import re

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	format_date,
	get_datetime,
	get_url_to_form,
	getdate,
	today,
	validate_email_address,
)

from one_fm.processor import sendemail

DAYS_AFTER_CREATION = 3
SETTINGS = "HR Settings"
RECIPIENTS_FIELD = "new_employee_notification_emails"
SENT_MARKER = "New Employee ID notification sent to HR"
SUBJECT = "New Employee ID Created"
SYSTEM_USERS = ("Administrator", "Guest", "")


def get_recipients() -> list:
	"""The valid addresses configured in HR Settings, in the order entered.

	Entries may be separated by commas, semicolons or new lines; anything that is not a
	valid email address is dropped, and duplicates are removed.
	"""
	raw = frappe.db.get_single_value(SETTINGS, RECIPIENTS_FIELD) or ""
	recipients = []
	for item in re.split(r"[,;\n]", raw):
		item = item.strip()
		if item and validate_email_address(item, throw=False) and item not in recipients:
			recipients.append(item)
	return recipients


def get_employees_created_on(day) -> list:
	"""Employees whose creation timestamp falls anywhere on ``day``."""
	day = getdate(day)
	start = get_datetime(f"{day} 00:00:00")
	end = get_datetime(f"{day} 23:59:59.999999")
	return frappe.get_all(
		"Employee",
		filters=[["creation", ">=", start], ["creation", "<=", end]],
		fields=[
			"name",
			"employee_name",
			"department",
			"designation",
			"date_of_joining",
			"owner",
			"creation",
		],
		order_by="creation asc",
	)


def already_notified(employee_name: str) -> bool:
	return bool(
		frappe.db.exists(
			"Comment",
			{
				"reference_doctype": "Employee",
				"reference_name": employee_name,
				"comment_type": "Info",
				"content": ["like", f"%{SENT_MARKER}%"],
			},
		)
	)


def mark_notified(employee_name: str) -> None:
	frappe.get_doc("Employee", employee_name).add_comment("Info", SENT_MARKER)


def creator_name(owner) -> str:
	"""Full name of the creating user, or ``System`` for the automatic ones."""
	if (owner or "") in SYSTEM_USERS:
		return _("System")
	return frappe.db.get_value("User", owner, "full_name") or owner


def build_message(employee) -> str:
	department = employee.get("department") or _("Not set")
	job_title = employee.get("designation") or _("Not set")
	start_date = (
		format_date(employee.get("date_of_joining")) if employee.get("date_of_joining") else _("Not set")
	)
	link = get_url_to_form("Employee", employee.get("name"))
	esc = frappe.utils.escape_html

	return f"""
<p>Hi HR Team,</p>
<p>This is an automated reminder that the following employee ID was created {DAYS_AFTER_CREATION} days ago.
Please verify that their profile information and employee folder are complete.</p>
<ul>
<li><b>Employee Name:</b> {esc(employee.get("employee_name") or "")}</li>
<li><b>Employee ID:</b> {esc(employee.get("name"))}</li>
<li><b>Department / Role:</b> {esc(department)} &ndash; {esc(job_title)}</li>
<li><b>Start Date:</b> {esc(start_date)}</li>
<li><b>Created By:</b> {esc(creator_name(employee.get("owner")))}</li>
<li><b>Date Created:</b> {esc(format_date(employee.get("creation")))}</li>
<li><b>Link to Profile / Folder:</b> <a href="{link}">{link}</a></li>
</ul>
"""


def send_notification(employee, recipients) -> bool:
	"""One employee, one email. True when queued, False when sending failed (retried next run)."""
	try:
		sendemail(
			recipients=list(recipients),
			subject=_(SUBJECT),
			content=build_message(employee),
			reference_doctype="Employee",
			reference_name=employee.get("name"),
			# HR addresses (a group mailbox, say) need not be Users with an Employee record;
			# without this sendemail drops every recipient that is not one.
			is_external_mail=True,
		)
		return True
	except Exception:
		frappe.log_error(title="New Employee ID notification", message=frappe.get_traceback())
		return False


def send_new_employee_id_notifications() -> None:
	"""Daily job: email HR about every Employee created exactly three days ago."""
	recipients = get_recipients()
	if not recipients:
		# Nothing configured: say nothing rather than guess an address.
		return

	for employee in get_employees_created_on(add_days(today(), -DAYS_AFTER_CREATION)):
		if already_notified(employee.name):
			continue
		if send_notification(employee, recipients):
			mark_notified(employee.name)
		# Commit per row so a later failure cannot roll back a mail already queued and marked.
		frappe.db.commit()  # nosemgrep
