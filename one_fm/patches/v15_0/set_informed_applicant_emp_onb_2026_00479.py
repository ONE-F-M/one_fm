import frappe

DOCTYPE = "Onboard Employee"
NAME = "EMP-ONB-2026-00479"


def execute():
	"""HD-1927134: let EMP-ONB-2026-00479 out of the Applicant Attended dead end.

	Create > Work Contract on this onboarding throws `Applicant not Informed !`.
	create_work_contract() calls validate_orientation(), which refuses while
	informed_applicant is unset, and on this record informed_applicant is 0 even
	though applicant_attended is 1 and the workflow has moved on to Applicant
	Attended.

	The Inform Applicant step never completed here. It is the only Onboard Employee
	of the last six weeks carrying no "Inform Applicant" Workflow comment, and its
	version history writes applicant_attended without ever writing
	informed_applicant. The workflow advanced regardless because
	validate_transition() marks the applicant attended off the workflow state alone
	and never checks the flag the earlier state was supposed to set.

	Nobody can repair it from the desk. informed_applicant is read_only, and the one
	place that writes it, inform_applicant(), runs only from on_update while the
	workflow state is Inform Applicant, which this submitted record is long past. The
	only forward action throws and there is no way back.

	So set the flag the Inform Applicant step would have set, leaving the record
	exactly where a healthy onboarding stands at this point. The Work Contract step
	then runs normally.

	Scope is this record alone: it is the single submitted Onboard Employee on
	production with informed_applicant = 0, against 2147 correct ones. The gap in
	validate_transition() that allowed it is a separate piece of work.
	"""
	onboarding = frappe.db.get_value(
		DOCTYPE,
		NAME,
		["docstatus", "workflow_state", "informed_applicant", "applicant_attended", "work_contract"],
		as_dict=True,
	)

	if not onboarding:
		return

	# Already informed, or moved on by other means: nothing stranded to repair.
	if onboarding.informed_applicant:
		return

	# Only the exact stranded shape is touched. A record that is still a draft, has
	# left Applicant Attended, was never marked attended, or already has its Work
	# Contract is not the one this patch is for.
	if onboarding.docstatus != 1:
		return

	if onboarding.workflow_state != "Applicant Attended":
		return

	if not onboarding.applicant_attended:
		return

	if onboarding.work_contract:
		return

	# db.set_value, not the document: the record is submitted, and a save would run
	# validate_transition() again and re-enter the creation path this patch unblocks.
	frappe.db.set_value(DOCTYPE, NAME, "informed_applicant", 1, update_modified=False)

	frappe.db.commit()
