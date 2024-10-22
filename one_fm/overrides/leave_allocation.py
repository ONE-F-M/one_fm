import frappe
from frappe.utils import getdate, rounded, flt
from frappe import _
from hrms.hr.doctype.leave_allocation.leave_allocation import LeaveAllocation

class LeaveAllocationOverride(LeaveAllocation):
    def validate(self):
        super().validate()
        self.validate_employee_gender_for_maternity()
        self.validate_hajj_leave()
    
    def validate_employee_gender_for_maternity(self):
        employees_gender  = frappe.db.get_value("Employee", self.employee, "gender")
        maternity_check  = frappe.db.get_value("Gender", employees_gender, "custom_maternity_required")
        maternity_leave_check  = frappe.db.get_value("Leave Type", self.leave_type, "custom_is_maternity")
        if not maternity_check and maternity_leave_check:
            frappe.throw("Maternity Leave allocation is only allowed for gender eligible workers.")

    def validate_hajj_leave(self):
        employee_info = frappe.db.get_value("Employee", self.employee, ["one_fm_religion", "went_to_hajj"], as_dict=True)
        religion = employee_info.get("one_fm_religion")
        religion_check  = frappe.db.get_value("Religion", religion, "custom_hajj_check_required")
        hajj_leave_check  = frappe.db.get_value("Leave Type", self.leave_type, "one_fm_is_hajj_leave")
        went_to_hajj = employee_info.get("went_to_hajj")
        if (not religion_check and hajj_leave_check) or (religion_check and went_to_hajj and hajj_leave_check):
            frappe.throw("Hajj leave allocation is only allowed for muslim staff who have not performed hajj before.")
    
    def validate_against_leave_applications(self):
        pass




@frappe.whitelist()
def update_annual_leave_allocation(name, new_leaves_allocated, from_date, leave_policy_assignment, employee):
    employee = frappe.db.get_values("Employee", employee, ["status", "employee_name"], as_dict=1)
    if employee[0].status == "Left":
        frappe.throw(_(f"Employee: {employee[0].employee_name} has already left the company."))

    leave_policy = frappe.get_value("Leave Policy Assignment", leave_policy_assignment, "leave_policy")
    annual_leave_allocation = frappe.get_value("Leave Policy Detail", {"parent": leave_policy, "leave_type": "Annual Leave"}, "annual_allocation")

    # Get days passed between today and from_date
    days_passed = getdate() - getdate(from_date)
    # Calculation = annual leave days mentioned in leave policy / 365 | e.g. 30/365 = 0.082 
    daily_earned_allocation = rounded((annual_leave_allocation / 365), precision=3)
    
    # calculation = (daily earned leave * days difference between today and from date) | e.g. 0.082 * 43 days passed 
    calculated_leave_allocation =  rounded((daily_earned_allocation * days_passed.days), precision=3)

    if flt(new_leaves_allocated) > calculated_leave_allocation:
        frappe.db.set_value("Leave Allocation", name, "new_leaves_allocated", calculated_leave_allocation)
        show_notification("Unearned leaves found", "Unearned leaves cleared", "green")
    elif flt(new_leaves_allocated) < calculated_leave_allocation:
        frappe.db.set_value("Leave Allocation", name, "new_leaves_allocated", calculated_leave_allocation)
        show_notification("Missing leave allocation found", "New leaves allocated", "green")
    else:
        show_notification("No changes made", "Leave allocation is up to date", "blue")


def show_notification(title, msg, indicator):
    frappe.msgprint(
        title=_(title),
        msg=_(msg),
        indicator=indicator
    )
        
