# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, format_date, getdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.setup.doctype.employee.employee import is_holiday
from hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request import (
	CompensatoryLeaveRequest,
)
from hrms.hr.utils import create_additional_leave_ledger_entry


class CompensatoryLeaveRequestOverride(CompensatoryLeaveRequest):
	"""Credit compensatory leave without requiring a Leave Period.

	Standard HRMS ``on_submit`` throws "No Leave Period Found" when no active
	Leave Period covers the comp-leave-valid-from date. ONE FM allocates leave
	by daily earning against the Leave Policy Assignment (joining-date based)
	and does not maintain Leave Periods, so this override credits the leave
	directly:

	  * If the employee already has an active Leave Allocation for the leave
	    type covering the valid-from date, extend it (same as HRMS).
	  * Otherwise create a new Leave Allocation spanning the current fiscal
	    year instead of a Leave Period.

	``on_cancel`` is inherited unchanged — it only reverses ``leave_allocation``
	and never touches Leave Period.
	"""

	def on_submit(self):
		date_difference = date_diff(self.work_end_date, self.work_from_date) + 1
		if self.half_day:
			date_difference -= 0.5

		# Compensatory leave becomes valid the day after the worked day(s).
		comp_leave_valid_from = add_days(self.work_end_date, 1)

		leave_allocation = self.get_existing_allocation(comp_leave_valid_from)
		if leave_allocation:
			# Extend the existing allocation (mirrors standard HRMS behaviour).
			leave_allocation.new_leaves_allocated += date_difference
			leave_allocation.validate()
			leave_allocation.db_set("new_leaves_allocated", leave_allocation.total_leaves_allocated)
			leave_allocation.db_set("total_leaves_allocated", leave_allocation.total_leaves_allocated)

			# Generate the additional ledger entry for the new compensatory leaves.
			create_additional_leave_ledger_entry(
				leave_allocation, date_difference, comp_leave_valid_from
			)
		else:
			leave_allocation = self.create_leave_allocation_without_period(
				comp_leave_valid_from, date_difference
			)

		self.db_set("leave_allocation", leave_allocation.name)

		self.create_draft_leave_application()

	def create_draft_leave_application(self):
		"""
		Generate the Draft Leave Application for the claimed compensatory day off
		(WI-001696), so the day off shows up in the employee's attendance and roster.

		Only applies to Compensatory Leave Requests raised by the Overtime Request
		workflow: the compensatory day off date the employee selected lives on the
		Overtime Request, not here, so a request with no Overtime Request behind it has
		no date to apply for and is skipped.

		The application is left in "Draft" (docstatus 0) and owned by Administrator, per
		the AC - HR reviews and routes it.
		"""
		overtime_request = frappe.db.get_value(
			"Overtime Request",
			{"compensatory_leave_request": self.name, "docstatus": ["!=", 2]},
			["name", "compensatory_day_off"],
			as_dict=True,
		)
		if not overtime_request or not overtime_request.compensatory_day_off:
			return

		# Idempotent: never raise a second application for the same request.
		existing = frappe.db.exists(
			"Leave Application",
			{"custom_compensatory_leave_request": self.name, "docstatus": ["!=", 2]},
		)
		if existing:
			return

		day_off = getdate(overtime_request.compensatory_day_off)

		leave_application = frappe.new_doc("Leave Application")
		leave_application.employee = self.employee
		# The leave type credited by this request - in the Overtime Request flow this is
		# the Holiday Compensatory Leave Type from HR and Payroll Additional Settings.
		# Using it (rather than re-reading the setting) guarantees the application draws
		# on the allocation that was just credited.
		leave_application.leave_type = self.leave_type
		leave_application.from_date = day_off
		leave_application.to_date = day_off
		leave_application.resumption_date = get_next_working_day(self.employee, day_off)
		leave_application.custom_compensatory_leave_request = self.name
		leave_application.description = _(
			"Auto-generated from Compensatory Leave Request {0} (Overtime Request {1})."
		).format(self.name, overtime_request.name)
		# frappe.Document.insert only defaults `owner` when it is unset, so this stands.
		leave_application.owner = "Administrator"

		try:
			leave_application.flags.ignore_permissions = True
			leave_application.insert(ignore_permissions=True)
		except Exception:
			# The leave has already been credited and the Overtime Request completed;
			# a rejected draft (overlapping leave, insufficient balance, a mandatory
			# approver) must not roll either of those back. Log it and let HR raise the
			# application by hand.
			frappe.log_error(
				title=_("Could not auto-create Leave Application for {0}").format(self.name),
				message=frappe.get_traceback(),
			)
			frappe.msgprint(
				_("Compensatory leave was credited, but the Draft Leave Application for {0} could not be created automatically. Please create it manually.").format(
					format_date(day_off)
				),
				indicator="orange",
				alert=True,
			)
			return

		# "Draft" is the first workflow state after save; set it after insert so the
		# Leave Application workflow does not overwrite it during validation.
		if leave_application.meta.get_field("workflow_state"):
			leave_application.db_set("workflow_state", "Draft", update_modified=False)

		frappe.msgprint(
			_("Draft Leave Application {0} created for {1}.").format(
				leave_application.name, format_date(day_off)
			),
			indicator="green",
			alert=True,
		)

	def create_leave_allocation_without_period(self, comp_leave_valid_from, date_difference):
		"""Create a Leave Allocation for the comp leave, scoped to the fiscal year.

		Used when no active Leave Allocation already covers the valid-from date.
		The allocation runs from the valid-from date to the end of the fiscal
		year that contains it, so the credited leave stays usable without any
		Leave Period being configured.
		"""
		company = frappe.db.get_value("Employee", self.employee, "company")

		fiscal_year = get_fiscal_year(getdate(comp_leave_valid_from), company=company)
		if not fiscal_year:
			frappe.throw(
				_("No Fiscal Year found for the date {0}. Please create one first.").format(
					format_date(comp_leave_valid_from)
				),
				title=_("No Fiscal Year Found"),
			)
		year_end_date = fiscal_year[2]

		# A later allocation for the same employee and leave type may already own part of
		# that range - HRMS rejects overlapping allocations, so running to fiscal-year end
		# unconditionally made back-dated compensatory leave impossible to credit once a
		# later allocation existed. End the day before the next one starts instead; the
		# window still covers the compensatory day off, which falls within 7 days of the
		# worked holiday.
		next_allocation_start = frappe.db.get_value(
			"Leave Allocation",
			{
				"employee": self.employee,
				"leave_type": self.leave_type,
				"docstatus": 1,
				"from_date": [">", getdate(comp_leave_valid_from)],
			},
			"from_date",
			order_by="from_date asc",
		)
		if next_allocation_start:
			year_end_date = min(getdate(year_end_date), add_days(getdate(next_allocation_start), -1))

		is_carry_forward = frappe.db.get_value("Leave Type", self.leave_type, "is_carry_forward")

		allocation = frappe.get_doc(
			dict(
				doctype="Leave Allocation",
				employee=self.employee,
				employee_name=self.employee_name,
				leave_type=self.leave_type,
				from_date=comp_leave_valid_from,
				to_date=year_end_date,
				carry_forward=cint(is_carry_forward),
				new_leaves_allocated=date_difference,
				total_leaves_allocated=date_difference,
				description=self.reason,
			)
		)
		allocation.insert(ignore_permissions=True)
		allocation.submit()
		return allocation


def get_next_working_day(employee, from_date, max_lookahead_days=30):
	"""
	First working day strictly after from_date, skipping the employee's holidays.

	Same holiday-list walk as one_fm.overrides.attendance_request, bounded so a holiday
	list that marks every day cannot spin forever.
	"""
	next_date = add_days(getdate(from_date), 1)

	for _attempt in range(max_lookahead_days):
		if not is_holiday(employee, next_date):
			return next_date
		next_date = add_days(next_date, 1)

	return next_date
