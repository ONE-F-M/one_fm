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

	Already executed on production (Patch Log ensures it never re-runs) —
	this function body is retained only for historical reference. The
	``one_fm.api.amp_verification`` module it originally called has since
	been removed; its logic now lives inline in the newer
	``send_work_item_notify_assignee_demo_email`` patch, which follows the
	same "trigger via bench migrate on production" pattern for a different
	verification send.
	"""
	pass
