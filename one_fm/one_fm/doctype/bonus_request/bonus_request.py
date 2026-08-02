# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, getdate, cint, flt


MONTH_MAP = {
	"January": 1, "February": 2, "March": 3, "April": 4,
	"May": 5, "June": 6, "July": 7, "August": 8,
	"September": 9, "October": 10, "November": 11, "December": 12
}


class BonusRequest(Document):
	def before_insert(self):
		"""Set defaults for new Bonus Request documents."""
		if not self.posting_date:
			self.posting_date = nowdate()

		if not self.effective_year:
			self.effective_year = getdate(nowdate()).year

		if not self.requested_by:
			self.requested_by = frappe.session.user

	def validate(self):
		self.set_line_manager()
		self.validate_self_request()
		self.validate_effective_month()
		self.validate_items()
		self.calculate_total_bonus_amount()
		self.validate_recurring_dates()
		self.validate_recurring_start_date()
		self.validate_row_level_approvals()

	def set_line_manager(self):
		"""Fetch the requesting employee's line manager (Reports To).

		reports_to_user is auto-populated by fetch_from (reports_to.user_id),
		and drives the "Bonus Request - Line Manager" assignment rule.
		"""
		if not self.requested_by:
			return

		self.reports_to = frappe.db.get_value(
			"Employee",
			{"user_id": self.requested_by, "status": "Active"},
			"reports_to"
		)

	def validate_self_request(self):
		"""Prevent users from adding themselves to the bonus request."""
		current_user = frappe.session.user
		if current_user == "Administrator":
			return

		current_employee = frappe.db.get_value(
			"Employee",
			{"user_id": current_user, "status": "Active"},
			"name"
		)
		if not current_employee:
			return

		for row in self.bonus_request_employees:
			if row.employee == current_employee:
				frappe.throw(
					_("Compliance Error: You cannot include yourself in a bonus request. "
					  "Please remove Employee {0} from Row {1}.").format(
						frappe.bold(row.employee_name or row.employee),
						row.idx
					),
					title=_("Self-Request Not Allowed")
				)

	def validate_items(self):
		"""Validate each child row: justification 'Other' requires description,
		clear description when justification is not 'Other',
		and enforce mutual exclusivity of approve/reject."""
		for row in self.bonus_request_employees:
			if row.justification == "Other" and not row.description:
				frappe.throw(
					_("Row {0}: Description is mandatory when Justification is 'Other'.").format(row.idx),
					title=_("Missing Description")
				)
			if row.justification != "Other":
				row.description = ""

			# Mutual exclusivity: cannot mark both Approved and Rejected
			if cint(row.approve) and cint(row.reject):
				frappe.throw(
					_("Row {0}: Cannot mark both Approved and Rejected "
					  "for Employee {1}.").format(
						row.idx, frappe.bold(row.employee_name or row.employee)
					),
					title=_("Invalid Approval State")
				)

	def validate_row_level_approvals(self):
		"""Block workflow transitions out of approval states unless every
		child row is explicitly marked as either Approved or Rejected."""
		approval_states = ["Pending HR Manager", "Pending Finance Manager"]

		previous_doc = self.get_doc_before_save()
		if not previous_doc:
			return

		# Only enforce when transitioning OUT of an approval state
		if previous_doc.workflow_state not in approval_states:
			return

		# If the state hasn't changed, this is just an edit — no gate needed
		if previous_doc.workflow_state == self.workflow_state:
			return

		undecided_rows = []
		for row in self.bonus_request_employees:
			if not cint(row.approve) and not cint(row.reject):
				undecided_rows.append(str(row.idx))

		if undecided_rows:
			frappe.throw(
				_("Cannot proceed: You must explicitly mark every single row "
				  "as either Approved or Rejected before advancing to the "
				  "next transition. Undecided rows: {0}").format(
					", ".join(undecided_rows)
				),
				title=_("Row-Level Approval Required")
			)

	def validate_effective_month(self):
		"""Ensure effective month is not in a past closed payroll period.

		The current month and any future month are allowed.
		Only past months (before the current month) are blocked.
		"""
		if not self.effective_month or not self.effective_year:
			return

		today = getdate(nowdate())
		current_month = today.month
		current_year = today.year

		selected_month = MONTH_MAP.get(self.effective_month)
		selected_year = cint(self.effective_year)

		if not selected_month:
			return

		# Block only past months — current month and future months are allowed
		if selected_year < current_year or (
			selected_year == current_year and selected_month < current_month
		):
			frappe.throw(
				_("Validation Error: Bonus requests cannot be applied to "
				  "previous closed payroll months."),
				title=_("Invalid Effective Month")
			)

	def calculate_total_bonus_amount(self):
		"""Sum bonus_amount across all child table rows."""
		self.total_bonus_amount = sum(
			flt(row.bonus_amount) for row in self.bonus_request_employees
		)

	def validate_recurring_dates(self):
		"""AC: End Date ≤ Start Date → block save."""
		if not cint(self.is_recurring_monthly):
			return

		if not self.start_date or not self.end_date:
			return

		if getdate(self.end_date) <= getdate(self.start_date):
			frappe.throw(
				_("Invalid Timeline: End Date must be later than the Start Date."),
				title=_("Invalid Recurring Dates")
			)

	def validate_recurring_start_date(self):
		"""AC: Start Date in current/past month → block save."""
		if not cint(self.is_recurring_monthly):
			return

		if not self.start_date:
			return

		today = getdate(nowdate())
		start = getdate(self.start_date)

		if (start.year < today.year) or (
			start.year == today.year and start.month <= today.month
		):
			frappe.throw(
				_("Timing Conflict: The recurring series must be scheduled to begin "
				  "in a future calendar month to ensure payroll accuracy."),
				title=_("Invalid Start Date")
			)


@frappe.whitelist()
def get_employees_for_bulk(department: str):
	"""Fetch active employees for a given department for the bulk bonus modal."""
	if not department:
		frappe.throw(_("Department is required."))

	return frappe.get_list(
		"Employee",
		filters={"status": "Active", "department": department},
		fields=["name as employee", "employee_name", "designation"],
		order_by="employee_name asc"
	)


@frappe.whitelist()
def create_consolidated_bonus_request(
	employees: str,
	bonus_amount: float,
	effective_month: str,
	effective_year: int,
	justification: str,
	description: str = ""
) -> str:
	"""Create a single Bonus Request with all employees as child table rows.

	Args:
		employees: JSON array of employee IDs.
		bonus_amount: Bonus amount applied to each employee row.
		effective_month: The month the bonus takes effect.
		effective_year: The year the bonus takes effect.
		justification: Justification from the dropdown (applied to all rows).
		description: Description text (required when justification is "Other").

	Returns:
		Name of the created Bonus Request document.
	"""
	employees = json.loads(employees) if isinstance(employees, str) else employees

	if not employees:
		frappe.throw(_("No employees selected."))

	effective_year = cint(effective_year)
	bonus_amount = flt(bonus_amount)

	if bonus_amount <= 0:
		frappe.throw(_("Bonus Amount must be greater than zero."))

	if not justification:
		frappe.throw(_("Please select a Justification."))

	if justification == "Other" and not description:
		frappe.throw(_("Description is mandatory when Justification is 'Other'."))

	# Validate effective month is not in a past closed payroll period
	today = getdate(nowdate())
	selected_month = MONTH_MAP.get(effective_month)
	if not selected_month:
		frappe.throw(_("Invalid Effective Month."))

	if effective_year < today.year or (
		effective_year == today.year and selected_month < today.month
	):
		frappe.throw(
			_("Validation Error: Bonus requests cannot be applied to "
			  "previous closed payroll months."),
			title=_("Invalid Effective Month")
		)

	# Build child table rows
	items = []
	for emp in employees:
		items.append({
			"employee": emp,
			"bonus_amount": bonus_amount,
			"justification": justification,
			"description": description if justification == "Other" else "",
		})

	# Create the consolidated Bonus Request document
	bonus_request = frappe.get_doc({
		"doctype": "Bonus Request",
		"posting_date": nowdate(),
		"effective_month": effective_month,
		"effective_year": effective_year,
		"bonus_request_employees": items,
	})
	bonus_request.insert()

	frappe.msgprint(
		_("Bonus Request {0} created with {1} employee(s).").format(
			frappe.bold(bonus_request.name),
			len(employees)
		),
		title=_("Bonus Request Created"),
		indicator="green"
	)

	return bonus_request.name
