import frappe

# WI-002069: the Visa Request visibility rules the BA site carries and this site did not, plus
# three mandatory rules that had been switched off by writing "// " in front of them.
#
# The state names in the rules are this site's. The BA export writes the MOI state
# "Pending by MOI" where the workflow here has "Pending By MOI", and a depends_on naming a
# state that does not exist hides the section at exactly the step that fills it in.
GATED_FIELDS = (
	"pam_details_section",
	"custom_pam_file",
	"custom_work_permit_number",
	"moi_details_section",
	"visa_details_section",
)

MOI_STATE = "Pending By MOI"


def execute():
	frappe.reload_doc("visa_management", "doctype", "visa_request")

	verify()


def verify():
	meta = frappe.get_meta("Visa Request")
	states = {state.state for state in frappe.get_doc("Workflow", "Visa Request").states}

	if MOI_STATE not in states:
		frappe.throw(
			f"WI-002069: the Visa Request workflow has no {MOI_STATE!r} state, so the rules "
			"below name a state that does not exist and would hide each section at the step "
			"that fills it in."
		)

	for fieldname in GATED_FIELDS:
		field = meta.get_field(fieldname)
		if not field:
			frappe.throw(f"WI-002069: Visa Request has no {fieldname} field.")
		if not field.depends_on:
			frappe.throw(f"WI-002069: {fieldname} did not get its visibility rule.")

	# Every state a rule names has to be one the workflow actually has.
	for fieldname in GATED_FIELDS:
		named = {
			part.split('"')[1]
			for part in (meta.get_field(fieldname).depends_on or "").split("||")
			if '"' in part
		}
		unknown = sorted(named - states)
		if unknown:
			frappe.throw(
				f"WI-002069: {fieldname} names {unknown}, which the Visa Request workflow does "
				"not have - the section would stay hidden in those states."
			)
