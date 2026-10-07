# one_fm/patches/v15_0/restore_cancelled_onboarding_emp_onb_2026_00361.py
import frappe

ONBOARDING = "EMP-ONB-2026-00361"
DUTY_COMMENCEMENT = "DC-2026-00358"

# Put the onboarding back at "Work Contract", not at "Duty Commencement" where it was
# cancelled from. OnboardEmployee.validate_transition creates the Duty Commencement on the
# transition INTO "Duty Commencement":
#
#     if self.workflow_state == 'Duty Commencement' and not self.duty_commencement:
#         self.create_duty_commencement()
#
# so parking it one step earlier is what lets the officer click the workflow action and get
# a brand new Duty Commencement through the normal code path, instead of us hand-building
# one here. The "Work Contract" -> "Duty Commencement" transition is open to the Onboarding
# Officer, and create_duty_commencement's guard passes: WC-2026-00358 reads
# "Submitted to Legal", which is in its allowed work_contract_status list.
RESTORE_STATE = "Work Contract"

# The mirror fields Onboard Employee carries for its Duty Commencement. All of them are
# allow_on_submit, so clearing them leaves a submitted record that still saves cleanly.
DC_MIRROR_FIELDS = {
	"duty_commencement": "",
	"duty_commencement_name": "",
	"duty_commencement_status": "",
	"duty_commencement_docstatus": "",
	"duty_commencement_progress": 0,
}


def execute():
	"""Restore the onboarding cancelled by mistake on 2026-10-05, minus its Duty Commencement.

	EMP-ONB-2026-00361 (Abdi Kahin Gure, HR-OFF-2026-00772) was cancelled at 16:06 on
	2026-10-05 while it sat at "Duty Commencement". Onboard Employee has no on_cancel
	handler, so the cancel only flipped two columns on the onboarding itself -
	workflow_state and docstatus - and left every linked document intact. There is nothing
	to rebuild; there is only a flag to put back.

	Amending was the alternative and is worse: it would mint EMP-ONB-2026-00361-1 while
	WC-2026-00358 and DC-2026-00358 kept pointing at the old name, and update_onboarding_doc
	would keep writing back into the cancelled record.

	Three things happen here:

	* The onboarding goes back to docstatus 1 at RESTORE_STATE, child rows included.
	  Document.cancel() stamps docstatus 2 on the child tables too, and nothing propagates
	  the parent's docstatus back onto them until the document is saved again
	  (set_docstatus only runs inside a save), so they are fixed directly.

	* Its Duty Commencement mirror fields are cleared, and DC-2026-00358 is moved to the
	  "Cancelled" workflow state. Duty Commencement is not submittable - every state in its
	  workflow carries doc_status 0 - so this is a state change, not a cancellation, and
	  DutyCommencement.on_cancel never runs. It is marked rather than deleted because it
	  holds the applicant's signed PDF, and nothing else references it.

	* The employee link is cleared if it points at somebody else's Employee record. On this
	  onboarding it reads HR-EMP-04525 - Adit Rai, the onboarding officer, from their own
	  onboarding EMP-ONB-2026-00347 - and DC-2026-00358 inherited it through
	  fetch_from: onboard_employee.employee. Left in place it is not cosmetic: the next
	  workflow step runs create_employee -> update_duty_commencement ->
	  auto_checkin_candidate, which would raise a Shift Assignment and an auto check-in
	  against Adit Rai, and validate_name_change would write Abdi's Arabic names onto Adit
	  Rai's Employee record on the next name edit.

	Guarded on docstatus == 2 so it is a no-op on every site that does not carry the record
	in this state, and on a re-run after it has already been applied.
	"""
	if not frappe.db.exists("Onboard Employee", ONBOARDING):
		return

	onboarding = frappe.db.get_value(
		"Onboard Employee",
		ONBOARDING,
		["docstatus", "workflow_state", "employee", "job_applicant"],
		as_dict=True,
	)
	if onboarding.docstatus != 2:
		return

	updates = {"docstatus": 1, "workflow_state": RESTORE_STATE}
	updates.update(DC_MIRROR_FIELDS)

	# Only drop the employee link when it belongs to a different applicant. A link that
	# does match this onboarding is the real Employee record and must survive.
	if onboarding.employee:
		linked_applicant = frappe.db.get_value("Employee", onboarding.employee, "job_applicant")
		if linked_applicant != onboarding.job_applicant:
			updates["employee"] = ""

	frappe.db.set_value("Onboard Employee", ONBOARDING, updates, update_modified=False)

	for table_field in frappe.get_meta("Onboard Employee").get_table_fields():
		frappe.db.set_value(
			table_field.options,
			{"parent": ONBOARDING, "parenttype": "Onboard Employee", "docstatus": 2},
			"docstatus",
			1,
			update_modified=False,
		)

	if frappe.db.exists("Duty Commencement", DUTY_COMMENCEMENT):
		frappe.db.set_value(
			"Duty Commencement",
			DUTY_COMMENCEMENT,
			{"workflow_state": "Cancelled", "progress": 0},
			update_modified=False,
		)

	# These are direct column writes, so they leave no Version row. Leave the trail on the
	# document itself instead - this is a hand repair of a live record.
	frappe.get_doc("Onboard Employee", ONBOARDING).add_comment(
		"Comment",
		(
			"Restored by patch after an accidental cancellation on 2026-10-05: docstatus "
			f"back to 1 at '{RESTORE_STATE}'. {DUTY_COMMENCEMENT} was marked Cancelled and "
			"unlinked so a new Duty Commencement is created on the next workflow action."
		),
	)

	frappe.db.commit()
