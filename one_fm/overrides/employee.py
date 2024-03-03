from itertools import chain

import frappe
from frappe.utils import getdate, add_days, get_url_to_form, get_url
from frappe.utils.user import get_users_with_role
from frappe.permissions import remove_user_permission
from one_fm.api.api import  push_notification_rest_api_for_checkin
from one_fm.api.tasks import send_notification
from hrms.overrides.employee_master import *
from one_fm.hiring.utils import (
    employee_after_insert, employee_before_insert, set_employee_name,
    employee_validate_attendance_by_timesheet, set_mandatory_feilds_in_employee_for_Kuwaiti,
    is_subcontract_employee
)
from one_fm.processor import sendemail,send_whatsapp
from one_fm.utils import get_domain, get_standard_notification_template, get_approver
from six import string_types
from frappe import _

class EmployeeOverride(EmployeeMaster):
    def validate(self):
        from erpnext.controllers.status_updater import validate_status
        validate_status(self.status, ["Active", "Court Case", "Absconding", "Left","Vacation"])

        self.employee = self.name
        self.set_employee_name()
        set_employee_name(self, method=None)
        self.set_employee_id_based_on_residency()
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

    def set_employee_id_based_on_residency(self):
        if self.employee_id:
            residency_employee_id = get_employee_id_based_on_residency(self.employee_id, self.under_company_residency, self.name, self.employment_type)
            if self.employee_id != residency_employee_id:
                self.employee_id = residency_employee_id

    def before_save(self):
        self.assign_role_profile_based_on_designation()

    def after_insert(self):
        employee_after_insert(self, method=None)
        self.assign_role_profile_based_on_designation()

    @frappe.whitelist()
    def run_employee_id_generation(self):
        employee_after_insert(self, method=None)

    def before_insert(self):
        employee_before_insert(self, method=None)

    def validate_onboarding_process(self):
        validate_onboarding_process(self)

    def assign_role_profile_based_on_designation(self):
        previous_designation = frappe.db.get_value("Employee", self.name, "designation")
        if self.designation and self.user_id and self.designation != previous_designation:
            role_profile = frappe.db.get_value("Designation", self.designation, "role_profile")
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
        self.update_subcontract_onboard()
        self.notify_attendance_manager_on_status_change()
        self.inform_employee_id_update()
        self.notify_employee_id_update()


    def inform_employee_id_update(self):
        try:
            if self.has_value_changed('employee_id'):
                reports_to = self.get_reports_to_user()
                subject = f"Employee {self.name} employee id changed"
                description = '''
                    The Employee ID for {{employee_name}} has been updated to {{employee_id}}.
                    Kindly ensure that the Employee is aware of this change so that they can continue to log in
                '''
                doc_link = "<p><a href='{0}'>Link to Employee Record</a></p>".format(get_url(self.get_url()))
                context = self.as_dict()
                recipients = get_hr_generalists()
                recipients.append(reports_to)
                context['message_heading'] = ''
                msg = frappe.render_template(get_standard_notification_template(description, doc_link), context)
                # sendemail(recipients=[reports_to], subject=subject, content=msg)
                send_notification(title=subject,subject=subject,message=msg,category="Alert",recipients=recipients)
                emp_id = frappe.get_value("Employee",{'user_id':reports_to})
                if emp_id:
                    msg = f"Employee ID for {context.employee_name} has been updated to {context.employee_id}."
                    push_notification_rest_api_for_checkin(employee_id=emp_id,title=subject,body=msg,checkin=False,arriveLate=False,checkout=False)
        except:
            frappe.log_error(title = "Error Notifying Manager",message = frappe.get_traceback())
            frappe.msgprint("Error Notifying Manager, Please check Error Log for Details")
        
    def notify_employee_id_update(self):
        try:
            if self.has_value_changed('employee_id'):
                context = self.as_dict()
                subject = f"Your  Employee ID changed"
                if self.prefered_contact_email == "Company Email":
                    
                    description = f'''
                        Dear {self.employee_name},
                        Your residency registration process has been completed and your employee id has been update from {self.get_doc_before_save().employee_id} to {self.employee_id}
                    '''
                    doc_link = "<p><a href='{0}'>Link to Employee Record</a></p>".format(get_url(self.get_url()))
                    context['message_heading'] = ''
                    msg = frappe.render_template(get_standard_notification_template(description, doc_link), context)
                    # sendemail(recipients=[self.user_id], subject=subject, content=msg)
                    send_notification(title=subject,subject=subject,message=msg,category="Alert",recipients=[self.user_id])
                
                push_message = f"Dear {context.first_name}, Your residency registration process has been completed and your employee ID has been updated  to {self.employee_id}."
                push_notification_rest_api_for_checkin(employee_id=self.name,title=subject,body=push_message,checkin=False,arriveLate=False,checkout=False)
                if self.cell_number:
                    if '(' in self.cell_number or ')' in self.cell_number or '+' in self.cell_number:
                        cell_number = "".join(i for i in self.cell_number if i.isdigit())
                    else:
                        cell_number = self.cell_number
                whatsapp_message = f"Dear {context.first_name}, Your residency registration process has been completed and your employee ID has been updated from {self.get_doc_before_save().employee_id} to {self.employee_id}.",
                send_whatsapp(sender_id=cell_number,body = whatsapp_message)
        except:
            frappe.log_error(title = "Error Notifying Employee",message = frappe.get_traceback())
            frappe.msgprint("Error Notifying Employee, Please check Error Log for Details")

    def get_reports_to_user(self):
        approver = get_approver(self.name)
        if approver:
            return frappe.db.get_value('Employee', approver, 'user_id')

    def update_subcontract_onboard(self):
        subcontract_onboard = frappe.db.exists("Onboard Subcontract Employee", {"employee": self.name, "enrolled": ['!=', '1']})
        if subcontract_onboard and self.enrolled:
            frappe.db.set_value("Onboard Subcontract Employee", subcontract_onboard, "enrolled", self.enrolled)

    def notify_attendance_manager_on_status_change(self):
        last_doc = self.get_doc_before_save()
        if last_doc and last_doc.get('status') == "Active":
            if self.status != "Active":
                NotifyAttendanceManagerOnStatusChange(employee_object=self).notify_authorities()

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
def is_employee_master(user:str) -> int:
    #Return 1 if the employee has the required roles to modify the employee form.
    can_edit = 0
    employee_master_role = frappe.get_all("ONEFM Document Access Roles Detail",{'parent':"ONEFM General Setting",'parentfield':"employee_master_role"},['role'])
    if employee_master_role:
        master_roles = [i.role for i in employee_master_role]
        user_roles = frappe.get_roles(user)
        role_intersect = [i for i in master_roles if i in user_roles]
        if role_intersect:
            return 1
    return can_edit


def get_hr_generalists():
    users = frappe.get_all("User",{'role_profile_name':"HR Generalist"})
    if users:
        return [i.name for i in users]
    return []

@frappe.whitelist()
def get_employee_id_based_on_residency(employee_id, residency, employee=False, employment_type=False):
    length = len(employee_id)
    if isinstance(residency, string_types):
        residency = int(residency)
    employee_id_residency_digit = '1' if residency==1 else '0'
    if is_subcontract_employee(employee, employment_type):
        employee_id_residency_digit = 'S'
    # Change third last character in employee id
    return employee_id[:length-3] + employee_id_residency_digit + employee_id[length-2:]

def update_user_doc(doc):
    if not doc.is_new():
        old_self = doc.get_doc_before_save().status
        if doc.status in ['Left','Absconding','Court Case'] and doc.status not in [old_self] and doc.user_id:
            user_doc = frappe.get_doc('User',doc.user_id)
            if user_doc.enabled == 1:
                user_doc.enabled = 0
                user_doc.flags.ignore_validate = 1
                user_doc.flags.ignore_permissions = 1
                user_doc.save()
                frappe.msgprint(f"User {doc.user_id} disabled",alert=1)
                frappe.db.commit()
        elif doc.status == "Active" and doc.status not in [old_self] and doc.user_id:
            user_doc = frappe.get_doc('User',doc.user_id)
            if user_doc.enabled == 0:
                user_doc.enabled = 1
                user_doc.save(ignore_permissions=1)
                frappe.msgprint(f"User {doc.user_id} enabled",alert=1)
                frappe.db.commit()



class NotifyAttendanceManagerOnStatusChange:

    def __init__(self, employee_object: EmployeeOverride) -> None:
        self.employee_object = employee_object

    @property
    def _operations_shift_supervisor(self) -> list:
        operation_shifts = frappe.db.sql(""" SELECT name from `tabOperations Shift` WHERE supervisor = %s AND status = 'Active' """, (self.employee_object.name), as_list=1)
        return list(chain.from_iterable(operation_shifts)) if operation_shifts else list()

    @property
    def _operations_site_supervisor(self) -> list:
        operation_sites = frappe.db.sql(""" SELECT name from `tabOperations Site` WHERE account_supervisor = %s AND status = 'Active' """, (self.employee_object.name), as_list=1)
        return list(chain.from_iterable(operation_sites)) if operation_sites else list()

    @property
    def _projects_manager(self) -> list:
        projects = frappe.db.sql(""" SELECT name from `tabProject` WHERE account_manager = %s AND is_active = 'Yes' """, (self.employee_object.name), as_list=1)
        return list(chain.from_iterable(projects)) if projects else list()

    @property
    def _employee_reports_to(self) -> list:
        reports_to = frappe.db.sql(""" SELECT name, employee_name from `tabEmployee` where reports_to = %s AND status= 'Active' """, (self.employee_object.name), as_dict=1)
        return reports_to

    @property
    def _to_do(self) -> str:
        try:
            result = frappe.db.sql("""
                                    SELECT EXISTS (
                                        SELECT 1
                                        FROM `tabToDo`
                                        WHERE allocated_to = %s AND status = 'Open'
                                    ) AS record_exists
                                    """, (self.employee_object.user_id,))
            is_to_do = result[0][0]
            return f"{get_domain()}/app/todo?status=Open&allocated_to={self.employee_object.user_id}" if is_to_do else ""
        except Exception as e:
            return ""

    @property
    def _operation_manager(self) -> str | None:
        return frappe.db.get_single_value("Operation Settings", "default_operation_manager") == self.employee_object.user_id

    @property
    def _attendance_manager(self) -> str:
        return frappe.db.get_single_value('ONEFM General Setting', 'attendance_manager') ==  self.employee_object.name

    @property
    def _directors(self) -> list:
        return frappe.db.get_list("User", filters={"role_profile_name": "Director"}, pluck="name")


    def generate_data(self) -> dict:
        try:
            data_dict = dict()
            operations_shift = self._operations_shift_supervisor
            if operations_shift:
                data_dict.update({"operations_shift": dict()})
                for obj in operations_shift:
                    data_dict.get("operations_shift").update({obj: get_url_to_form("Operations Shift", obj)})


            operations_site = self._operations_site_supervisor
            if operations_site:
                data_dict.update({"operations_site": dict()})
                for obj in operations_site:
                    data_dict.get("operations_site").update({obj: get_url_to_form("Operations Site", obj)})


            projects = self._projects_manager
            if projects:
                data_dict.update({"projects": dict()})
                for obj in projects:
                    data_dict.get("projects").update({obj: get_url_to_form("Projects", obj)})

            reports_to = self._employee_reports_to
            if reports_to:
                data_dict.update({"reports_to": list()})
                for obj in reports_to:
                    data_dict.get("reports_to").append(dict(name=obj.get("name"), employee_name=obj.get("employee_name"), url=get_url_to_form("Employee", obj.get("name"))))

            if self._operation_manager:
                data_dict.update({"operations_manager": f"{get_domain()}/app/operation-settings"})

            if self._attendance_manager:
                data_dict.update({"attendance_manager": f"{get_domain()}/app/onefm-general-setting"})

            if self._to_do:
                data_dict.update({"to_do": self._to_do})

            return data_dict
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Employee Status Change Notification")
            return dict()


    def notify_authorities(self):
        pass
        # try:
        #     data = self.generate_data()
        #     if data:
        #         the_recipient = get_users_with_role("HR Manager")
        #         data_update = dict(
        #             employee_name=self.employee_object.employee_name,
        #             employee_id=self.employee_object.employee_id,
        #             status=self.employee_object.status
        #         )
        #         data.update(data_update)
        #         title = f"Immediate Attention Required: Employee {self.employee_object.name} Status Change and Reassignment is required"
        #         msg = frappe.render_template('one_fm/templates/emails/notify_authorities_employee_status_change.html', context=data)
        #         sendemail(recipients=the_recipient, subject=title, content=msg)
        # except Exception as e:
        #     frappe.log_error(frappe.get_traceback(), "Error while sending mail on status change(Employee)")
