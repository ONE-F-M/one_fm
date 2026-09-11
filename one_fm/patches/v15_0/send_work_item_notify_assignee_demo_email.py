import frappe
from frappe import _

SENDER = "notifications@one-fm.com"
# AMP for Email sender-registration addresses (per
# https://amp.dev/documentation/guides-and-tutorials/start/email_sender_distribution)
# — Gmail and Yahoo/Verizon Media require a production-ready AMP email sent
# directly to these addresses as part of allowlisting one-fm.com as a sender.
# Self-test run: deliver to our own inbox only. Restore the registration
# addresses once the Gmail developer-settings check passes.
RECIPIENTS = [
	"notifications@one-fm.com",
	# "ampforemail.whitelisting@gmail.com",
	# "ampverification@yahoo.com",
]

# Real, live Work Item whose "Start Work" user task is waiting in its BPMN
# Process Instance. The instance and task id are looked up at run time from
# `BPMN Active Task` so the token always matches the live task.
WORK_ITEM_ID = "WI-002492"
TASK_NAME = "Start Work"

# The task's real assignee — the token must be issued for this user (not
# RECIPIENTS) since handle_amp_action checks it against the task's actual
# assignment. RECIPIENTS is only where this AMP submission is delivered for
# Gmail's/Yahoo's allowlisting review — not who's expected to click it.
ASSIGNEE_USER = "k.sharma@one-fm.com"


def execute():
	"""One-time trigger: send a real "Start Work" notification email — tied
	to the actual live BPMN task for WORK_ITEM_ID — from
	notifications@one-fm.com to RECIPIENTS, through the actual production
	sending pipeline.

	The email's "Start Work" action is a genuine one-click AMP action tied
	to a real, live BPMN Process Instance task. The token is generated the
	same way the engine itself would
	(`one_bpmn.utils.token.generate_action_token`, keyed on `instance_name`
	+ `task_id`). Clicking the button calls `complete_task` on the real
	Process Instance, genuinely advancing it — a deliberate, confirmed side
	effect for this specific task, for whoever actually clicks it.

	This runs automatically, once, the first time `bench migrate` executes
	on any site with this patch present (Frappe's Patch Log ensures it
	never re-runs after that). Bump the date comment in patches.txt to
	re-run it.

	Deliberately does not raise — a transient email/SMTP failure must
	never block or fail a production migration. Check the Email Queue
	for the actual outcome instead.
	"""
	try:
		send()
	except Exception:
		frappe.log_error(
			title=f"{WORK_ITEM_ID} Start Work AMP notify failed",
			message=frappe.get_traceback(),
		)


def _find_live_task() -> tuple[str, str]:
	"""Return (instance_name, task_id) of the waiting TASK_NAME task for WORK_ITEM_ID."""
	instances = frappe.get_all(
		"BPMN Process Instance",
		filters={"context_doctype": "Work Item", "context_docname": WORK_ITEM_ID},
		pluck="name",
	)
	if not instances:
		frappe.throw(
			_("No BPMN Process Instance found for Work Item {0}.").format(WORK_ITEM_ID),
			frappe.ValidationError,
		)

	task = frappe.get_all(
		"BPMN Active Task",
		filters={
			"parent": ["in", instances],
			"task_name": TASK_NAME,
			"status": "Waiting",
		},
		fields=["parent", "task_id"],
		limit=1,
	)
	if not task:
		frappe.throw(
			_("No waiting '{0}' task found for Work Item {1} (instances: {2}).").format(
				TASK_NAME, WORK_ITEM_ID, ", ".join(instances)
			),
			frappe.ValidationError,
		)
	return task[0].parent, task[0].task_id


def _yes_no(value) -> str:
	return "Yes" if frappe.utils.cint(value) else "No"


def send():
	account_name = frappe.db.get_value("Email Account", {"email_id": SENDER}, "name")
	if not account_name:
		frappe.throw(
			_("No Email Account found for {0}.").format(SENDER),
			frappe.ValidationError,
		)
	if not frappe.db.get_value("Email Account", account_name, "enable_outgoing"):
		frappe.throw(
			_("Email Account '{0}' ({1}) has outgoing mail disabled.").format(
				account_name, SENDER
			),
			frappe.ValidationError,
		)

	from one_bpmn.email_builder.renderer import render_amp, render_html_fallback
	from one_bpmn.email_builder.email_actions import build_email_actions

	instance_name, task_id = _find_live_task()
	wi = frappe.get_doc("Work Item", WORK_ITEM_ID)
	epic_title = frappe.db.get_value("Work Item", wi.epic, "title") if wi.epic else ""

	work_item_url = f"https://one-fm.com/app/work-item/{WORK_ITEM_ID}"
	title = f"[{WORK_ITEM_ID}] Assigned to you: {wi.title} ({wi.priority} priority)"
	sprint = f"{wi.sprint} ({wi.sprint_status})" if wi.sprint_status else (wi.sprint or "")

	body = f"""
<p>Hi,</p>
<p>A work item has been assigned to you and is ready to start.</p>
<table cellpadding="6" border="0">
<tbody>
<tr><td><b>Work Item</b></td><td>{WORK_ITEM_ID} &mdash; {frappe.utils.escape_html(wi.title)}</td></tr>
<tr><td><b>Type</b></td><td>{wi.work_item_type or ""}</td></tr>
<tr><td><b>Priority</b></td><td>{wi.priority or ""}</td></tr>
<tr><td><b>Sprint</b></td><td>{sprint}</td></tr>
<tr><td><b>Story Points</b></td><td>{frappe.utils.flt(wi.story_points):g}</td></tr>
<tr><td><b>Epic</b></td><td>{frappe.utils.escape_html(epic_title or wi.epic or "")}</td></tr>
<tr><td><b>Reported By</b></td><td><a href="mailto:{wi.reporter_user}">{wi.reporter_user}</a></td></tr>
<tr><td><b>PR Required</b></td><td>{_yes_no(wi.pr_required)}</td></tr>
<tr><td><b>Research Required</b></td><td>{_yes_no(wi.research_required)}</td></tr>
</tbody>
</table>
<p><b>Description</b></p>
{wi.description or ""}
""".strip()

	# Real BPMN-instance-tied token — the same mechanism
	# compose_and_send_task_email uses for every other task action.
	actions = build_email_actions(
		instance_name=instance_name,
		task_id=task_id,
		actions=[{"label": TASK_NAME, "primary": True}],
		user=ASSIGNEE_USER,
	)

	task_content = {
		"subject": title,
		"body": body,
		"actions": actions,
		"open_link": work_item_url,
		"doctype": "Work Item",
		"name": WORK_ITEM_ID,
	}
	amp_html = render_amp(task_content)
	html_body = render_html_fallback(task_content)

	frappe.flags.amp_html = amp_html
	frappe.sendmail(
		recipients=RECIPIENTS,
		sender=SENDER,
		subject=title,
		message=html_body,
		now=True,
	)
	frappe.db.commit()
