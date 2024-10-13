import frappe

from hrms.hr.doctype.leave_allocation.leave_allocation import LeaveAllocation


class LeaveAllocationOverride(LeaveAllocation):
    def validate(self):
        super().validate()
        self.validate_employee_gender()
    
    def validate_employee_gender(self):
        gender  = frappe.db.get_value("Employee", self.employee, "gender")
        if gender == "Male" and self.leave_type == "Maternity Leave":
            frappe.throw("Maternity Leave allocation is only allowed for female workers.")

