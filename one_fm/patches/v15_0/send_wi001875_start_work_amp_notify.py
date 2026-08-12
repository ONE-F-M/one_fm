import frappe


def execute():
	"""One-time trigger: send a real "Start Work" AMP notification — tied to
	the actual live BPMN task for WI-001875 (instance c57ogcqvmu, task
	1c9b34b8-019e-4402-bd74-75905d15b0f6, currently READY) — from
	notifications@one-fm.com to the real assignee (s.shariff@one-fm.com),
	through the actual production sending pipeline.

	This is a genuine, correctly-authorized one-click action (using
	one_bpmn.utils.token.generate_action_token, tied to the real Process
	Instance + task, processed by handle_amp_action) — not the earlier
	static-registry workaround. Clicking "Start Work" in the resulting
	email will genuinely advance this specific Process Instance.

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
		from one_fm.api.amp_verification import send_amp_verification_email

		send_amp_verification_email(recipients="s.shariff@one-fm.com")
	except Exception:
		frappe.log_error(
			title="WI-001875 Start Work AMP notify failed",
			message=frappe.get_traceback(),
		)
