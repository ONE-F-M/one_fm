import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, today, cint


class PenaltyAndInvestigation(Document):
	def validate(self):
		self.validate_duplicate_penalty()
		self.calculate_offence_count()
		self.validate_workflow_transition()

	def validate_workflow_transition(self):
		if not self.workflow_state:
			return

		old_state = self.get_db_value("workflow_state")
		if not old_state:
			return

		# Trim to handle trailing spaces in state names (e.g. "Pending Legal Investigation ")
		curr_state_trimmed = self.workflow_state.strip()
		old_state_trimmed = old_state.strip()

		if old_state_trimmed == "Pending Employee Response" and curr_state_trimmed == "Pending Supervisor Review":
			self._validate_employee_to_supervisor_transition()

		if old_state_trimmed == "Pending Supervisor Review" and curr_state_trimmed == "Pending HR Review":
			self._validate_supervisor_to_hr_transition()

		if old_state_trimmed == "Pending GM Decision" and curr_state_trimmed == "Pending Legal Investigation":
			if not self.general_manager_decision:
				frappe.throw(_("General Manager Decision is required before moving to Pending Legal Investigation"))

		if old_state_trimmed == "Pending HR Review" and curr_state_trimmed == "Pending GM Decision":
			if not self.hr_remarks:
				frappe.throw(_("HR Remarks are required before moving to Pending GM Decision"))

	def _validate_employee_to_supervisor_transition(self):
		if not self.employee_rejection_remarks:
			frappe.throw(_("Employee Rejection Remarks are required before moving to Pending Supervisor Review"))

	def _validate_supervisor_to_hr_transition(self):
		if not self.supervisor_remarks or not self.evidence:
			frappe.throw(_("Both Supervisor Remarks and Evidence are required before moving to Pending HR Review"))

	def validate_duplicate_penalty(self):
		if not self.employee or not self.applied_penalty_code or not self.incident_date:
			return

		duplicate = frappe.db.exists(
			"Penalty And Investigation",
			{
				"employee": self.employee,
				"applied_penalty_code": self.applied_penalty_code,
				"incident_date": self.incident_date,
				"name": ["!=", self.name],
				"docstatus": ["!=", 2],
			},
		)

		if duplicate:
			frappe.throw(
				_("An active penalty investigation already exists for Employee {0} with Penalty Code {1} on {2}").format(
					self.employee, self.applied_penalty_code, self.incident_date
				)
			)

	def calculate_offence_count(self):
		if not self.employee or not self.applied_penalty_code or not self.incident_date:
			return

		# Get date 12 months ago from today
		twelve_months_ago = add_months(today(), -12)

		# Count previous occurrences for this employee and penalty code
		# We count records within the last 12 months, excluding the current record
		# We exclude cancelled records (docstatus 2)
		previous_count = frappe.db.count(
			"Penalty And Investigation",
			{
				"employee": self.employee,
				"applied_penalty_code": self.applied_penalty_code,
				"incident_date": [">=", twelve_months_ago],
				"name": ["!=", self.name],
				"docstatus": ["!=", 2],
			},
		)

		# The current offence count is the previous count plus this one
		self.offence_count = previous_count + 1

		# Set applied_level based on offence_count, capped at 5
		level = self.offence_count
		if level > 5:
			level = 5

		self.applied_level = str(level)

		# Set deduction_type and salary_deduction_days based on offence level
		level_map = {
			1: "1st",
			2: "2nd",
			3: "3rd",
			4: "4th",
			5: "5th"
		}
		target_level = level_map.get(level)
		
		penalty_code_doc = frappe.get_doc("Penalty Code", self.applied_penalty_code)
		
		found_level = False
		for row in penalty_code_doc.get("penalty_level") or []:
			if row.offence_level == target_level:
				self.deduction_type = row.deduction_type
				self.salary_deduction_days = row.salary_deduction_days
				found_level = True
				break
				
		if not found_level:
			self.deduction_type = None
			self.salary_deduction_days = 0


@frappe.whitelist()
def get_penalty_count():
	user = frappe.session.user
	count = frappe.db.count("Penalty And Investigation", {
		"employee_user": user,
		"docstatus": ["!=", 2]
	})

	return {
		"value": count,
		"fieldtype": "Int",
		"route": ["List", "Penalty And Investigation", "", {"docstatus": ["!=", 2]}]
	}


@frappe.whitelist()
def get_last_penalty_status():
	user = frappe.session.user
	latest_record = frappe.db.get_list(
		"Penalty And Investigation",
		filters={"employee_user": user},
		fields=["name", "workflow_state"],
		order_by="creation desc",
		limit=1,
	)

	if not latest_record:
		return {"value": _("None"), "fieldtype": "Data", "route": ["New", "Penalty And Investigation", ""]}

	record = latest_record[0]
	return {
		"value": f'{record.workflow_state}',
		"fieldtype": "Data",
		"route": ["Form", "Penalty And Investigation", record.name],
	}
