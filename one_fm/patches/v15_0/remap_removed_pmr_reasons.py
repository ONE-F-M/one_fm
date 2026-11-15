import frappe

DOCTYPE = "Project Manpower Request"

# The two options dropped from the Reason select, and the option each one folds
# into. Both targets are existing, unchanged options.
REASON_MAP = {
	"Subcontractor Replacement": "Sub Contractor",
	"Reliever": "Day OFF Reliever",
}


def execute():
	"""HD-1927006: fold the two retired Reason options into the ones that stay.

	Operations asked for "Subcontractor Replacement" and "Reliever" to be removed
	from the Reason select on Project Manpower Request. The select is trimmed in the
	doctype, which leaves every record still holding one of those two values with a
	Reason the field can no longer render: the form shows it blank, and the next save
	by a recruiter or an approver writes that blank back.

	Five records carry the retired values, four of them still in flight (In Process
	and Awaiting Recruiter Approval). The requester confirmed the mapping above, so
	the stored values move to the options that remain rather than being cleared.

	The mapping is safe for the Project Allocation rule in
	validate_project_allocation(). "Day OFF Reliever" is already an exempt reason, so
	the four Reliever requests keep their exemption from the mandatory Project check,
	and "Sub Contractor" was never exempt, exactly like the "Subcontractor
	Replacement" it replaces. Nothing that was saveable becomes unsaveable.

	The now dead "Reliever" entry is dropped from exempt_reasons in the controller in
	the same change, which is why this patch has to leave no record behind: it is
	scoped by value, not by name, so it catches drafts and cancelled records too.

	db.set_value per record rather than loading the document: these are submitted and
	workflow driven, and a save would re-run validation and the workflow transition
	checks on records this patch is only correcting a stored value on.
	"""
	for old_reason, new_reason in REASON_MAP.items():
		names = frappe.get_all(
			DOCTYPE,
			filters={"reason": old_reason},
			pluck="name",
		)

		for name in names:
			frappe.db.set_value(DOCTYPE, name, "reason", new_reason, update_modified=False)

	frappe.db.commit()
