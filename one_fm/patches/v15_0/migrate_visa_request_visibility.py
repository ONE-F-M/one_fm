import frappe
from frappe.model.utils.rename_field import rename_field

# WI-002069: the Visa Request visibility rules the BA site carries and this site did not, plus
# three mandatory rules that had been switched off by writing "// " in front of them.
#
# The state names in the rules are this site's. The BA export writes the MOI state
# "Pending by MOI" where the workflow here has "Pending By MOI", and a depends_on naming a
# state that does not exist hides the section at exactly the step that fills it in.
# WI-002069 (second pass): the BA site also locks each of these once the request has moved
# past the step that fills it in. None of them came across the first time - the diff that
# drove that pass compared a hand-picked list of attributes and read_only_depends_on was not
# on it.
READ_ONLY_FIELDS = (
	"custom_pam_file",
	"pam_reference_number",
	"custom_visa_application_date",
	"custom_pam_designation_list",
	"custom_work_permit_number",
	"moi_reference_number",
	"visa_reference_number",
	"visa_issue_date",
	"visa_expiry_date",
	"visa_document",
	"payment_receipt",
	"payment_date",
)

GATED_FIELDS = (
	"pam_details_section",
	"custom_pam_file",
	"custom_work_permit_number",
	"moi_details_section",
	"visa_details_section",
)

MOI_STATE = "Pending By MOI"


# WI-002069 (third pass): a Link the BA site added after the migration, which that site has
# since renamed and made visible - "assign_grd_operator", hidden, is now "grd_operator"
# labelled GRD Operator. Still an empty holder there: no assignment rule takes its assignee
# from it and no script mentions it.
NEW_FIELD = "grd_operator"
OLD_FIELD = "assign_grd_operator"


def execute():
	frappe.reload_doc("visa_management", "doctype", "visa_request")

	# The holder shipped under its old name first, so anything already written to it moves
	# with the rename rather than being left behind in an orphan column.
	rename_field("Visa Request", OLD_FIELD, NEW_FIELD)

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

	if not meta.get_field(NEW_FIELD):
		frappe.throw(f"WI-002069: Visa Request has no {NEW_FIELD} field.")

	for fieldname in READ_ONLY_FIELDS:
		field = meta.get_field(fieldname)
		if not field:
			frappe.throw(f"WI-002069: Visa Request has no {fieldname} field.")
		if not field.read_only_depends_on:
			frappe.throw(
				f"WI-002069: {fieldname} did not get its read-only rule, so it stays editable "
				"after the step that fills it in."
			)

	# Every state a rule names has to be one the workflow actually has - for both kinds of
	# rule, because a condition naming a state that does not exist simply never fires.
	for fieldname, attribute in (
		[(f, "depends_on") for f in GATED_FIELDS] + [(f, "read_only_depends_on") for f in READ_ONLY_FIELDS]
	):
		named = {
			part.split('"')[1]
			for part in (meta.get_field(fieldname).get(attribute) or "").split("||")
			if '"' in part
		}
		unknown = sorted(named - states)
		if unknown:
			frappe.throw(
				f"WI-002069: {fieldname}.{attribute} names {unknown}, which the Visa Request "
				"workflow does not have - the rule would never fire."
			)
