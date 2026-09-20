# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""WI-002602: one DSOT approval email per employee per continuous date cycle.

Every Employee Schedule entering ``Pending DSOT Approval`` used to put its own assignment
in front of the DSOT Approver as a normal assignment, so ERPNext sent one Assignment
Notification per row. A week of overtime for one person is eight rows, and the approver
got eight near-identical emails for what they experience as a single request.

The assignment itself is unchanged - the approver still needs the ToDo in their task list,
and the existing Approve/Reject flow is built on it. Only the EMAIL is consolidated: the
per-row notification is suppressed and one message is sent per (employee, continuous date
cycle) once the request that created them commits.

Why on commit rather than per row: a range is not known to be a range until the last row
of it has been written. Collecting the names as they are held and flushing once the
transaction commits is what turns eight rows into one email - and it means a rolled-back
roster run sends nothing at all, which a per-row email could not promise.
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

	``[13, 14, ..., 20, 23, 24]`` becomes ``[(13, 20), (23, 24)]`` - AC3's "continuous
	date blocks". Duplicates collapse, because two overtime rows on one date are still
	one day of the cycle.
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
		# Registered here rather than at import: a request that holds nothing should not
		# carry a hook that does nothing.
		frappe.db.after_commit.add(flush)

	pending.update(names)


def flush() -> None:
	"""Send one email per (employee, continuous cycle) for everything queued.

	Wrapped whole: the schedules are already saved and already blocking their Shift
	Assignments, so a mail server that is down must not turn a held request into a
	traceback on the roster screen.
	"""
	names = frappe.flags.pop(FLAG, None)
	if not names:
		return

	try:
		approver = frappe.db.get_single_value("Operation Settings", "dsot_approver")
		if not approver:
			# Nobody configured: the requests still stand and still block, exactly as
			# they did before this story. There is simply no one to write to.
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

		# AC4: grouped strictly by employee first, then by cycle within that employee, so
		# two people sharing a date range are two emails rather than one muddled together.
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

	AC6. A link to one schedule is the wrong destination for a request that is eight of
	them - the approver has to act on the whole cycle, and the List View is where Frappe
	offers Bulk Approve. The date filter is a ``between`` so the range itself is part of
	the link rather than something the approver has to reconstruct.
	"""
	filters = {
		"employee": employee,
		"workflow_state": PENDING_DSOT,
		"date": ["between", [str(start), str(end)]],
	}
	# Compact JSON for the operator filter: frappe.as_json pretty-prints, which pads the
	# query string with encoded newlines and indentation for no benefit in a URL.
	query = "&".join(
		f"{field}={frappe.utils.quote(json.dumps(value, separators=(',', ':')) if isinstance(value, list) else str(value))}"
		for field, value in filters.items()
	)
	return f"{get_url()}/app/employee-schedule?{query}"


def send_cycle_email(approver, employee, employee_name, start, end, shifts) -> None:
	"""One cycle, one email (AC5).

	The body copies the layout of Frappe's own Assignment Notification rather than editing
	it: that template serves every assignment in the system, and rewriting it for this one
	flow would reword the emails for leave, penalties and everything else. The approver
	reads the same shape they already act on - only the scope is a cycle, not a row.
	"""
	span = formatdate(start) if start == end else f"{formatdate(start)} to {formatdate(end)}"
	subject = _("DSOT Approval Request: {0} ({1})").format(employee_name, span)

	requestor = frappe.utils.get_fullname(frappe.session.user) or frappe.session.user

	# AC5's Document Name: the cycle is the document as far as the approver is concerned,
	# so it is named by its range and size rather than by whichever row happens to be first.
	document_name = span if start == end else _("{0} (Total: {1} Shifts)").format(span, len(shifts))

	# Built here rather than in the template for the same reason Frappe builds it in
	# notify_assignment: the sentence stays one translatable string with the bold markup
	# applied to its arguments.
	headline = _("{0} assigned a new task {1} {2} to you").format(
		frappe.bold(requestor),
		frappe.bold(_("Employee Schedule")),
		frappe.bold(document_name),
	)

	message = frappe.render_template(
		"one_fm/templates/emails/dsot_approval_request.html",
		context={
			"employee_name": employee_name,
			"employee": employee,
			"span": span,
			"shift_count": len(shifts),
			"single_day": start == end,
			"requestor": requestor,
			"headline": headline,
			"document_name": document_name,
			"list_url": pending_list_url(employee, start, end),
		},
	)

	# "Alert" is the one type Frappe never emails itself - Notification Log's after_insert
	# would otherwise send a second copy through its own template, so the approver would
	# get two emails per cycle and open the wrong one. The bell still shows it.
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
