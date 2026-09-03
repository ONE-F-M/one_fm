import frappe

from one_fm.one_fm.doctype.erf.erf import DEFAULT_ERF_APPROVER_ROLE

# WI-002316: who approves an ERF was decided by matching Reason for Request against the
# literal string "UnPlanned". That tied the approver to one spelling of one Select option,
# so removing or renaming the option sent every ERF to the general approver and left
# "Unplanned ERF Approver" unreachable - silently, because nothing checks that a role is
# still reachable.
#
# The mapping lives in Hiring Settings now. This seeds it with exactly what the code used
# to do, so nothing about today's routing changes on migrate; what changes is that the next
# reason can be routed without touching the code.
UNPLANNED_REASON = "UnPlanned"
UNPLANNED_ROLE = "Unplanned ERF Approver"


def execute():
	frappe.reload_doc("hiring", "doctype", "erf_approver_rule")
	frappe.reload_doc("hiring", "doctype", "hiring_settings")

	settings = frappe.get_doc("Hiring Settings")

	if not settings.default_erf_approver_role and frappe.db.exists("Role", DEFAULT_ERF_APPROVER_ROLE):
		settings.default_erf_approver_role = DEFAULT_ERF_APPROVER_ROLE

	already = {rule.reason_for_request for rule in settings.erf_approver_rules}
	if UNPLANNED_REASON not in already and frappe.db.exists("Role", UNPLANNED_ROLE):
		settings.append("erf_approver_rules", {
			"reason_for_request": UNPLANNED_REASON,
			"approver_role": UNPLANNED_ROLE,
		})

	settings.flags.ignore_mandatory = True
	settings.flags.ignore_permissions = True
	settings.save()
	frappe.clear_cache(doctype="Hiring Settings")

	verify()


def verify():
	"""The seeded mapping has to reproduce the old behaviour exactly, or every ERF raised
	before the next Hiring Settings edit routes somewhere new without anybody asking."""
	from one_fm.one_fm.doctype.erf.erf import get_erf_approver_role

	if frappe.db.exists("Role", UNPLANNED_ROLE):
		routed = get_erf_approver_role(UNPLANNED_REASON)
		if routed != UNPLANNED_ROLE:
			frappe.throw(
				f"WI-002316: {UNPLANNED_REASON!r} now routes to {routed!r} rather than "
				f"{UNPLANNED_ROLE!r} - the seeded rule did not take."
			)

	for reason in ("Staffing Plan", "Employee Exit", "New Project", None):
		routed = get_erf_approver_role(reason)
		if routed != DEFAULT_ERF_APPROVER_ROLE:
			frappe.throw(
				f"WI-002316: {reason!r} routes to {routed!r} rather than the default "
				f"{DEFAULT_ERF_APPROVER_ROLE!r}."
			)

	print("WI-002316: ERF approver routing is configurable, and routes as it did before")
