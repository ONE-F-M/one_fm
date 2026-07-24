# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, format_date, getdate

from erpnext.accounts.utils import get_fiscal_year
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
