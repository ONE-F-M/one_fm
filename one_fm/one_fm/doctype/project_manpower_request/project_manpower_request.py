# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.desk.form.assign_to import add as add_assignment


class ProjectManpowerRequest(Document):
	def autoname(self):
		from frappe.model.naming import make_autoname
		
		# Only generate autoname on first creation
		if not self.name:
			# Base sequence
			base_id = make_autoname("PR.#####")
			
			# Append suffix based on 'reason' or Manpower Type
			if self.reason == "Overtime":
				self.name = f"{base_id}-OT"
			elif self.reason == "Sub Contractor":
				self.name = f"{base_id}-SB"
			else:
				self.name = base_id
		
		# Sync the visual ID field
		self.project_request_code = self.name

	def validate(self):
		self.update_select_field_options()
		if self.reason == "Exit":
			if self.get("resignation_links"):
				self.count = len(self.resignation_links)
				projects = {r.project_allocation for r in self.resignation_links if r.project_allocation}
				if len(projects) > 1:
					frappe.throw(_("All grouped resignations must belong to exactly the same Project."))
				if projects:
					self.project_allocation = list(projects)[0]
					
		self.ensure_fulfillment_rows()
		self.calculate_remaining_qty()
		self.check_status_lock()
		self.validate_project_allocation()
		self.validate_erf_presence()
		self.validate_recruiter_presence()
		self.validate_change_request_reason()
		self.validate_deployment_date()
		self.validate_completion()

	def validate_project_allocation(self):
		exempt_reasons = ["Annual Leave Reliever", "Day OFF Reliever", "Reliever"]
		if self.reason and self.reason not in exempt_reasons:
			if not self.project_allocation:
				frappe.throw(
					_("Project is mandatory for Reason: {0}").format(self.reason),
					frappe.MandatoryError
				)

	def validate_deployment_date(self):
		if self.deployment_date:
			from frappe.utils import getdate, today
			is_changed = False
			if self.is_new():
				is_changed = True
			else:
				db_date = frappe.db.get_value("Project Manpower Request", self.name, "deployment_date")
				if db_date and getdate(self.deployment_date) != getdate(db_date):
					is_changed = True
			
			if is_changed and getdate(self.deployment_date) < getdate(today()):
				frappe.throw(
					_("Deployment Date cannot be before today."),
					title=_("Invalid Deployment Date")
				)

	def validate_change_request_reason(self):
		if not self.is_new():
			old_state = frappe.db.get_value("Project Manpower Request", self.name, "workflow_state")
			if old_state == "Awaiting Recruiter Approval" and getattr(self, "workflow_state", None) == "Draft":
				if not getattr(self, "reason_for_rejection", None) or not self.reason_for_rejection.strip():
					frappe.throw(
						_("Please provide a reason for requesting changes before sending it back to Draft."),
						title=_("Change Request Reason Required")
					)

	def validate_recruiter_presence(self):
		if self.flags.ignore_mandatory:
			return
		if (getattr(self, "workflow_state", None) or "Draft") != "Draft":
			if not self.recruiter:
				frappe.throw(
					_("Please assign a <b>Recruiter</b> before moving this Project Manpower Request past Draft."),
					title=_("Missing Recruiter")
				)


	def validate_erf_presence(self):
		if self.flags.ignore_mandatory:
			return
		if getattr(self, "workflow_state", None) in ["Awaiting Recruiter Approval", "In Process", "Completed"]:
			if not self.erf:
				frappe.throw(
					_("Please select an ERF before sending this Project Manpower Request for Recruitment.")
				)
			erf_designation = frappe.db.get_value("ERF", self.erf, "designation")
			if erf_designation != self.designation:
				frappe.throw(
					_("The selected ERF ({0}) has designation '{1}' which does not match this PMR's designation '{2}'.").format(
						self.erf, erf_designation, self.designation
					)
				)

	def ensure_fulfillment_rows(self):
		required_actions = [
			"Cancelled", "Managed by OT", "Managed by SubContractor", 
			"Internal Transfer", "Resignation Withdrawal"
		]
		
		existing = set()
		for row in self.get("fulfillment_actions"):
			existing.add(row.action_type)
			
		for action in required_actions:
			if action not in existing:
				self.append("fulfillment_actions", {
					"action_type": action,
					"qty": 0
				})

	def check_status_lock(self):
		if not self.is_new():
			old_status = frappe.db.get_value("Project Manpower Request", self.name, "workflow_state")
			terminal_statuses = ["Completed", "Rejected", "Cancelled"]
			
			if old_status in terminal_statuses and getattr(self, "workflow_state", None) != old_status:
				frappe.throw(
					_("The status cannot be changed further because it has already reached a terminal state: {0}").format(old_status)
				)



	def validate_completion(self):
		if self.flags.ignore_mandatory:
			return
		if getattr(self, "workflow_state", None) == "Completed":
			hired_count = len(self.get('fulfilled_by_employees', []))
			if hired_count != self.remaining_qty:
				frappe.throw(
					_("To mark this PMR as Completed, you must link exactly {0} Employee(s) in the Closure Details section to match the Remaining Qty (Currently linked: {1}).").format(
						self.remaining_qty, hired_count
					)
				)

	def on_submit(self):
		pass

	def on_update(self):
		self.update_erf_headcount()
		self.assign_recruiter()

	def assign_recruiter(self):
		recruiter = self.get("recruiter")
		if not recruiter:
			return

		if not self.is_new():
			old_doc = self.get_doc_before_save()
			old_recruiter = old_doc.get("recruiter") if old_doc else None
			if old_recruiter and old_recruiter != recruiter:
				try:
					from frappe.desk.form.assign_to import remove as remove_assignment
					remove_assignment(self.doctype, self.name, old_recruiter)
				except Exception:
					pass

		# Check if already assigned to this recruiter
		is_assigned = frappe.db.exists("ToDo", {
			"reference_type": self.doctype,
			"reference_name": self.name,
			"allocated_to": recruiter,
			"status": "Open"
		})
		
		if not is_assigned:
			try:
				add_assignment({
					"doctype": self.doctype,
					"name": self.name,
					"assign_to": [recruiter],
					"description": _("Assigned for Recruitment processing"),
				}, ignore_permissions=True)
			except Exception as e:
				frappe.log_error(
					message=f"Error assigning recruiter for {self.name}: {str(e)}",
					title="PMR Recruiter Assignment Error"
				)
		
	def before_update_after_submit(self):
		self.calculate_remaining_qty()
		self.validate_completion()

	def on_update_after_submit(self):
		# Explicitly commit the recalculated totals to the DB
		self.db_set("remaining_qty", self.remaining_qty, update_modified=False)
		self.db_set("number_to_hire", self.number_to_hire, update_modified=False)
		self.update_erf_headcount()

	def on_trash(self):
		self.revert_erf_headcount()

	def calculate_remaining_qty(self):
		target = self.count or 0
		
		fulfilled = sum((row.qty or 0) for row in self.get("fulfillment_actions", []))

		self.remaining_qty = max(0, target - fulfilled)
		
		# Number to hire = Remaining Qty minus the actual employees linked in the child table (and legacy joined)
		hired_count = len(self.get('fulfilled_by_employees', []))
		historically_joined = self.historically_joined_qty or 0
		self.number_to_hire = max(0, self.remaining_qty - hired_count - historically_joined)

	def update_erf_headcount(self):
		if not self.erf:
			return

		# If it is Rejected or Cancelled, its contribution should be 0.
		# Include Draft and early stages so the message shows immediately on creation
		active_statuses = ["Draft", "In Process", "Completed", "Awaiting Recruiter Approval", "Pending OM Approval"]
		target_contribution = self.number_to_hire if getattr(self, "workflow_state", None) in active_statuses or not self.workflow_state else 0

		current_contribution = self.qty_added_to_erf or 0
		delta = target_contribution - current_contribution

		if delta != 0:
			current_erf_req = frappe.db.get_value("ERF", self.erf, "number_of_candidates_required") or 0
			new_req = current_erf_req + delta
			frappe.db.set_value("ERF", self.erf, "number_of_candidates_required", new_req)
			self.db_set("qty_added_to_erf", target_contribution, update_modified=False)
			
			direction = "increased" if delta > 0 else "decreased"
			frappe.msgprint(_("ERF {0} requirement {1} by {2}. Current Total: {3}").format(
				frappe.bold(self.erf), direction, frappe.bold(abs(delta)), frappe.bold(new_req)))

	def revert_erf_headcount(self):
		if self.erf and self.qty_added_to_erf:
			current_erf_req = frappe.db.get_value("ERF", self.erf, "number_of_candidates_required") or 0
			frappe.db.set_value("ERF", self.erf, "number_of_candidates_required", current_erf_req - self.qty_added_to_erf)

	def update_select_field_options(self):
		for fieldname, default_opts, doctype in [
			("gender", ["Any", "Male", "Female"], "Gender"),
			("nationality", ["Any", "African", "Asian"], "Nationality")
		]:
			field = self.meta.get_field(fieldname)
			if field:
				db_opts = [d for d in frappe.get_all(doctype, pluck="name", ignore_permissions=True) if d]
				opts = list(default_opts)
				for opt in db_opts:
					if opt not in opts:
						opts.append(opt)
				field.options = "\n".join(opts)

@frappe.whitelist()
def set_edit_reason(name: str, reason: str) -> str:
	doc = frappe.get_doc("Project Manpower Request", name)
	doc.check_permission("read")
	frappe.db.set_value("Project Manpower Request", name, "reason_for_rejection", reason)
	frappe.clear_document_cache("Project Manpower Request", name)
	return frappe.db.get_value("Project Manpower Request", name, "modified")




@frappe.whitelist()
def get_autocomplete_options() -> dict:
	"""Fetch all Nationality and Gender options for PMR Autocomplete fields."""
	# Ensure the caller has permission to read PMR
	if not frappe.has_permission("Project Manpower Request", "read"):
		frappe.throw(_("Not permitted to access manpower request details."), frappe.PermissionError)

	nationalities = frappe.get_all("Nationality", fields=["name"], order_by="name asc", ignore_permissions=True)
	genders = frappe.get_all("Gender", fields=["name"], order_by="name asc", ignore_permissions=True)

	return {
		"nationalities": [n.name for n in nationalities if n.name],
		"genders": [g.name for g in genders if g.name]
	}



