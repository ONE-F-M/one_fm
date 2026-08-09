# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class EmployeeResignationWithdrawal(Document):
	def on_update(self):
		self.validate_rejection_reason()
		self.process_withdrawal_approval()
		self.notify_offboarding_on_submission()

	def notify_offboarding_on_submission(self):
		# Notify Offboarding Officer as soon as the withdrawal is first submitted,
		# whichever of the three branch entry states it lands in.
		entry_states = ("Pending Line Manager", "Pending Supervisor", "Pending T4 Admin")
		if self.workflow_state in entry_states:
			old_doc = self.get_doc_before_save()
			if not old_doc or old_doc.workflow_state not in entry_states:
				recipients = set()
				from frappe.utils.user import get_users_with_role
				offboarding_officers = get_users_with_role("Offboarding Officer")
				for user in offboarding_officers:
					recipients.add(user)
				
				if recipients:
					subject = _("Attention: Resignation Withdrawal Initiated - {0}").format(self.name)
					message = _("A resignation withdrawal request <b>{0}</b> has been submitted to the supervisor. Please hold any offboarding processing for the involved employees.").format(self.name)
					
					from one_fm.processor import sendemail
					sendemail(
						recipients=list(recipients),
						subject=subject,
						message=message,
						reference_doctype=self.doctype,
						reference_name=self.name
					)

	def process_withdrawal_approval(self):
		if not self.is_new():
			old_doc = self.get_doc_before_save()
			if (
				old_doc
				and old_doc.workflow_state != "Approved"
				and self.workflow_state == "Approved"
			):
				if not (self.reason and self.resignation_withdrawal_letter):
					return

				# A. Clear Relieving Date on the actual Employee profile
				if self.employee:
					frappe.db.set_value("Employee", self.employee, {
						"relieving_date": None,
						"resignation_date": None,
						"resignation_letter_date": None,
						"reason_for_leaving": None,
						"resignation_status": None,
						"current_resignation": None
					}, update_modified=False)

				if not self.employee_resignation:
					return

				# B. Mark the original Resignation as Withdrawn -- single employee, so
				# approving this withdrawal always fully withdraws the resignation.
				resignation = frappe.get_doc("Employee Resignation", self.employee_resignation)
				if frappe.db.has_column("Employee Resignation", "status"):
					resignation.db_set("status", "Withdrawn")
				if frappe.db.has_column("Employee Resignation", "workflow_state"):
					# Bypass workflow engine: Administrative auto-close.
					# Employee Resignation workflow does not have a user-facing transition to 'Withdrawn'.
					resignation.db_set("workflow_state", "Withdrawn")

				# C. Handle PMR counters
				pmr_name = frappe.db.get_value("Project Manpower Request", {"employee_resignation": self.employee_resignation}, "name")
				if pmr_name:
					pmr = frappe.get_doc("Project Manpower Request", pmr_name)
					if pmr.docstatus < 2:
						# Increase PMR withdrawal tracking natively in the child table matrix!
						withdrawal_row_found = False
						for f_row in pmr.get("fulfillment_actions", []):
							if f_row.action_type == "Resignation Withdrawal":
								f_row.qty = (f_row.qty or 0) + 1
								withdrawal_row_found = True
								break

						if not withdrawal_row_found:
							pmr.append("fulfillment_actions", {
								"action_type": "Resignation Withdrawal",
								"qty": 1
							})

						# Recalculate remaining quantities automatically
						if hasattr(pmr, 'calculate_remaining_qty'):
							pmr.calculate_remaining_qty()
							pmr.save()

							# Auto-close/set status if entirely withdrawn
							if (pmr.remaining_qty or 0) == 0:
								withdrawal_qty = sum((row.qty or 0) for row in pmr.get("fulfillment_actions", []) if row.action_type == "Resignation Withdrawal")
								if withdrawal_qty >= (pmr.count or 0):
									# Bypass workflow engine: Administrative auto-close.
									# PMR workflow does not have a user-facing transition to 'Withdrawn'.
									pmr.db_set("workflow_state", "Withdrawn")
									if frappe.db.has_column("Project Manpower Request", "status"):
										pmr.db_set("status", "Withdrawn") # Sync legacy status if it exists

						# Simply notify the recruiter that a withdrawal occurred.
						# We do NOT cancel the PMR here; the Recruiter will handle closure manually.
						if getattr(pmr, "recruiter", None):
							from one_fm.processor import sendemail
							sendemail(
								recipients=[pmr.recruiter],
								subject=_("Action Required: Withdrawal on PR {0}").format(pmr.name),
								message=_("An employee involved in PR <b>{0}</b> has withdrawn their resignation. Please review the 'Fulfillment Actions' table and close the request if no longer needed.").format(pmr.name),
								reference_doctype="Project Manpower Request",
								reference_name=pmr.name
							)

	def validate(self):
		self.set_approver()
		self.validate_no_active_withdrawal()
		if self.employee_resignation:
			pmr_name = frappe.db.get_value("Project Manpower Request", {"employee_resignation": self.employee_resignation}, "name")
			if pmr_name:
				pmr_wf_state = frappe.db.get_value("Project Manpower Request", pmr_name, "workflow_state")

				if pmr_wf_state in ["Completed", "Closed", "Fulfilled", "Hired"]:
					frappe.throw(_("Cannot withdraw resignation because the replacement Project Manpower Request ({0}) has already been completed or fulfilled. A replacement has likely already been hired. Please contact HR.").format(pmr_name))

		# Skip on the initial insert and while still a Draft: the mobile API (and
		# the desk "New" flow) creates the document first, then attaches the
		# letter via a direct db.set_value once the doc has a name --
		# resignation_withdrawal_letter is genuinely empty at that moment, and a
		# Draft may be saved incomplete before the requester submits it for
		# review. Enforced from "Submit for Review" onward.
		if (
			not self.is_new()
			and self.workflow_state not in (None, "", "Draft")
			and (not self.reason or not self.resignation_withdrawal_letter)
		):
			frappe.throw(_("You must provide both a Reason and a Withdrawal Letter to submit a withdrawal."), title=_("Missing Information"))


	def validate_no_active_withdrawal(self):
		# One withdrawal request per employee at a time -- otherwise a second
		# request could get approved/rejected independently of the first and
		# leave the employee's resignation in an inconsistent state.
		if not self.employee:
			return

		existing = frappe.db.get_value(
			"Employee Resignation Withdrawal",
			{
				"employee": self.employee,
				"workflow_state": ["not in", ["Approved", "Rejected"]],
				"name": ["!=", self.name or ""],
			},
			"name",
		)
		if existing:
			frappe.throw(
				_("Withdrawal request {0} for this employee is still in progress. Please wait until it is Approved or Rejected before submitting another.").format(existing),
				title=_("Withdrawal Already In Progress"),
			)

	def validate_rejection_reason(self):
		if not self.is_new():
			old_doc = self.get_doc_before_save()
			if (
				old_doc
				and old_doc.workflow_state in [
					"Pending Line Manager", "Pending Supervisor", "Pending T4 Admin", "Pending Project Manager",
				]
				and self.workflow_state == "Rejected"
			):
				if not getattr(self, "reason_for_rejection", None):
					frappe.throw(_("Please provide Reason for Rejection"))

	def set_approver(self):
		if not self.employee and self.employee_resignation:
			self.employee = frappe.db.get_value("Employee Resignation", self.employee_resignation, "employee")

		if not self.employee:
			return

		# Withdrawal reuses the exact same routing/actors already resolved on the
		# originating Employee Resignation -- fetch rather than re-derive, so the
		# two documents can never disagree on who the actor is.
		if self.employee_resignation:
			resignation = frappe.db.get_value(
				"Employee Resignation", self.employee_resignation,
				["shift_working", "supervisor", "t4_admin", "cleaning_head_supervisor",
				 "security_manager", "project_manager"],
				as_dict=True,
			)
			if resignation:
				self.is_corporate = 0 if resignation.shift_working else 1
				self.supervisor = resignation.supervisor
				self.t4_admin = resignation.t4_admin
				self.cleaning_head_supervisor = resignation.cleaning_head_supervisor
				self.security_manager = resignation.security_manager
				self.project_manager = resignation.project_manager

		# Set Offboarding Officer — first user with that role
		if not self.get("offboarding_officer"):
			from frappe.utils.user import get_users_with_role
			om_users = get_users_with_role("Offboarding Officer")
			if om_users:
				self.offboarding_officer = om_users[0]

