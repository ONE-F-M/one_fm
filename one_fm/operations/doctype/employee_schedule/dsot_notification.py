# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""DSOT approval emails: urgent same-day requests at once, everything else in a daily batch.

Every Employee Schedule entering ``Pending DSOT Approval`` puts a ToDo in front of the DSOT
Approver. The per-row Assignment Notification is suppressed (the approver is named as the
assigner), so the approver is told about waiting requests by the two emails in this module,
both rendered from one shared grid (``dsot_approval_request.html``):

* **Immediate** - ``flush()`` runs when the request that held the rows commits, and emails
  only the rows whose schedule date is today, one email per employee, with an "Urgent"
  subject. Waiting for the next morning would be too late for those shifts. Collecting the
  names as they are held and flushing on commit also means a rolled-back roster run sends
  nothing at all.
* **Batch** - ``send_daily_dsot_digest()`` runs at 00:05 and sends ONE email listing every
  pending overtime row that was not raised for its own day (``date != DATE(creation)``),
  every day until the row is decided. Nothing is sent when there are none.

Each row in either email has Approve and Reject buttons, and the header has Approve All and
Reject All. The buttons open ``confirm_email_action`` - a signed page that changes nothing
and shows what would be decided - and its Confirm button opens ``apply_email_action``, the
signed GET endpoint that runs the workflow action. Approve means the workflow's existing
Active state; Reject means Rejected. The digest's bulk buttons sign a creation cutoff
rather than a list of names, so rows raised after the email was built are never swept in.

The outcome email is the other half: once the approver has decided, the REQUESTOR is told
which days were approved and which were rejected, in one email per request. Approvers
decide one row per commit (the form saves one row, and Frappe's bulk workflow action
commits after each row), so the commit cannot group a request. Each row carries the
dsot_request it was held under instead, and the email waits until no row of that request
is still pending.
"""

import json

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	escape_html,
	formatdate,
	get_datetime,
	get_url,
	getdate,
	now_datetime,
	today,
)
from frappe.utils.jinja import get_template
from frappe.utils.verified_command import get_signed_params, verify_request
from pypika import functions as fn

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
	"""Send one urgent email per employee for the queued rows that are dated today.

	Rows for any other date are not emailed here; they wait for the daily digest.

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
			fields=[
				"name",
				"employee",
				"employee_name",
				"date",
				"shift",
				"shift_type",
				"start_datetime",
				"end_datetime",
			],
		)
		# Immediate means the schedule date is today at hold time; the rest is the
		# digest's job.
		rows = [row for row in rows if getdate(row.date) == getdate(today())]
		if not rows:
			return

		by_employee = {}
		for row in rows:
			by_employee.setdefault((row.employee, row.employee_name), []).append(row)

		# One email per employee, so two people held in one roster run are two emails
		# rather than one muddled together.
		for (employee, employee_name), employee_rows in by_employee.items():
			send_urgent_email(approver, employee, employee_name or employee, employee_rows)
	except Exception:
		frappe.log_error(
			title="DSOT consolidated notification",
			message=frappe.get_traceback(),
		)


APPROVAL_TEMPLATE = "one_fm/templates/emails/dsot_approval_request.html"
EMAIL_ACTIONS = ("Approve", "Reject")
ENDPOINT = "one_fm.operations.doctype.employee_schedule.dsot_notification"
SAVEPOINT = "dsot_email_action"


def signed_action_url(method, **params) -> str:
	"""A signed link to one of the two email-action endpoints.

	The signature covers every parameter, so the action, the user it runs as and the rows
	(or the digest cutoff) cannot be changed by whoever holds the link.
	"""
	params = {key: value for key, value in params.items() if value}
	return f"{get_url()}/api/method/{ENDPOINT}.{method}?{get_signed_params(params)}"


def shift_label(row) -> str:
	"""A shift as the approver reads it: the Operations Shift, and its Shift Type."""
	shift = row.get("shift")
	shift_type = row.get("shift_type")
	if shift and shift_type:
		return f"{shift} ({shift_type})"
	return shift or shift_type or ""


def dsot_label(row) -> str:
	"""The overtime shift with its hours, read from the datetimes (a 00:00 Time is falsy)."""
	label = row.get("shift") or row.get("shift_type") or ""
	start, end = row.get("start_datetime"), row.get("end_datetime")
	if start and end:
		label = "{0} ({1} - {2})".format(
			label, get_datetime(start).strftime("%H:%M"), get_datetime(end).strftime("%H:%M")
		)
	return label.strip()


def basic_shifts(schedules) -> dict:
	"""(employee, date) -> the Basic shift worked that day, in one query for the whole grid."""
	from one_fm.operations.doctype.employee_schedule.employee_schedule import BASIC, WORKING

	if not schedules:
		return {}

	return {
		(row.employee, getdate(row.date)): shift_label(row)
		for row in frappe.get_all(
			"Employee Schedule",
			filters={
				"roster_type": BASIC,
				"employee_availability": WORKING,
				"employee": ["in", list({s.employee for s in schedules})],
				"date": ["in", list({s.date for s in schedules})],
			},
			fields=["employee", "date", "shift", "shift_type"],
		)
	}


def build_email_rows(approver, schedules) -> list:
	"""The grid rows for the shared template, each with its own signed Approve/Reject links."""
	basic = basic_shifts(schedules)
	return [
		frappe._dict(
			date=schedule.date,
			date_label=formatdate(schedule.date),
			employee=schedule.employee,
			employee_name=schedule.employee_name,
			basic_shift=basic.get((schedule.employee, getdate(schedule.date))),
			dsot_shift=dsot_label(schedule),
			approve_url=signed_action_url(
				"confirm_email_action", action="Approve", user=approver, names=schedule.name
			),
			reject_url=signed_action_url(
				"confirm_email_action", action="Reject", user=approver, names=schedule.name
			),
		)
		for schedule in schedules
	]


def render_approval_request(approver, schedules, intro, **bulk) -> str:
	"""Render the shared grid. ``bulk`` is what Approve All / Reject All sign."""
	return get_template(APPROVAL_TEMPLATE).render(
		{
			"intro": intro,
			"rows": build_email_rows(approver, schedules),
			"approve_all_url": signed_action_url(
				"confirm_email_action", action="Approve", user=approver, **bulk
			),
			"reject_all_url": signed_action_url(
				"confirm_email_action", action="Reject", user=approver, **bulk
			),
		}
	)


def send_urgent_email(approver, employee, employee_name, schedules) -> None:
	"""One employee's same-day requests, emailed at once."""
	subject = _("Urgent DSOT Approval Request: {0} ({1})").format(
		employee_name, formatdate(today())
	)
	intro = _("Double shift overtime for {0} ({1}) is for today and needs a decision now.").format(
		employee_name, employee
	)
	message = render_approval_request(
		approver,
		schedules,
		intro,
		# Only the rows in this email: they are dated today, so the digest's cutoff rule
		# (date != DATE(creation)) would not select them.
		names=",".join(schedule.name for schedule in schedules),
	)

	sendemail(
		recipients=[approver],
		subject=subject,
		content=message,
		reference_doctype="Employee Schedule",
		reference_name=schedules[0].name,
		is_scheduler_email=True,
	)


def pending_overtime_rows(cutoff=None) -> list:
	"""Pending overtime requests that were not raised for their own day, oldest date last.

	These are the rows no immediate email covered. ``cutoff`` limits them to rows created
	by then, which is what lets a digest's bulk buttons mean "what this email listed".
	"""
	from one_fm.operations.doctype.employee_schedule.employee_schedule import OVERTIME

	schedule = frappe.qb.DocType("Employee Schedule")
	query = (
		frappe.qb.from_(schedule)
		.select(
			schedule.name,
			schedule.employee,
			schedule.employee_name,
			schedule.date,
			schedule.shift,
			schedule.shift_type,
			schedule.start_datetime,
			schedule.end_datetime,
		)
		.where(schedule.workflow_state == PENDING_DSOT)
		.where(schedule.roster_type == OVERTIME)
		.where(fn.Date(schedule.creation) != schedule.date)
	)
	if cutoff:
		query = query.where(schedule.creation <= cutoff)

	rows = query.orderby(schedule.employee).orderby(schedule.date).run(as_dict=True)
	return [frappe._dict(row) for row in rows]


def send_daily_dsot_digest() -> None:
	"""Email the approver ONE list of every pending overtime request not mailed at once.

	Runs daily at 00:05. A row stays in the list each day until it is decided.
	"""
	approver = frappe.db.get_single_value("Operation Settings", "dsot_approver")
	if not approver:
		return

	cutoff = str(now_datetime())
	rows = pending_overtime_rows(cutoff)
	if not rows:
		return

	try:
		subject = _("DSOT Approval Request: {0} Pending Overtime Requests").format(len(rows))
		intro = _("{0} overtime requests are waiting for your decision.").format(len(rows))
		message = render_approval_request(approver, rows, intro, digest_cutoff=cutoff)

		sendemail(
			recipients=[approver],
			subject=subject,
			content=message,
			reference_doctype="Employee Schedule",
			reference_name=rows[0].name,
			is_scheduler_email=True,
		)
	except Exception:
		frappe.log_error(title="DSOT daily digest", message=frappe.get_traceback())


def selected_schedules(names=None, digest_cutoff=None) -> list:
	"""The rows a signed link stands for: the digest's cutoff set, or the names it carries."""
	if digest_cutoff:
		return [row.name for row in pending_overtime_rows(digest_cutoff)]
	return [name for name in (names or "").split(",") if name]


def respond_email_action_page(title, html, indicator_color="blue", **kwargs) -> None:
	frappe.respond_as_web_page(title, html, indicator_color=indicator_color, **kwargs)


def is_valid_email_action(action, user) -> bool:
	"""A signed link, for a known action, on behalf of somebody."""
	if not verify_request():
		respond_email_action_page(
			_("Invalid Link"),
			_("This link is invalid or has been changed."),
			"red",
			http_status_code=403,
		)
		return False

	if action not in EMAIL_ACTIONS or not user:
		respond_email_action_page(
			_("Invalid Action"), _("Only Approve or Reject is allowed."), "red", http_status_code=400
		)
		return False

	return True


# Guest access is the point: the approver opens this from an email. The signature checked in
# is_valid_email_action is the guard, and this page writes nothing.
@frappe.whitelist(allow_guest=True, methods=["GET"])  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def confirm_email_action(
	action: str | None = None,
	user: str | None = None,
	names: str | None = None,
	digest_cutoff: str | None = None,
):
	"""The page the email buttons open. Changes nothing.

	Mail clients and security scanners open links to preview them, so the link in the email
	must not decide anything; the single Confirm button here is what does.
	"""
	if not is_valid_email_action(action, user):
		return

	selected = selected_schedules(names, digest_cutoff)
	rows = (
		frappe.get_all(
			"Employee Schedule",
			filters={"name": ["in", selected], "workflow_state": PENDING_DSOT},
			fields=[
				"name",
				"employee",
				"employee_name",
				"date",
				"shift",
				"shift_type",
				"start_datetime",
				"end_datetime",
			],
			order_by="employee asc, date asc",
		)
		if selected
		else []
	)

	if not rows:
		respond_email_action_page(
			_("Nothing to Decide"), _("There are no pending requests left for this link."), "orange"
		)
		return

	basic = basic_shifts(rows)
	body = "".join(
		"<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td></tr>".format(
			escape_html(formatdate(row.date)),
			escape_html(row.employee),
			escape_html(row.employee_name or row.employee),
			escape_html(basic.get((row.employee, getdate(row.date))) or "-"),
			escape_html(dsot_label(row) or "-"),
		)
		for row in rows
	)
	html = (
		"<p>{0}</p><table class='table table-bordered'><thead><tr><th>{1}</th><th>{2}</th>"
		"<th>{3}</th><th>{4}</th><th>{5}</th></tr></thead><tbody>{6}</tbody></table>"
	).format(
		escape_html(
			_("{0} request(s) will be {1}.").format(
				len(rows), _("approved") if action == "Approve" else _("rejected")
			)
		),
		_("Date"),
		_("Employee ID"),
		_("Employee Name"),
		_("Basic (Shift Name)"),
		_("DSOT (Shift Name)"),
		body,
	)

	respond_email_action_page(
		_("Confirm {0}").format(_(action)),
		html,
		"green" if action == "Approve" else "red",
		primary_action=signed_action_url(
			"apply_email_action",
			action=action,
			user=user,
			names=names,
			digest_cutoff=digest_cutoff,
		),
		primary_label=_("Confirm"),
	)


# Guest access is the point: the approver confirms from an email without logging in. The
# signature is checked first, may_decide_dsot gates the signed user, and a decided row is skipped.
@frappe.whitelist(allow_guest=True, methods=["GET"])  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def apply_email_action(
	action: str | None = None,
	user: str | None = None,
	names: str | None = None,
	digest_cutoff: str | None = None,
):
	"""Approve or Reject the rows a signed link stands for, as the approver it was signed for.

	Approve is the workflow's own Approve action, so the row lands on Active. Each row has its
	own savepoint so one failure undoes only itself; everything else is committed once.
	"""
	if not is_valid_email_action(action, user):
		return

	from one_fm.operations.doctype.employee_schedule.employee_schedule import may_decide_dsot
	from one_fm.overrides.workflow import apply_workflow

	approved = rejected = skipped = 0
	allowed = True

	# A logged-in browser session is used as-is; only a Guest acts as the signed user.
	switched = frappe.session.user == "Guest"
	if switched:
		# The user is part of the signed parameters, so the link cannot be re-pointed.
		frappe.set_user(user)  # nosemgrep: frappe-semgrep-rules.rules.security.frappe-setuser
	try:
		allowed = may_decide_dsot()
		if allowed:
			for name in selected_schedules(names, digest_cutoff):
				state = frappe.db.get_value("Employee Schedule", name, "workflow_state")
				if state != PENDING_DSOT:
					# Missing, or already decided by somebody else.
					skipped += 1
					continue

				frappe.db.savepoint(SAVEPOINT)
				messages_before = len(frappe.message_log)
				try:
					result = apply_workflow(frappe.get_doc("Employee Schedule", name), action)
				except Exception:
					frappe.db.rollback(save_point=SAVEPOINT)
					frappe.log_error(
						title=f"DSOT email action failed: {name}", message=frappe.get_traceback()
					)
					skipped += 1
					continue
				finally:
					# A refusal is reported on the page below, not as a popup message.
					del frappe.message_log[messages_before:]

				if isinstance(result, dict):
					# The workflow said the action is no longer valid for this row.
					skipped += 1
				elif action == "Approve":
					approved += 1
				else:
					rejected += 1

			# A GET is never committed by Frappe, and verify_request accepts only a GET. The
			# email link itself opens confirm_email_action, so a prefetch decides nothing.
			frappe.db.commit()  # nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit, frappe-semgrep-rules.rules.security.whitelisted-side-effect-on-get
	finally:
		if switched:
			frappe.set_user("Guest")  # nosemgrep: frappe-semgrep-rules.rules.security.frappe-setuser

	if not allowed:
		respond_email_action_page(
			_("Not Allowed"),
			_("Only the DSOT Approver or the Operation Manager named in Operation Settings can decide this request."),
			"red",
			http_status_code=403,
		)
		return

	respond_email_action_page(
		_("DSOT Requests Updated"),
		"<p>{0}</p><p>{1}</p><p>{2}</p>".format(
			_("Approved: {0}").format(approved),
			_("Rejected: {0}").format(rejected),
			_("Skipped: {0}").format(skipped),
		),
		"green",
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

	The body is one_fm's existing notification table - the same one every assignment email
	on this site already arrives in - so the approver reads the shape they act on daily.
	Frappe's shared Assignment Notification is still not edited: that template serves every
	assignment in the system, and rewording it for this one flow would change the emails
	for leave, penalties and everything else. Only the scope differs here: the row is a
	cycle, and the link opens the pending range rather than one schedule.
	"""
	span = formatdate(start) if start == end else f"{formatdate(start)} to {formatdate(end)}"
	subject = _("DSOT Approval Request: {0} ({1})").format(employee_name, span)

	list_url = pending_list_url(employee, start, end)
	requestor = frappe.utils.get_fullname(frappe.session.user) or frappe.session.user

	# AC5's Document Name: the cycle is the document as far as the approver is concerned,
	# so it is named by its range and size rather than by whichever row happens to be first.
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

	# Worded like Frappe's own assignment sentence, and built here for the same reason it
	# builds it in notify_assignment: the sentence stays one translatable string with the
	# bold markup applied to its arguments.
	body_content = _("{0} assigned a new task {1} {2} to you").format(
		frappe.bold(requestor),
		frappe.bold(_("Employee Schedule")),
		frappe.bold(document_name),
	)

	# one_fm already renders every Notification Log email as this table
	# (one_fm/overrides/notification_log.py). Reusing it rather than carrying a second
	# layout is what makes a DSOT request read like every other assignment the approver
	# gets - and means a future change to that table reaches this email too.
	message = frappe.render_template(
		"one_fm/templates/emails/notification_log.html",
		context={
			"header": _("DSOT Approval Request on {0}").format(span),
			"document_name": document_name,
			"document_type": _("Employee Schedule"),
			"description": description,
			"body_content": body_content,
			# An anchor rather than the bare URL the single-document path passes: the
			# filtered link carries encoded JSON, which mail clients autolink badly.
			"doc_link": f'<a href="{list_url}">{list_url}</a>',
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
