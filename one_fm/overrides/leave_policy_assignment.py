import frappe

from erpnext.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
    LeavePolicyAssignment, get_leave_type_details,
)


class LeavePolicyAssignmentOverride(LeavePolicyAssignment):
    # overide default class
    @frappe.whitelist()
    def grant_leave_alloc_for_employee(self):
        if not self.leaves_allocated:
            leave_allocations = {}
            leave_type_details = get_leave_type_details()

            leave_policy = frappe.get_doc("Leave Policy", self.leave_policy)
            date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")

            for leave_policy_detail in leave_policy.leave_policy_details:
                if not leave_type_details.get(leave_policy_detail.leave_type).is_lwp:
                    leave_allocation, new_leaves_allocated = self.create_leave_allocation(
                        leave_policy_detail.leave_type, leave_policy_detail.annual_allocation,
                        leave_type_details, date_of_joining
                    )

                    leave_allocations[leave_policy_detail.leave_type] = {"name": leave_allocation, "leaves": new_leaves_allocated}

            self.db_set("leaves_allocated", 1)
            return leave_allocations
