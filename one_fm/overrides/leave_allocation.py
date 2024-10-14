import frappe
from frappe.utils import getdate
from frappe import _
from hrms.hr.doctype.leave_allocation.leave_allocation import LeaveAllocation

class LeaveAllocationOverride(LeaveAllocation):
    def validate(self):
        super().validate()
        self.validate_employee_gender()
    
    def validate_employee_gender(self):
        gender  = frappe.db.get_value("Employee", self.employee, "gender")
        if gender == "Male" and self.leave_type == "Maternity Leave":
            frappe.throw("Maternity Leave allocation is only allowed for female workers.")


@frappe.whitelist()
def get_annual_leave_allocation(from_date, leave_policy_assignment, employee):
    employee = frappe.db.get_values("Employee", employee, ["status", "employee_name"], as_dict=1)
    if employee[0].status == "Left":
        frappe.throw(_(f"Employee: {employee[0].employee_name} has already left the company."))

    leave_policy = frappe.get_value("Leave Policy Assignment", leave_policy_assignment, "leave_policy")
    annual_leave_allocation = frappe.get_value("Leave Policy Detail", {"parent": leave_policy, "leave_type": "Annual Leave"}, "annual_allocation")

    days_passed = getdate() - getdate(from_date)

    calculated_leave_allocation = (annual_leave_allocation / 365) * days_passed.days
    return calculated_leave_allocation
