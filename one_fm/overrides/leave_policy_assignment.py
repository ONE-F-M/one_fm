import frappe

from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
    LeavePolicyAssignment
)


class LeavePolicyAssignmentOverride(LeavePolicyAssignment):
	# overide default class
	@frappe.whitelist()
	def grant_leave_alloc_for_employee(self):
		leave_allocations = {}
		if not self.leaves_allocated:
			leave_type_details = get_leave_type_detail()

			leave_policy = frappe.get_doc("Leave Policy", self.leave_policy)
			date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")

			for leave_policy_detail in leave_policy.leave_policy_details:
				leave_details = leave_type_details.get(leave_policy_detail.leave_type)
				if not leave_type_details.get(leave_policy_detail.leave_type).is_lwp:
					allocate_leave = True
					new_leaves_allocate = leave_policy_detail.annual_allocation

					# Annual Leave allocated by scheduler, initially allocate 0
					if leave_type_details.get(leave_policy_detail.leave_type).one_fm_is_paid_annual_leave == 1:
						default_annual_leave_balance = frappe.db.get_value('Company', {"name": frappe.defaults.get_user_default("company")}, 'default_annual_leave_balance')
						new_leaves_allocate = default_annual_leave_balance/365

					# Hajj Leave is allocated for employees who do not perform hajj before
					if leave_type_details.get(leave_policy_detail.leave_type).one_fm_is_hajj_leave == 1 and \
						frappe.db.get_value("Employee", self.employee, "went_to_hajj"):
						allocate_leave = False

					if allocate_leave:
						leave_allocation, new_leaves_allocated = self.create_leave_allocation(
							new_leaves_allocate,
							leave_details, date_of_joining
						)

						leave_allocations[leave_policy_detail.leave_type] = {"name": leave_allocation, "leaves": new_leaves_allocated}

			self.db_set("leaves_allocated", 1)
		return leave_allocations

	def create_leave_allocation(self, annual_allocation, leave_details, date_of_joining):
		# Creates leave allocation for the given employee in the provided leave period
		carry_forward = self.carry_forward
		if self.carry_forward and not leave_details.is_carry_forward:
			carry_forward = 0

		new_leaves_allocated = self.get_new_leaves(annual_allocation, leave_details, date_of_joining)

		allocation = frappe.get_doc(
			dict(
				doctype="Leave Allocation",
				employee=self.employee,
				leave_type=leave_details.name,
				from_date=self.effective_from,
				to_date=self.effective_to,
				new_leaves_allocated=new_leaves_allocated,
				leave_period=self.leave_period if self.assignment_based_on == "Leave Policy" else "",
				leave_policy_assignment=self.name,
				leave_policy=self.leave_policy,
				carry_forward=carry_forward,
			)
		)
		allocation.save(ignore_permissions=True)
		allocation.submit()
		return allocation.name, new_leaves_allocated
	

def get_leave_type_detail():
	leave_type_details = frappe._dict()
	leave_types = frappe.get_all(
		"Leave Type",
		fields=[
			"name",
			"is_lwp",
			"is_earned_leave",
			"is_compensatory",
			"allocate_on_day",
			"is_carry_forward",
			"expire_carry_forwarded_leaves_after_days",
			"earned_leave_frequency",
			"rounding",
			"one_fm_is_hajj_leave",
			"one_fm_is_paid_sick_leave",
			"one_fm_is_paid_annual_leave"
		],
	)
	for d in leave_types:
		leave_type_details.setdefault(d.name, d)
	return leave_type_details
