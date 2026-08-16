import frappe


def execute():
	"""One-time trigger: send the Work Item "Notify Assignee" demo email
	(with a real action button, not a plain link) from
	notifications@one-fm.com to both AMP verification addresses
	(Gmail's ampforemail.whitelisting@gmail.com and Yahoo's
	ampverification@yahoo.com), through the actual production sending
	pipeline.

	This runs automatically, once, the first time `bench migrate` executes
	on any site with this patch present (Frappe's Patch Log ensures it
	never re-runs after that) — including production, which is the whole
	point: the SMTP connection needs to originate from production's
	registered IP for Google Workspace's SMTP relay to accept it, and
	`bench migrate` is the one thing guaranteed to execute there. See
	`one_fm.patches.v15_0.send_amp_verification_test_email` for the
	original precedent this follows.

	Deliberately does not raise — a transient email/SMTP failure must
	never block or fail a production migration. Check the Email Queue
	for the actual outcome instead.
	"""
	try:
		from one_fm.api.amp_verification import send_amp_verification_email

		send_amp_verification_email()
	except Exception:
		frappe.log_error(
			title="Work Item notify-assignee demo email failed",
			message=frappe.get_traceback(),
		)
