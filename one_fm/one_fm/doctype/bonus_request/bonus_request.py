# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, getdate, cint


MONTH_MAP = {
	"January": 1, "February": 2, "March": 3, "April": 4,
	"May": 5, "June": 6, "July": 7, "August": 8,
	"September": 9, "October": 10, "November": 11, "December": 12
}


class BonusRequest(Document):
	def before_insert(self):
		"""Set default effective_year to current year if not provided."""
		if not self.effective_year:
			self.effective_year = getdate(nowdate()).year

	def validate(self):
		self.validate_self_request()
		self.validate_effective_month()
		self.validate_justification()

	def validate_self_request(self):
		"""Prevent users from creating a bonus request for themselves."""
		current_user = frappe.session.user
		if current_user == "Administrator":
			return

		employee_user_id = frappe.db.get_value("Employee", self.employee, "user_id")
		if employee_user_id and employee_user_id == current_user:
			frappe.throw(
				_("Compliance Error: You cannot initiate a bonus request for yourself."),
				title=_("Self-Request Not Allowed")
			)

	def validate_effective_month(self):
		"""Ensure effective month is not in the past."""
		if not self.effective_month or not self.effective_year:
			return

		today = getdate(nowdate())
		current_month = today.month
		current_year = today.year

		selected_month = MONTH_MAP.get(self.effective_month)
		selected_year = cint(self.effective_year)

		if not selected_month:
			return

		if selected_year < current_year or (selected_year == current_year and selected_month < current_month):
			frappe.throw(
				_("Validation Error: Effective Month cannot be in the past."),
				title=_("Invalid Effective Month")
			)

	def validate_justification(self):
		"""Ensure justification is provided when Others is checked."""
		if self.others and not self.justification:
			frappe.throw(
				_("Justification is mandatory when 'Others' performance criteria is checked."),
				title=_("Missing Justification")
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
def create_bulk_bonus_requests(
	employees: str,
	bonus_amount: float,
	effective_month: str,
	effective_year: int,
	posting_date: str,
	increased_productivity: int = 0,
	improved_work_processes: int = 0,
	significant_effort: int = 0,
	star_performer: int = 0,
	others: int = 0,
	justification: str = ""
):
	"""Create individual Bonus Request records in Draft state for selected employees."""
	import json

	employees = json.loads(employees) if isinstance(employees, str) else employees

	if not employees:
		frappe.throw(_("No employees selected."))

	effective_year = cint(effective_year)
	bonus_amount = float(bonus_amount)

	# Validate effective month is not in the past
	today = getdate(nowdate())
	selected_month = MONTH_MAP.get(effective_month)
	if not selected_month:
		frappe.throw(_("Invalid Effective Month."))

	if effective_year < today.year or (effective_year == today.year and selected_month < today.month):
		frappe.throw(
			_("Validation Error: Effective Month cannot be in the past."),
			title=_("Invalid Effective Month")
		)

	# Validate at least one performance criteria
	if not any([cint(increased_productivity), cint(improved_work_processes),
				cint(significant_effort), cint(star_performer), cint(others)]):
		frappe.throw(_("Please select at least one Performance Criteria."))

	if cint(others) and not justification:
		frappe.throw(_("Justification is mandatory when 'Others' is checked."))

	# Enqueue to background job
	frappe.enqueue(
		method="one_fm.one_fm.doctype.bonus_request.bonus_request._create_bulk_bonus_requests_bg",
		queue="long",
		timeout=1500,
		employees=employees,
		bonus_amount=bonus_amount,
		effective_month=effective_month,
		effective_year=effective_year,
		posting_date=posting_date,
		increased_productivity=cint(increased_productivity),
		improved_work_processes=cint(improved_work_processes),
		significant_effort=cint(significant_effort),
		star_performer=cint(star_performer),
		others=cint(others),
		justification=justification,
		user=frappe.session.user
	)

	frappe.msgprint(
		_("Bonus Request generation has been queued for {0} employee(s). You will be notified once completed.").format(len(employees)),
		title=_("Generation Started"),
		indicator="blue"
	)


def _create_bulk_bonus_requests_bg(
	employees, bonus_amount, effective_month, effective_year,
	posting_date, increased_productivity, improved_work_processes,
	significant_effort, star_performer, others, justification, user
):
	"""Background job to create individual Bonus Request records."""
	created_count = 0
	failed_count = 0

	for emp in employees:
		try:
			bonus_request = frappe.get_doc({
				"doctype": "Bonus Request",
				"posting_date": posting_date or nowdate(),
				"employee": emp,
				"bonus_amount": bonus_amount,
				"effective_month": effective_month,
				"effective_year": effective_year,
				"increased_productivity": increased_productivity,
				"improved_work_processes": improved_work_processes,
				"significant_effort": significant_effort,
				"star_performer": star_performer,
				"others": others,
				"justification": justification if others else ""
			})
			bonus_request.insert(ignore_permissions=True)
			created_count += 1
		except Exception:
			failed_count += 1
			frappe.log_error(
				title=_("Bulk Bonus Request - Failed to create for {0}").format(emp),
				message=frappe.get_traceback()
			)

	frappe.db.commit()

	frappe.publish_realtime(
		"msgprint",
		{
			"message": _("Bulk Bonus Request completed: {0} created, {1} failed.").format(
				created_count, failed_count
			),
			"title": _("Bulk Bonus Request Complete"),
			"indicator": "green" if failed_count == 0 else "orange"
		},
		user=user
	)
