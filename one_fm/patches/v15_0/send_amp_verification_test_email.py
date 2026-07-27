import frappe


def execute():
	"""One-time trigger: send a real AMP-for-Email test message from
	notifications@one-fm.com to s.shariff@one-fm.com through the actual
	production sending pipeline, to verify DKIM/SPF/DMARC alignment ahead
	of the Google AMP sender registration submission.

	This runs automatically, once, the first time `bench migrate` executes
	on any site with this patch present (Frappe's Patch Log ensures it
	never re-runs after that) — including production, which is the whole
	point: the SMTP connection needs to originate from production's
	registered IP for Google Workspace's SMTP relay to accept it, and
	`bench migrate` is the one thing guaranteed to execute there.

	Deliberately does not raise — a transient email/SMTP failure must
	never block or fail a production migration. Check the "amp_verification"
	logger (or the returned Email Queue row) for the actual outcome instead.
	"""
	try:
		from one_fm.api.amp_verification import send_amp_verification_email

		result = send_amp_verification_email()
		frappe.logger("amp_verification").info(f"Patch send result: {result}")
	except Exception:
		frappe.log_error(
			title="AMP verification test email failed",
			message=frappe.get_traceback(),
		)
