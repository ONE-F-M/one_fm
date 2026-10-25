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


# The approver is told a request is waiting (above); the requestor is told what was
# decided - and for a range that was decided unevenly, exactly which days went which way.
OUTCOME_FLAG = "dsot_outcome_notifications"

ACTIVE = "Active"
REJECTED = "Rejected"

# The two states a decided request lands in, and what each is called in the email. Approve
# transitions to Active rather than to an "Approved" state of its own: only an
# Active schedule is picked up for a Shift Assignment.
DECIDED_STATES = (ACTIVE, REJECTED)

# Who the email says processed the request when nobody did. reject_expired_dsot_requests
# closes a request whose shift has already finished, under Administrator, because no
# approver ever answered it.
SYSTEM_PROCESSOR = "Administrator"


def queue_outcome(names) -> None:
	"""Remember decided schedules, and tell their requestors once this request commits.

	Separate from queue(): a roster run can hold new requests and decide old ones in the
	same transaction, and the two emails go to different people about different shifts.
	"""
	names = [name for name in (names or []) if name]
	if not names:
		return

	pending = frappe.flags.get(OUTCOME_FLAG)
	if pending is None:
		pending = frappe.flags[OUTCOME_FLAG] = set()
		frappe.db.after_commit.add(flush_outcomes)

	pending.update(names)


def flush_outcomes() -> None:
	"""Send one outcome email per request whose last pending row has now been decided.

	Wrapped whole for the same reason as flush(): the decision has already saved and the
	shift assignment has already been made, so a mail server that is down must not turn an
	approval into a traceback on the approver's screen.
	"""
	names = frappe.flags.pop(OUTCOME_FLAG, None)
	if not names:
		return

	try:
		decided = frappe.get_all(
			"Employee Schedule",
			filters={"name": ["in", list(names)]},
			fields=["name", "dsot_request"],
		)
		# Rows held before dsot_request existed have none, and stand as a request of one.
		requests = {
			("dsot_request", row.dsot_request) if row.dsot_request else ("name", row.name)
			for row in decided
		}

		for field, value in requests:
			rows = frappe.get_all(
				"Employee Schedule",
				filters={field: value},
				fields=[
					"name",
					"employee",
					"employee_name",
					"date",
					"site",
					"owner",
					"workflow_state",
					"modified_by",
				],
			)
			# ponytail: two approvers committing the last two rows of one request at the
			# same moment each see the other still pending, and neither sends.
			if any(row.workflow_state == PENDING_DSOT for row in rows):
				continue

			outcome = [row for row in rows if row.workflow_state in DECIDED_STATES]
			if outcome:
				send_outcome_email(
					requestor=outcome[0].owner, employee=outcome[0].employee, decided=outcome
				)
	except Exception:
		frappe.log_error(
			title="DSOT outcome notification",
			message=frappe.get_traceback(),
		)


def format_cycles(dates) -> str:
	"""AC3's date blocks, written the way the template shows them.

	A single day is that day; a run is "first - last"; several runs are comma separated.
	"None (0 shifts)" is what an empty side says, rather than an empty cell the reader has
	to interpret.
	"""
	cycles = continuous_cycles(dates)
	if not cycles:
		return _("None (0 shifts)")

	return ", ".join(
		formatdate(start) if start == end else f"{formatdate(start)} - {formatdate(end)}"
		for start, end in cycles
	)


def schedule_list_url(employee, dates) -> str:
	"""The requestor's landing place: this employee's schedules over the range decided.

	Not filtered on state: the point of the link is to see the approved and the rejected
	days together, which is the whole of what the email is about.
	"""
	span = sorted(getdate(date) for date in dates if date)
	filters = {
		"employee": employee,
		"date": ["between", [str(span[0]), str(span[-1])]],
	}
	query = "&".join(
		f"{field}={frappe.utils.quote(json.dumps(value, separators=(',', ':')) if isinstance(value, list) else str(value))}"
		for field, value in filters.items()
	)
	return f"{get_url()}/app/employee-schedule?{query}"


def processed_by(decided) -> str:
	"""Who decided it, or that nobody did.

	An expired request is closed by the hourly job under Administrator - nobody answered
	it - and the email says so rather than naming a person who never saw it.
	"""
	actors = {row.modified_by for row in decided} - {None, ""}
	if actors == {SYSTEM_PROCESSOR}:
		return _("System Administrator (auto-expired)")

	named = sorted(actors - {SYSTEM_PROCESSOR})
	return ", ".join(frappe.utils.get_fullname(actor) or actor for actor in named) or _(
		"System Administrator (auto-expired)"
	)


def send_outcome_email(requestor, employee, decided) -> None:
	"""One request, one email."""
	if not requestor:
		return

	approved = [row.date for row in decided if row.workflow_state == ACTIVE]
	rejected = [row.date for row in decided if row.workflow_state == REJECTED]
	all_dates = [row.date for row in decided]

	employee_name = next((row.employee_name for row in decided if row.employee_name), employee)
	site = next((row.site for row in decided if row.site), None)

	overall = continuous_cycles(all_dates)
	span = (
		f"{formatdate(overall[0][0])} - {formatdate(overall[-1][1])}"
		if overall and overall[0][0] != overall[-1][1]
		else formatdate(overall[0][0])
		if overall
		else ""
	)

	subject = _("DSOT Request Outcome: {0} ({1})").format(employee_name, span)
	list_url = schedule_list_url(employee, all_dates)

	# The same table every other one_fm notification arrives in
	# (one_fm/overrides/notification_log.py), so the requestor reads the shape they act on
	# daily. The decision itself is the description; the date blocks are the body.
	description = _("Employee: {0} ({1}).").format(employee_name, employee)
	if site:
		description += " " + _("Operations Site: {0}.").format(site)

	body_content = "<br>".join([
		_("Approved Dates: {0}").format(frappe.bold(format_cycles(approved))),
		_("Rejected Dates: {0}").format(frappe.bold(format_cycles(rejected))),
		_("Processed By: {0}").format(frappe.bold(processed_by(decided))),
	])

	message = frappe.render_template(
		"one_fm/templates/emails/notification_log.html",
		context={
			"header": _("DSOT Process Decision Notification"),
			"document_name": span,
			"document_type": _("Employee Schedule"),
			"description": description,
			"body_content": body_content,
			"doc_link": f'<a href="{list_url}">{list_url}</a>',
		},
	)

	# "Alert" is the one type Frappe never emails itself, so the requestor gets the bell
	# entry and exactly one email rather than two copies through two templates.
	frappe.get_doc({
		"doctype": "Notification Log",
		"type": "Alert",
		"subject": subject,
		"email_content": message,
		"document_type": "Employee Schedule",
		"document_name": decided[0].name,
		"for_user": requestor,
	}).insert(ignore_permissions=True)

	sendemail(
		recipients=[requestor],
		subject=subject,
		content=message,
		reference_doctype="Employee Schedule",
		reference_name=decided[0].name,
		is_scheduler_email=True,
	)
