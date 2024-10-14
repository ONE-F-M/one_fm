import frappe

from hrms.hr.doctype.leave_allocation.leave_allocation import LeaveAllocation


class LeaveAllocationOverride(LeaveAllocation):
    def validate(self):
        super().validate()
        self.validate_employee_gender()
        self.validate_hajj_leave()
    
    def validate_employee_gender(self):
        gender  = frappe.db.get_value("Employee", self.employee, "gender","went_to_hajj")
        if gender == "Male" and self.leave_type == "Maternity Leave":
            frappe.throw("Maternity Leave allocation is only allowed for female workers.")

    def validate_hajj_leave(self):
        religion, went_to_hajj = frappe.db.get_value("Employee", self.employee, ["one_fm_religion", "went_to_hajj"])
        if religion != "Muslim" or (religion == "Muslim" and went_to_hajj  == True):
            frappe.throw("Hajj Leave allocation is only allowed for a muslim staff Who has not performed Hajj before.")

        



