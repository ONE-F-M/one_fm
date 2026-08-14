# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""The monthly penalty report email to the departments (WI-002016).

Sent on the 23rd at 06:15 covering the 23rd of the previous month to the 22nd of this one,
which is the cycle payroll already runs on - a penalty deducted in a month's payroll is one
the departments should have been told about in that month's email.

The rows come from the One FM Penalty Report rather than from a query of this module's own.
The email and the report are two renderings of the same month, and two queries would
eventually disagree about it.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, escape_html, flt, formatdate, get_first_day, getdate, today

from one_fm.legal.report.one_fm_penalty_report.one_fm_penalty_report import execute as run_report
from one_fm.processor import sendemail

# Payroll cuts on the 22nd, so a cycle runs from the 23rd of the previous month to the 22nd
# of this one.
CYCLE_END_DAY = 22

# The email's columns, which are not the report's: it drops Sl.No, Receiving Date, Type of
# Violation and the recipient's ERP ID, because a department lead is reading a summary rather
# than reconciling payroll. Taken from the reporter's notification template.
EMAIL_COLUMNS = (
	("Violation Date", "violation_date"),
	("ERP ID", "issuer"),
	("Issued by", "issuer_name"),
	("Serial No.", "penalty_serial_no"),
	("Employee ID", "employee_id_number"),
	("Employee Name", "employee_name"),
	("Location", "operations_site"),
	("Violation Category", "penalty_name"),
	("Penalty", "penalty"),
	("Status", "employee_response"),
)

HEADER_STYLE = "padding: 10px; text-align: left; background-color: #f2f2f2;"
CELL_STYLE = "padding: 10px;"


def send_monthly_penalty_report():
	"""Scheduled entry point, wired to the 23rd at 06:15.

	The date lives in the cron rather than in a guard here, so the schedule is visible where
	schedules are read and cannot end up saying two different things.
	"""
	send_penalty_report_for_cycle()


@frappe.whitelist()
def send_penalty_report_for_cycle(end_date: str = None):
	"""Send one cycle's report. Separate from the schedule so HR can re-run a month by hand.

	`end_date` is the last day of the cycle, defaulting to the 22nd of the current month.
	"""
	frappe.only_for(("HR Manager", "System Manager"))

	from_date, to_date = get_cycle(end_date)
	to_addresses, cc_addresses = get_recipients()

	if not (to_addresses or cc_addresses):
		# Logged rather than raised. This runs unattended, and the criterion is that it halts
		# instead of broadcasting to nobody.
		frappe.log_error(
			title="Monthly Penalty Report not sent: no recipients configured",
			message=(
				f"HR Settings has no rows in Penalty Email Recipients, so the report for "
				f"{from_date} to {to_date} was not sent."
			),
		)
		return

	rows = get_cycle_penalties(from_date, to_date)
	if not rows:
		frappe.log_error(
			title="Monthly Penalty Report not sent: no penalties in cycle",
			message=f"No penalties were submitted between {from_date} and {to_date}.",
		)
		return

	sendemail(
		recipients=to_addresses or cc_addresses,
		cc=cc_addresses if to_addresses else None,
		subject=_("Monthly Penalty Report - {0}-{1}").format(
			formatdate(from_date), formatdate(to_date)
		),
		header=[_("Monthly Penalty Report")],
		message=build_message(from_date, to_date, rows),
		is_scheduler_email=True,
	)
	return {"sent_to": to_addresses, "cc": cc_addresses, "penalties": len(rows)}


def get_cycle(end_date=None):
	"""(from_date, to_date) for the cycle ending on the 22nd of `end_date`'s month."""
	to_date = getdate(end_date) if end_date else getdate(get_first_day(today())).replace(day=CYCLE_END_DAY)
	from_date = add_days(add_months(to_date, -1), 1)
	return from_date, to_date


def get_cycle_penalties(from_date, to_date):
	"""The penalties submitted in the cycle, rendered as the report renders them.

	Selected on submission rather than on Violation Date, per the criterion: an incident from
	two months ago that was only signed off this month belongs in this month's email.

	`modified` stands in for the submission time because the doctype records no submitted-on
	of its own. A penalty is submitted at the end of its workflow and only its allow_on_submit
	fields can change afterwards, so the two coincide in practice - but an edit made after the
	cycle closes would move that penalty into the following month's email.
	"""
	_columns, rows = run_report({})
	if not rows:
		return []

	in_cycle = {
		row.name
		for row in frappe.get_all(
			"Penalty And Investigation",
			filters={
				"docstatus": 1,
				"name": ["in", [row.name for row in rows]],
				"modified": ["between", [from_date, add_days(to_date, 1)]],
			},
			fields=["name"],
		)
	}

	return [row for row in rows if row.name in in_cycle]


def get_recipients():
	"""(to, cc) addresses from the HR Settings child table.

	A row naming a user with no email address is dropped rather than carried through as an
	empty recipient, which some mail servers reject for the whole message.
	"""
	settings = frappe.get_cached_doc("HR Settings")
	to_addresses, cc_addresses = [], []

	for row in settings.get("penalty_email_recipients") or []:
		email = frappe.db.get_value("User", row.user_id, "email")
		if not email:
			continue
		(cc_addresses if row.type == "CC" else to_addresses).append(email)

	return to_addresses, cc_addresses


def build_message(from_date, to_date, rows):
	"""The salutation, the covering note and the table, as the reporter's template writes them.

	A fragment, not a whole document: sendemail wraps it in the house template, which already
	carries the logo, the signature and the confidentiality notice. The table markup matches
	the one the assignment-rule notifications use, so the departments get one house style.
	"""
	intro = _(
		"Please find below the report for Penalties submitted from {0} to {1}. Please inform "
		"employees regarding the decision as well as please acknowledge this email."
	).format(formatdate(from_date), formatdate(to_date))

	queries = _("Department users can contact HR if they have queries related to below penalties:")

	head = "".join(f"<th style='{HEADER_STYLE}'>{_(label)}</th>" for label, _fieldname in EMAIL_COLUMNS)
	body = "".join(
		"<tr>{0}</tr>".format(
			"".join(
				f"<td style='{CELL_STYLE}'>{escape_html(cell_value(row, fieldname))}</td>"
				for _label, fieldname in EMAIL_COLUMNS
			)
		)
		for row in rows
	)

	return (
		f"<p>{_('Dear Team,')}</p>"
		f"<p>{intro}</p>"
		f"<p>{queries}</p>"
		f"<table cellpadding='0' cellspacing='0' border='1' style='border-collapse: collapse;'>"
		f"<thead><tr>{head}</tr></thead>"
		f"<tbody>{body}</tbody>"
		f"</table>"
	)


def cell_value(row, fieldname):
	"""One cell, printed the way a reader expects rather than the way Python repr's it."""
	value = row.get(fieldname)
	if value in (None, ""):
		return ""
	if fieldname == "violation_date":
		return formatdate(value)
	if isinstance(value, float):
		return f"{flt(value):g}"
	return str(value)
