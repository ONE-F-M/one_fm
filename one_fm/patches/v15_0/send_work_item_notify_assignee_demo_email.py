import frappe
from frappe import _

SENDER = "notifications@one-fm.com"
RECIPIENT = "s.shariff@one-fm.com"

# Real, live BPMN Process Instance task for WI-001875's "Start Work" step —
# not a synthetic demo. Must be in READY (16) or WAITING (8) state at the
# time this runs; look these up fresh from the BPMN Process Instance's
# `workflow_state` (not the older, possibly-stale `serialized_spec`) if
# reusing this pattern for a different task.
INSTANCE_NAME = "c57ogcqvmu"
TASK_ID = "1c9b34b8-019e-4402-bd74-75905d15b0f6"
WORK_ITEM_ID = "WI-001875"
WORK_ITEM_TITLE = "1.2 Skills index in the static context and on-trigger body loading"


def execute():
	"""One-time trigger: send a real "Start Work" notification email — tied
	to the actual live BPMN task for WI-001875 — from
	notifications@one-fm.com to the real assignee (s.shariff@one-fm.com),
	through the actual production sending pipeline.

	The email's "Start Work" action is a genuine one-click AMP action tied
	to a real, live BPMN Process Instance task — not a static registry
	entry. Work Item's "Start Work" step is a `userTask` inside the
	"Software Development v3" BPMN process (see
	`one_bpmn.api.bpmn_task_actions.handle_amp_action`), so the token is
	generated the same way the engine itself would
	(`one_bpmn.utils.token.generate_action_token`, keyed on `instance_name`
	+ `task_id`) — not `generate_doc_action_token` + the
	`amp_workflow_actions` static allowlist, which is reserved for
	documents with no BPMN engine behind them at all. Clicking the button
	calls `complete_task` on the real Process Instance, genuinely advancing
	it — a deliberate, confirmed side effect for this specific task.

	This runs automatically, once, the first time `bench migrate` executes
	on any site with this patch present (Frappe's Patch Log ensures it
	never re-runs after that) — including production, which is the whole
	point: the SMTP connection needs to originate from production's
	registered IP for Google Workspace's SMTP relay to accept it, and
	`bench migrate` is the one thing guaranteed to execute there.

	Deliberately does not raise — a transient email/SMTP failure must
	never block or fail a production migration. Check the Email Queue
	for the actual outcome instead.
	"""
	try:
		send()
	except Exception:
		frappe.log_error(
			title="WI-001875 Start Work AMP notify failed",
			message=frappe.get_traceback(),
		)


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

	work_item_url = f"https://one-fm.com/app/work-item/{WORK_ITEM_ID}"
	title = f"[{WORK_ITEM_ID}] Assigned to you: {WORK_ITEM_TITLE} (Medium priority)"

	body = f"""
<p style="margin:1em 0!important">Hi,</p>
<p style="margin:1em 0!important">A work item has been assigned to you and is ready to start.</p>
<table cellpadding="6" border="0">
<tbody>
<tr><td><b>Work Item</b></td><td>{WORK_ITEM_ID} &mdash; {WORK_ITEM_TITLE}</td></tr>
<tr><td><b>Type</b></td><td>User Story</td></tr>
<tr><td><b>Priority</b></td><td>Medium</td></tr>
<tr><td><b>Sprint</b></td><td>AI-017 (Active)</td></tr>
<tr><td><b>Story Points</b></td><td>5</td></tr>
<tr><td><b>Epic</b></td><td>Agent Skills</td></tr>
<tr><td><b>Reported By</b></td><td><a href="mailto:k.sharma@one-fm.com">k.sharma@one-fm.com</a></td></tr>
<tr><td><b>PR Required</b></td><td>Yes</td></tr>
<tr><td><b>Research Required</b></td><td>No</td></tr>
</tbody>
</table>
<p style="margin:1em 0!important"><b>Description</b><br></p>
<p style="margin:0!important">Add skills-index rendering in context_assembler.build_static_context and active-skill tracking in the dispatcher's dynamic-preamble path.</p>
""".strip()

	# Real BPMN-instance-tied token — the same mechanism
	# compose_andsend_task_email uses for every other task action.
	actions = build_email_actions(
		instance_name=INSTANCE_NAME,
		task_id=TASK_ID,
		actions=[{"label": "Start Work", "primary": True}],
		user=RECIPIENT,
	)

	task_content = {
		"subject": title,
		"body": body,
		"actions": actions,
		"open_link": work_item_url,
		"doctype": "Work Item",
		"name": WORK_ITEM_ID,
		"action_endpoint": "https://one-fm.com/api/method/one_bpmn.api.bpmn_task_actions.handle_amp_action",
	}
	amp_html = render_amp(task_content)
	html_body = render_html_fallback(task_content)

	frappe.flags.amp_html = amp_html
	email_queue = frappe.sendmail(
		recipients=[RECIPIENT],
		sender=SENDER,
		subject=title,
		message=html_body,
		now=True,
	)
	frappe.db.commit()
