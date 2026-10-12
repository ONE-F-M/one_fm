# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""One DSOT approval email per employee per continuous date cycle.

Each Employee Schedule entering ``Pending DSOT Approval`` used to send its own assignment
notification, so a week of overtime was eight near-identical emails. The ToDo assignment
is unchanged; only the email is consolidated.

Sent on commit rather than per row: a range is not known to be a range until its last row
is written, and a rolled-back roster run then sends nothing.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, formatdate, get_url, getdate

from one_fm.processor import sendemail

PENDING_DSOT = "Pending DSOT Approval"

# Where the names wait between being held and the commit that announces them.
FLAG = "dsot_pending_notifications"


def continuous_cycles(dates) -> list:
	"""Split dates into runs of consecutive days.

	``[13, 14, ..., 20, 23, 24]`` becomes ``[(13, 20), (23, 24)]``. Duplicates collapse:
	two overtime rows on one date are still one day of the cycle.
	"""
	unique = sorted({getdate(d) for d in dates if d})
	if not unique:
		return []

	cycles, start, previous = [], unique[0], unique[0]
	for current in unique[1:]:
		if current == add_days(previous, 1):
			previous = current
			continue
		cycles.append((start, previous))
		start = previous = current
	cycles.append((start, previous))
	return cycles


def queue(names) -> None:
	"""Remember schedules to announce, and announce them once this request commits.

	The after-commit hook is registered once per request, not once per schedule: eight
	rows held in one roster run are one email, which is the whole point.
	"""
	names = [name for name in (names or []) if name]
	if not names:
		return

	pending = frappe.flags.get(FLAG)
	if pending is None:
		pending = frappe.flags[FLAG] = set()
		frappe.db.after_commit.add(flush)

	pending.update(names)


def flush() -> None:
	"""Send one email per (employee, continuous cycle) for everything queued.

	Wrapped whole: the schedules are already saved and already blocking their Shift
	Assignments, so an unreachable mail server must not fail the roster save.
	"""
	names = frappe.flags.pop(FLAG, None)
	if not names:
		return

	try:
		approver = frappe.db.get_single_value("Operation Settings", "dsot_approver")
		if not approver:
			# Nobody configured: the requests still stand and still block.
			return

		rows = frappe.get_all(
			"Employee Schedule",
			filters={"name": ["in", list(names)], "workflow_state": PENDING_DSOT},
			fields=["name", "employee", "employee_name", "date"],
		)
		if not rows:
			return

		by_employee = {}
		for row in rows:
			by_employee.setdefault((row.employee, row.employee_name), []).append(row)

		# By employee first, then by cycle, so two people sharing a range get two emails.
		for (employee, employee_name), employee_rows in by_employee.items():
			dates = [r.date for r in employee_rows]
			for start, end in continuous_cycles(dates):
				shifts = [r for r in employee_rows if start <= getdate(r.date) <= end]
				send_cycle_email(
					approver=approver,
					employee=employee,
					employee_name=employee_name or employee,
					start=start,
					end=end,
					shifts=shifts,
				)
	except Exception:
		frappe.log_error(
			title="DSOT consolidated notification",
			message=frappe.get_traceback(),
		)


def pending_list_url(employee, start, end) -> str:
	"""The approver's landing place: this employee's pending cycle, and nothing else.

	A link to one schedule is the wrong destination for a request that is eight of them:
	the approver acts on the whole cycle, and Bulk Approve lives in the List View.
	"""
	filters = {
		"employee": employee,
		"workflow_state": PENDING_DSOT,
		"date": ["between", [str(start), str(end)]],
	}
	# Compact JSON: frappe.as_json pretty-prints, padding the URL for no benefit.
	query = "&".join(
		f"{field}={frappe.utils.quote(json.dumps(value, separators=(',', ':')) if isinstance(value, list) else str(value))}"
		for field, value in filters.items()
	)
	return f"{get_url()}/app/employee-schedule?{query}"


def send_cycle_email(approver, employee, employee_name, start, end, shifts) -> None:
	"""One cycle, one email.

	Renders one_fm's own notification table rather than editing Frappe's shared Assignment
	Notification, which serves every assignment in the system. Only the scope differs: the
	row is a cycle, and the link opens the pending range rather than one schedule.
	"""
	span = formatdate(start) if start == end else f"{formatdate(start)} to {formatdate(end)}"
	subject = _("DSOT Approval Request: {0} ({1})").format(employee_name, span)

	list_url = pending_list_url(employee, start, end)
	requestor = frappe.utils.get_fullname(frappe.session.user) or frappe.session.user

	# The cycle is the document here, so it is named by its range and size.
	document_name = span if start == end else _("{0} (Total: {1} Shifts)").format(span, len(shifts))

	if start == end:
		description = _("Approve or reject double shift overtime for {0} on {1}.").format(
			employee_name, span
		)
	else:
		description = _("Approve or reject double shift overtime for {0} from {1}.").format(
			employee_name, span
		)
	description += " " + _("Employee: {0} ({1}). Shifts: {2}.").format(
		employee_name, employee, len(shifts)
	)

	# Built here, as notify_assignment does, so the sentence stays one translatable
	# string with bold applied to its arguments.
	body_content = _("{0} assigned a new task {1} {2} to you").format(
		frappe.bold(requestor),
		frappe.bold(_("Employee Schedule")),
		frappe.bold(document_name),
	)

	# The table one_fm/overrides/notification_log.py already renders every Notification
	# Log email through, so a change to it reaches this email too.
	message = frappe.render_template(
		"one_fm/templates/emails/notification_log.html",
		context={
			"header": _("DSOT Approval Request on {0}").format(span),
			"document_name": document_name,
			"document_type": _("Employee Schedule"),
			"description": description,
			"body_content": body_content,
			# An anchor, not a bare URL: the filtered link carries encoded JSON,
			# which mail clients autolink badly.
			"doc_link": f'<a href="{list_url}">{list_url}</a>',
		},
	)

	# "Alert" is the one type Frappe never emails itself; any other and after_insert sends
	# a second copy through its own template. The bell still shows it.
	frappe.get_doc({
		"doctype": "Notification Log",
		"type": "Alert",
		"subject": subject,
		"email_content": message,
		"document_type": "Employee Schedule",
		"document_name": shifts[0].name if shifts else None,
		"for_user": approver,
	}).insert(ignore_permissions=True)

	sendemail(
		recipients=[approver],
		subject=subject,
		content=message,
		reference_doctype="Employee Schedule",
		reference_name=shifts[0].name if shifts else None,
		is_scheduler_email=True,
	)
