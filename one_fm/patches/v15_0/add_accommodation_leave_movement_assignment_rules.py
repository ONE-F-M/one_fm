from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)

RULES = (
	"accommodation_leave_movement_site_supervisor.json",
	"accommodation_leave_movement_site_supervisor_checkin.json",
)


def execute():
	"""Assign Accommodation Leave Movements to the resident's site supervisor (WI-001781).

	Assignment rules are only created by the installer, so an existing site needs them
	applied here.

	The OUT rule closes on ALM's own `checked_out` flag rather than looking the linked
	IN movement up: `frappe.db.exists()` is not available in safe_eval, which is the
	same trap already patched out of the Leave Application rule.
	"""
	for rule in RULES:
		create_assignment_rule(get_assignment_rule_json_file(rule))
