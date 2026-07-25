# Copyright (c) 2021, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import (
	time_diff_in_hours, getdate, get_first_day, get_last_day,
	flt, rounded, now_datetime, get_datetime, add_days
)
from frappe import _
from frappe.query_builder.functions import Sum
from one_fm.api.notification import create_notification_log, get_employee_user_id

# Hours of unredeemed public holiday overtime that earn one compensatory day off.
COMPENSATORY_DAY_OFF_THRESHOLD_HOURS = 9

# Workflow states whose overtime hours count towards the cumulative unredeemed balance:
# everything the employee has actually submitted. "Draft" is excluded so an abandoned
# draft cannot inflate the balance, and Rejected/Cancelled never count.
ACCRUING_WORKFLOW_STATES = (
	"Pending Acceptance by Employee",
	"Pending Line Manager",
	"Pending Payroll Officer",
	"Pending Finance Manager",
	"Completed",
)


def get_unredeemed_balance(employee, exclude=None):
	"""
	Unredeemed public holiday overtime hours accrued across an employee's requests.

	Accrued hours minus 9 for every request that has already been redeemed as a
	compensatory day off. `exclude` drops one request from the tally - callers pass the
	document being saved, whose in-memory hours have not been written yet.
	"""
	if not employee:
		return 0.0

	OvertimeRequest = frappe.qb.DocType("Overtime Request")

	rows = (
		frappe.qb.from_(OvertimeRequest)
		.select(OvertimeRequest.overtime_hours, OvertimeRequest.compensatory_leave_request)
		.where(
			(OvertimeRequest.employee == employee)
			& (OvertimeRequest.overtime_type == "Overtime on Public Holiday")
			& (OvertimeRequest.workflow_state.isin(ACCRUING_WORKFLOW_STATES))
			& (OvertimeRequest.docstatus != 2)
			& (OvertimeRequest.name != (exclude or ""))
		)
	).run(as_dict=True)

	accrued = sum(flt(row.overtime_hours) for row in rows)
	redeemed = COMPENSATORY_DAY_OFF_THRESHOLD_HOURS * sum(
		1 for row in rows if row.compensatory_leave_request
	)

	return flt(accrued - redeemed, 2)


class OvertimeRequest(Document):

	def before_insert(self):
		if not self.requested_by:
			self.requested_by = frappe.session.user

	def validate(self):
		self.validate_duplicate()
		self.validate_leave_overlap()
		self.calculate_overtime_hours()
		self.calculate_yearly_overtime_hours()
		self.set_cumulative_unredeemed_balance()
		self.set_compensatory_day_off_eligibility()
		self.validate_compensatory_day_off()
		self.validate_yearly_overtime_limit()
		self.validate_attendance_verification_timing()
		self.validate_attendance_marked()

	def on_update(self):
		self.create_attendance_on_verification()
		self.create_compensatory_leave_request()
		self.workflow_notification()

	def validate_duplicate(self):
		"""Check for duplicate overtime requests for the same employee and date."""
		filters = {
			"employee": self.employee,
			"date": self.date,
			"name": ["!=", self.name],
			"start_time": self.start_time,
			"end_time": self.end_time
		}
		exists_overtime_request = frappe.db.exists("Overtime Request", filters)
		if exists_overtime_request:
			frappe.throw(
				_("Already exists an Overtime Request {0} for employee {1} on {2}!".format(
					exists_overtime_request, self.employee, self.date
				))
			)

	def validate_leave_overlap(self):
		"""
		Block save if the employee has approved leave on the overtime date
		and this is a self-request. For manager requests, allow but log a comment.
		"""
		if not self.employee or not self.date:
			return

		overtime_date = getdate(self.date)

		LeaveApplication = frappe.qb.DocType("Leave Application")
		leave = (
			frappe.qb.from_(LeaveApplication)
			.select(LeaveApplication.name, LeaveApplication.leave_type)
			.where(LeaveApplication.employee == self.employee)
			.where(LeaveApplication.status == "Approved")
			.where(LeaveApplication.docstatus == 1)
			.where(LeaveApplication.from_date <= overtime_date)
			.where(LeaveApplication.to_date >= overtime_date)
		).run(as_dict=True)

		if not leave:
			return

		# Check if this is a self-request
		employee_user = frappe.db.get_value("Employee", self.employee, "user_id")
		is_self_request = (self.requested_by == employee_user)

		if is_self_request:
			frappe.throw(
				_("You cannot create an Overtime Request on {0} as you have an approved {1} on this day.".format(
					frappe.format(overtime_date, {"fieldtype": "Date"}),
					leave[0].leave_type
				))
			)
		

	def calculate_overtime_hours(self):
		"""Calculate overtime hours from start_time and end_time.
		Handles overnight spans (e.g. 18:00 → 04:00 = 10 hours).
		"""
		if self.start_time and self.end_time:
			hours = time_diff_in_hours(self.end_time, self.start_time)
			# If negative, the overtime crosses midnight — add 24 hours
			if hours < 0:
				hours += 24
			self.overtime_hours = rounded(hours, 2)

	def calculate_yearly_overtime_hours(self):
		"""
		Calculate the cumulative yearly overtime hours for this employee
		in the current calendar year, including the current record's hours.
		"""
		if not self.employee or not self.overtime_hours:
			return

		# Get current calendar year boundaries
		overtime_date = getdate(self.date) if self.date else getdate()
		year_start = getdate(f"{overtime_date.year}-01-01")
		year_end = getdate(f"{overtime_date.year}-12-31")

		# Sum all approved/submitted overtime hours for this employee in the current year
		OvertimeRequest = frappe.qb.DocType("Overtime Request")
		result = (
			frappe.qb.from_(OvertimeRequest)
			.select(Sum(OvertimeRequest.overtime_hours).as_("total_hours"))
			.where(OvertimeRequest.employee == self.employee)
			.where(OvertimeRequest.docstatus == 1)
			.where(OvertimeRequest.date >= year_start)
			.where(OvertimeRequest.date <= year_end)
			.where(OvertimeRequest.name != self.name)
		).run(as_dict=True)

		past_hours = flt(result[0].total_hours) if result else 0.0
		self.yearly_overtime_hours = flt(past_hours + flt(self.overtime_hours), 2)

	def set_cumulative_unredeemed_balance(self):
		"""
		Maintain the running balance of unredeemed public holiday overtime (WI-001695).

		The balance is the employee's accrued public holiday overtime hours minus 9 for
		every compensatory day off already redeemed. It is recomputed from the employee's
		requests on every save rather than incremented in place, so it is idempotent and
		self-healing: cancelling or editing an earlier request corrects the total.

		Only public holiday overtime carries a balance; any other Overtime Type stores 0.
		"""
		if self.overtime_type != "Overtime on Public Holiday":
			self.cumulative_unredemmed_balance = 0
			return

		balance = get_unredeemed_balance(self.employee, exclude=self.name)

		# This request contributes its own hours once the employee has submitted it.
		if self.workflow_state in ACCRUING_WORKFLOW_STATES:
			balance += flt(self.overtime_hours)

		# ...and gives 9 of them back if it has already been redeemed.
		if self.compensatory_leave_request:
			balance -= COMPENSATORY_DAY_OFF_THRESHOLD_HOURS

		self.cumulative_unredemmed_balance = flt(balance, 2)

	def set_compensatory_day_off_eligibility(self):
		"""
		Detect eligibility for a compensatory day off.

		Eligible when the Overtime Type is "Overtime on Public Holiday" AND the employee's
		cumulative unredeemed balance has reached 9 hours (WI-001695). The threshold is
		cumulative across public holidays, not per request: 3 + 4 + 3 hours earns a
		compensatory day off just as a single 10-hour holiday does.

		In every other case the flag resets to 0 and the selected Compensatory Day Off
		clears - except on a request that has already been redeemed, where the flag and
		date are kept so the record (and the Compensatory Day Off section) survives the
		balance dropping back below the threshold.
		"""
		if self.compensatory_leave_request:
			self.eligible_for_compensatory_day_off = 1
			return

		if (
			self.overtime_type == "Overtime on Public Holiday"
			and flt(self.cumulative_unredemmed_balance) >= COMPENSATORY_DAY_OFF_THRESHOLD_HOURS
		):
			self.eligible_for_compensatory_day_off = 1
		else:
			self.eligible_for_compensatory_day_off = 0
			self.compensatory_day_off = None

	# Workflow states from which a Compensatory Day Off date is mandatory.
	# Before these (Draft, Pending Acceptance by Employee) the date is optional:
	# a Line Manager may pre-fill it when routing to the employee, and the
	# employee adds/confirms it when accepting the request.
	COMPENSATORY_DAY_OFF_REQUIRED_STATES = (
		"Pending Line Manager",
		"Pending Payroll Officer",
		"Pending Finance Manager",
		"Completed",
	)

	def validate_compensatory_day_off(self):
		"""
		Enforce the Compensatory Day Off rules when the request is eligible.

		Only applies when eligible_for_compensatory_day_off is set (Overtime Type
		is "Overtime on Public Holiday" and hours are 9 or more):
		  1. Whenever a Compensatory Day Off date is provided, it must fall within
			 7 days of the overtime date, i.e. between the overtime date and the
			 overtime date + 7 days (inclusive). This applies at every stage so a
			 Line Manager cannot pre-fill an out-of-window date.
		  2. The date is required only once the employee has accepted the request
			 (workflow state "Pending Line Manager" onward). At the Line Manager
			 routing stage it is optional so the employee can add it on review.
		"""
		if not self.eligible_for_compensatory_day_off:
			return

		# Require the date once the request has moved to the employee-accepted
		# stage (or beyond). It stays optional while the Line Manager routes it.
		if (
			not self.compensatory_day_off
			and self.workflow_state in self.COMPENSATORY_DAY_OFF_REQUIRED_STATES
		):
			frappe.throw(
				_("Compensatory Day Off date is required when Overtime Type is "
				  "'Overtime on Public Holiday' and hours are 9 or more.")
			)

		if not self.compensatory_day_off:
			return

		overtime_date = getdate(self.date)
		window_end = add_days(overtime_date, 7)
		comp_off = getdate(self.compensatory_day_off)

		if comp_off < overtime_date or comp_off > window_end:
			frappe.throw(
				_("Compensatory Day Off date must be within 7 days of the overtime "
				  "date ({0} to {1}).").format(overtime_date, window_end)
			)

	def validate_yearly_overtime_limit(self):
		"""
		Block save if yearly overtime hours strictly exceed 180.
		Story 4: Fatal error when yearly_overtime_hours > 180.
		"""
		if flt(self.yearly_overtime_hours) > 180:
			frappe.throw(
				_("This request cannot be submitted. Adding these overtime hours "
				  "will exceed the maximum allowable limit of 180 overtime hours per year.")
			)

	def validate_attendance_verification_timing(self):
		"""Block transition to 'Pending Payroll Officer' before overtime end time."""
		if self.workflow_state != "Pending Payroll Officer":
			return
		if not self.date or not self.end_time:
			return

		overtime_end = get_datetime(f"{self.date} {self.end_time}")
		if self.start_time:
			overtime_start = get_datetime(f"{self.date} {self.start_time}")
			if overtime_end <= overtime_start:
				overtime_end = frappe.utils.add_days(overtime_end, 1)
		if now_datetime() < overtime_end:
			frappe.throw(
				_("You cannot verify attendance until the scheduled overtime end time has passed.")
			)

	def validate_attendance_marked(self):
		"""Require Present or Absent to be checked before transitioning to 'Pending Payroll Officer'."""
		if self.workflow_state != "Pending Payroll Officer":
			return

		if not self.present and not self.absent:
			frappe.throw(
				_("Please mark the employee as Present or Absent before verifying attendance.")
			)

	def create_attendance_on_verification(self):
		"""Auto-create and submit an Attendance record when the Line Manager verifies attendance.

		Triggered on transition to 'Pending Payroll Officer'.
		Maps Employee, Attendance Date, Status, Roster Type, and reference fields
		from this Overtime Request.
		"""
		if self.workflow_state != "Pending Payroll Officer":
			return

		if not self.has_value_changed("workflow_state"):
			return

		# Determine attendance status from checkboxes
		attendance_status = "Present" if self.present else "Absent"

		# Check for existing Attendance with same employee + date + roster_type
		existing = frappe.db.exists("Attendance", {
			"employee": self.employee,
			"attendance_date": self.date,
			"roster_type": "Over-Time",
			"docstatus": ["!=", 2]
		})

		if existing:
			frappe.msgprint(
				_("Attendance {0} already exists for {1} on {2} with roster type Over-Time. Skipping creation.".format(
					existing, self.employee, self.date
				)),
				alert=True,
				indicator="orange"
			)
			return

		# Fetch company from the Employee record
		company = frappe.db.get_value("Employee", self.employee, "company")

		attendance = frappe.get_doc({
			"doctype": "Attendance",
			"employee": self.employee,
			"attendance_date": self.date,
			"status": attendance_status,
			"roster_type": "Over-Time",
			"reference_doctype": "Overtime Request",
			"reference_docname": self.name,
			"company": company,
			"working_hours": flt(self.overtime_hours, 2) if attendance_status == "Present" else 0,
		})
		attendance.insert(ignore_permissions=True)
		attendance.submit()

		frappe.msgprint(
			_("Attendance {0} has been created and submitted for {1}.".format(
				attendance.name, self.full_name or self.employee
			)),
			alert=True,
			indicator="green"
		)

	def create_compensatory_leave_request(self):
		"""Auto-create (or link) a Compensatory Leave Request when the request is Completed.

		Only runs for eligible Public Holiday overtime (Overtime Type
		"Overtime on Public Holiday" and hours >= 9) where the employee was
		marked Present and a Compensatory Day Off date is set.

		To avoid a duplicate / double leave credit, an existing Compensatory
		Leave Request for the same employee and overtime (worked) date is reused
		— such a request is normally already created by the holiday attendance
		hook (see one_fm.one_fm.utils.manage_attendance_on_holiday) when the
		Over-Time attendance is submitted at the "Pending Payroll Officer" stage.
		If none exists, a new one is created and submitted so the leave balance
		is credited. Either way the request is back-linked to this document.

		The work dates map to the worked holiday date (required for the
		Compensatory Leave Request to validate/submit — that day must be a
		holiday with Present attendance). The Compensatory Day Off date itself
		stays on this Overtime Request (compensatory_day_off).
		"""
		if self.workflow_state != "Completed":
			return

		if not self.has_value_changed("workflow_state"):
			return

		# Only Public Holiday overtime of 9+ hours earns a compensatory day off.
		if not self.eligible_for_compensatory_day_off:
			return

		# Already linked (e.g. on re-save) — nothing to do.
		if self.compensatory_leave_request:
			return

		# Comp leave is only credited when the employee actually worked (Present).
		if not self.present:
			return

		# The Compensatory Day Off date is mandatory at this stage (enforced by
		# validate_compensatory_day_off); guard defensively.
		if not self.compensatory_day_off:
			return

		leave_type = frappe.db.get_single_value(
			"HR and Payroll Additional Settings", "holiday_compensatory_leave_type"
		)
		if not leave_type:
			frappe.throw(
				_("Please Contact HRD to configure Leave Type for Holiday Compensatory Leave Request !!")
			)

		# Reuse an existing (non-cancelled) request for this employee + worked date.
		existing = frappe.db.exists("Compensatory Leave Request", {
			"employee": self.employee,
			"work_from_date": self.date,
			"work_end_date": self.date,
			"docstatus": ["!=", 2],
		})
		if existing:
			self.db_set("compensatory_leave_request", existing)
			self.redeem_compensatory_day_off_hours()
			return

		clr = frappe.new_doc("Compensatory Leave Request")
		clr.employee = self.employee
		clr.leave_type = leave_type
		clr.work_from_date = self.date
		clr.work_end_date = self.date
		clr.reason = _("Auto-generated from Overtime Request {0}").format(self.name)
		clr.insert(ignore_permissions=True)
		clr.submit()

		self.db_set("compensatory_leave_request", clr.name)
		self.redeem_compensatory_day_off_hours()

		frappe.msgprint(
			_("Compensatory Leave Request {0} has been created and submitted for {1}.").format(
				clr.name, self.full_name or self.employee
			),
			alert=True,
			indicator="green",
		)

	def redeem_compensatory_day_off_hours(self):
		"""
		Spend 9 hours of the cumulative balance on the compensatory day off just raised
		(WI-001695 AC4): a balance of 10 becomes 1, and the remainder carries forward to
		count towards the employee's next compensatory day off.

		One redemption per request. An employee sitting on 20 unredeemed hours redeems 9
		here and keeps 11, which re-triggers the prompt on their next public holiday
		overtime request rather than raising two leave requests at once.

		Written with db_set because the linking happens in on_update, after validate has
		already stored the pre-redemption balance.
		"""
		self.db_set(
			"cumulative_unredemmed_balance",
			flt(flt(self.cumulative_unredemmed_balance) - COMPENSATORY_DAY_OFF_THRESHOLD_HOURS, 2),
		)

	def workflow_notification(self):
		"""
		Send notifications based on workflow state transitions.
		- Pending Acceptance by Employee: notify the employee
		- Pending Line Manager: notify the line manager
		- Pending Payroll Officer: handled by assignment rule
		- Completed: notify the requester
		- Rejected: notify the requester
		"""
		date = getdate(self.date).strftime("%d-%m-%Y")

		if self.workflow_state == "Pending Acceptance by Employee":
			message = _("{0} has Requested for {1} Hours Overtime on {2}.".format(
				self.full_name or self.employee, rounded(self.overtime_hours, 2), date
			))
			employee_user = frappe.db.get_value("Employee", self.employee, "user_id")
			if employee_user:
				create_notification_log(message, message, [employee_user], self)

		elif self.workflow_state == "Pending Line Manager":
			reports_to_user = self.reports_to_user
			if reports_to_user:
				message = _("{0} has Requested for {1} Hours Overtime on {2}.".format(
					self.full_name or self.employee, rounded(self.overtime_hours, 2), date
				))
				create_notification_log(message, message, [reports_to_user], self)

		elif self.workflow_state == "Completed":
			message = _("The Overtime Request for {0} Hours on {1} has been Completed.".format(
				rounded(self.overtime_hours, 2), date
			))
			notify_user = self.requested_by or frappe.db.get_value("Employee", self.employee, "user_id")
			if notify_user:
				create_notification_log(message, message, [notify_user], self)

		elif self.workflow_state == "Rejected":
			message = _("The Overtime Request for {0} Hours on {1} has been Rejected.".format(
				rounded(self.overtime_hours, 2), date
			))
			notify_user = self.requested_by or frappe.db.get_value("Employee", self.employee, "user_id")
			if notify_user:
				create_notification_log(message, message, [notify_user], self)


@frappe.whitelist()
def check_leave_overlap(employee: str, overtime_date: str) -> dict:
	"""
	Check if the employee has an approved Leave Application
	that overlaps with the given overtime date.

	Returns:
		dict with keys:
			- has_leave (bool): True if overlap exists
			- employee_name (str): Full name of the employee
			- leave_type (str): Type of leave if overlap found
	"""
	overtime_date = getdate(overtime_date)

	LeaveApplication = frappe.qb.DocType("Leave Application")
	result = (
		frappe.qb.from_(LeaveApplication)
		.select(
			LeaveApplication.name,
			LeaveApplication.leave_type,
			LeaveApplication.from_date,
			LeaveApplication.to_date,
		)
		.where(LeaveApplication.employee == employee)
		.where(LeaveApplication.status == "Approved")
		.where(LeaveApplication.docstatus == 1)
		.where(LeaveApplication.from_date <= overtime_date)
		.where(LeaveApplication.to_date >= overtime_date)
	).run(as_dict=True)

	employee_name = frappe.db.get_value("Employee", employee, "employee_name") or ""

	if result:
		return {
			"has_leave": True,
			"employee_name": employee_name,
			"leave_type": result[0].leave_type,
			"leave_name": result[0].name,
		}

	return {
		"has_leave": False,
		"employee_name": employee_name,
		"leave_type": "",
		"leave_name": "",
	}


@frappe.whitelist()
def get_yearly_overtime_hours(employee: str, overtime_date: str, current_hours: float, current_name: str = "") -> float:
	"""
	Calculate the cumulative yearly overtime hours for an employee.
	Sum of all approved (docstatus=1) overtime hours in the current calendar year
	plus the current record's hours.

	Args:
		employee: Employee ID
		overtime_date: The date of the overtime request (to determine the year)
		current_hours: The current record's overtime hours
		current_name: The current record's name (to exclude from sum)

	Returns:
		float: Total yearly overtime hours including current
	"""
	overtime_date = getdate(overtime_date)
	year_start = getdate(f"{overtime_date.year}-01-01")
	year_end = getdate(f"{overtime_date.year}-12-31")

	OvertimeRequest = frappe.qb.DocType("Overtime Request")
	query = (
		frappe.qb.from_(OvertimeRequest)
		.select(Sum(OvertimeRequest.overtime_hours).as_("total_hours"))
		.where(OvertimeRequest.employee == employee)
		.where(OvertimeRequest.docstatus == 1)
		.where(OvertimeRequest.date >= year_start)
		.where(OvertimeRequest.date <= year_end)
	)

	if current_name:
		query = query.where(OvertimeRequest.name != current_name)

	result = query.run(as_dict=True)
	past_hours = flt(result[0].total_hours) if result else 0.0

	return flt(past_hours + flt(current_hours), 2)


@frappe.whitelist()
def get_projected_unredeemed_balance(
	employee: str, overtime_hours: float = 0, current_name: str = ""
) -> float:
	"""
	The cumulative unredeemed public holiday overtime balance this request would produce.

	Used by the client script to decide whether to prompt for a Compensatory Day Off,
	since the threshold is now the employee's cumulative balance and cannot be worked out
	from the hours on the form alone (WI-001695).

	Args:
		employee: Employee ID
		overtime_hours: The hours currently entered on the form
		current_name: The record's name, excluded from the tally (blank for a new record)

	Returns:
		float: Accrued unredeemed hours across the employee's requests, plus these hours
	"""
	frappe.has_permission("Overtime Request", "read", throw=True)

	return flt(get_unredeemed_balance(employee, exclude=current_name) + flt(overtime_hours), 2)
