import frappe


def execute():
	"""Disable the Roster Double Shift OT Checker assignment rules left on the site.

	WI-001689 was reverted, but sites where its registration patch already ran still
	carry the Assignment Rule documents. Their document type no longer exists, so the
	rules can only error; disable them by document_type to catch either fixture name
	("Roster Roster Double Shift OT Checker - Project Manager" and
	"Roster Double Shift OT Checker - Site Supervisor").
	"""
	rules = frappe.get_all(
		"Assignment Rule",
		filters={"document_type": "Roster Double Shift OT Checker", "disabled": 0},
		pluck="name",
	)

	for rule in rules:
		frappe.db.set_value("Assignment Rule", rule, "disabled", 1)
		print(f"Disabled Assignment Rule {rule!r} (reverted Roster Double Shift OT Checker)")
