import frappe
from frappe.utils import getdate, add_days
from frappe.permissions import remove_user_permission
from hrms.overrides.employee_master import *
from one_fm.hiring.utils import (
    employee_after_insert, employee_before_insert, set_employee_name,
    employee_validate_attendance_by_timesheet, set_mandatory_feilds_in_employee_for_Kuwaiti,
)

class EmployeeOverride(EmployeeMaster):
    def validate(self):
        from erpnext.controllers.status_updater import validate_status
        validate_status(self.status, ["Active", "Court Case", "Absconding", "Left","Vacation"])

        self.employee = self.name
        self.set_employee_name()
        set_employee_name(self, method=None)
        self.validate_date()
        self.validate_email()
        self.validate_status()
        self.validate_reports_to()
        self.validate_preferred_email()
        update_user_doc(self)
        if self.job_applicant:
            self.validate_onboarding_process()

        if self.user_id:
            self.validate_user_details()
        else:
            existing_user_id = frappe.db.get_value("Employee", self.name, "user_id")
            if existing_user_id:
                remove_user_permission(
                    "Employee", self.name, existing_user_id)
        employee_validate_attendance_by_timesheet(self, method=None)
        validate_leaves(self)
    
def update_user_doc(doc):
    if not doc.is_new():
        old_self = doc.get_doc_before_save().status
        if doc.status in ['Left','Absconding','Court Case'] and doc.status not in [old_self] and doc.user_id:
            user_doc = frappe.get_doc('User',doc.user_id)
            if user_doc.enabled == 1:
                user_doc.enabled = 0
                user_doc.save(ignore_permissions=1)
                frappe.msgprint(f"User {doc.user_id} disabled",alert=1)
                frappe.db.commit()
        elif doc.status == "Active" and doc.status not in [old_self] and doc.user_id:
            user_doc = frappe.get_doc('User',doc.user_id)
            if user_doc.enabled == 0:
                user_doc.enabled = 1
                user_doc.save(ignore_permissions=1)
                frappe.msgprint(f"User {doc.user_id} enabled",alert=1)
                frappe.db.commit()

    def before_save(self):
        self.assign_role_profile_based_on_designation()
        if self.under_company_residency=='1':
            self.employee_id = get_new_employee_id(self.employee_id)

    def after_insert(self):
        employee_after_insert(self, method=None)
        self.assign_role_profile_based_on_designation()
    
    def before_insert(self):
        employee_before_insert(self, method=None)

    def validate_onboarding_process(self):
        validate_onboarding_process(self)

    def assign_role_profile_based_on_designation(self):
        if self.designation:
            if self.is_new():
                if self.user_id:
                    designation = self.designation
                else:
                    return
            else:
                if self.designation != self.get_doc_before_save().designation:
                    designation = self.designation
                else:
                    return
            role_profile = frappe.db.get_value("Designation", designation, "role_profile")
            if role_profile:
                user = frappe.get_doc("User", self.user_id)
                user.role_profile_name = role_profile
                user.save()
            else:
                frappe.msgprint("Role profile not set in Designation, please set default.")

    def on_update(self):
        super(EmployeeOverride, self).on_update()
        set_mandatory_feilds_in_employee_for_Kuwaiti(self, method=None)
        try:
            current_doc = frappe.get_doc("Employee", self.name)
            if (self.shift != current_doc.shift) and (self.shift_working != current_doc.shift_working):
                frappe.db.sql(f"""
                    DELETE FROM `tabEmployee Schedule` WHERE employee='{self.employee}'
                    AND date>'{getdate()}'
                """)
        except:
            pass

        # clear future employee schedules
        self.clear_schedules()

    def clear_schedules(doc):
        # clear future employee schedules
        if doc.status == 'Left':
            frappe.db.sql(f"""
                DELETE FROM `tabEmployee Schedule` WHERE employee='{doc.name}'
                AND date>'{doc.relieving_date}'
            """)
            frappe.msgprint(f"""
                Employee Schedule cleared for {doc.employee_name} starting from {add_days(doc.relieving_date, 1)} 
            """)

def validate_leaves(self):
    if self.status=='Vacation':
        if not frappe.db.sql(f"""
                SELECT name FROM `tabLeave Application` WHERE employee="{self.name}" AND docstatus IN (0,1)
                AND
                '{getdate()}' BETWEEN from_date AND to_date
            """, as_dict=1):
            frappe.throw(f"Status cannot be 'Vacation' when no Leave Application exists for {self.employee_name} today {getdate()}.")

@frappe.whitelist()
def get_new_employee_id(employee_id):
    length = len(employee_id)
    num = employee_id[length-3] #get the third-last character.
    if num == '0':
        new_emp_id = employee_id[:length-3] + '1' + employee_id[length-2:]
        return new_emp_id
