from itertools import chain
from json import loads
import requests

import frappe
from frappe.utils import getdate, add_days, get_url_to_form, get_url, today
from frappe.utils.user import get_users_with_role
from frappe.permissions import remove_user_permission
from one_fm.api.api import  push_notification_rest_api_for_checkin
from one_fm.api.tasks import send_notification
from one_fm.api.v1.utils import response
from hrms.overrides.employee_master import *
from one_fm.hiring.utils import (
    employee_after_insert, employee_before_insert, set_employee_name,
    employee_validate_attendance_by_timesheet, set_mandatory_feilds_in_employee_for_Kuwaiti,
    is_subcontract_employee
)
from one_fm.processor import sendemail,send_whatsapp
from one_fm.utils import call_to_get_assurance_level, get_domain, get_standard_notification_template, get_approver_user, update_active_employees_assurance_level, send_push_notification
from six import string_types
from frappe import _
from one_fm.operations.doctype.operations_shift.operations_shift import get_supervisor_operations_shifts
from one_fm.one_fm.doctype.demand_letter.demand_letter import get_demand_letter, get_demand_letter_quota

class EmployeeOverride(EmployeeMaster):
    def validate(self):
        from erpnext.controllers.status_updater import validate_status
        validate_status(self.status, ["Active", "Court Case", "Absconding", "Left", "Vacation", "Not Returned from Leave"])

        if self.pam_type == "Kuwaiti":
            self.residency_expiry_date = None

        self.employee = self.name
        self.set_employee_name()
        set_employee_name(self, method=None)
        self.set_employee_id_based_on_residency()
        self.validate_reliever()
        self.validate_date()
        self.validate_email()
        self.validate_status()
        self.validate_reports_to()
        self.validate_preferred_email()
        self.validate_face_recognition_enrollment()
        self.toggle_auto_attendance()
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
        self.validate_relieving_date()
        self.validate_subcontractor_name()

    def toggle_auto_attendance(self):
        try:
            if not self.is_new():
                doc_before_update = self.get_doc_before_save()
                if doc_before_update.auto_attendance != self.auto_attendance:
                    if not any((frappe.db.exists("Has Role", {"role": ["IN", ["HR Manager", "HR Supervisor", "Attendance Manager"]], "parent": frappe.session.user}), frappe.session.user == "Administrator")):
                        frappe.throw("You Are Not Permitted To Toggle Auto-Attendance")
        except Exception as e:
            frappe.log_error(message=f"{str(e)}", title="Employee Auto Attendance Toggle")

    def set_employee_id_based_on_residency(self):
        if self.employee_id:
            residency_employee_id = get_employee_id_based_on_residency(self.employee_id, self.under_company_residency, self.name, self.employment_type)
            if self.employee_id != residency_employee_id:
                self.employee_id = residency_employee_id

    def validate_face_recognition_enrollment(self):
        # Skip the validation while creating new employee
        if self.is_new():
            return

        prev_enrollment = self.get_doc_before_save().get('enrolled')

        # Allow update if the context flag is set
        if not frappe.flags.allow_enrollment_update:
            if prev_enrollment != self.enrolled:
                frappe.throw(f"Enrollment field is read-only and cannot be modified.")

    def validate_relieving_date(self):
        if "one_fm_password_management" not in frappe.get_installed_apps():
            return
        if self.relieving_date and self.user_id:
            owner_credentials = frappe.get_all(
                "Password Management",
                {
                    "credentials_owner": self.user_id,
                    "docstatus": ("!=", 2) # Not cancelled
                },
                as_list=1
            )
            if owner_credentials:
                links = [
                    f"<a href='{get_url_to_form('Password Management', cred[0])}' target='_blank'>[{cred[0]}]</a>"
                    for cred in owner_credentials
                ]
                message = (
                    "Employee is still listed as Credentials Owner in the following Password Management Records:<br/>"
                    + ", ".join(links) +
                    "<br/><br/>Please reassign ownership before setting Relieving Date."
                )
                frappe.throw(message)

    def validate_subcontractor_name(self):
        """
        Validates that the Subcontractor Name on Employee matches
        the linked Onboard Subcontract Employee record, if one exists.
        Blocks save with a strict error if there is a mismatch.
        """
        if not self.custom_subcontractor_name:
            return

        onboard_record = frappe.db.get_value(
            "Onboard Subcontract Employee",
            {"employee": self.name},
            ["name", "subcontractor_name"],
            as_dict=True
        )

        if not onboard_record:
            return

        if self.custom_subcontractor_name != onboard_record.subcontractor_name:
            frappe.throw(
                _("The Subcontractor Name does not match the linked Onboard Subcontract Employee record. "
                  "Please verify and select the correct Subcontractor.")
            )

    def before_save(self):
        self.assign_role_profile_based_on_designation()
        update_employee_phone_number(self)
        # get_assurance_level_of_employee(self)

    def after_insert(self):
        employee_after_insert(self, method=None)
        self.assign_role_profile_based_on_designation()
        self.update_agency_employee_count()

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

    def update_agency_employee_count(self):
        if not self.job_applicant:
            return
        agency = frappe.db.get_value("Job Applicant", self.job_applicant, "one_fm_agency")
        if not agency:
            return

        if not get_demand_letter(agency, self.designation, self.gender):
            return
        demand_letter = get_demand_letter_quota(agency, self.designation, self.gender)
        available_quota = 0
        if demand_letter:
            available_quota = demand_letter.quantity - demand_letter.used_quantity
        if available_quota <= 0:
            inform_demand_letter_quota_completion = frappe.db.get_single_value("Hiring Settings", "inform_demand_letter_quota_completion")
            if not inform_demand_letter_quota_completion:
                return

            if inform_demand_letter_quota_completion:
                frappe.msgprint(f"Demand letter quota for agency {agency} has been exhausted.")
                completion_notification_email = frappe.db.get_single_value("Hiring Settings", "demand_letter_quota_completion_notification_email")

                if not completion_notification_email:
                    return

                sendemail(
                    recipients=[completion_notification_email],
                    subject="Demand Letter Quota Exhausted",
                    message=f"The demand letter quota for agency {agency} has been exhausted."
                )
        elif demand_letter:
            # Update used quantity
            new_used_quantity = demand_letter.used_quantity + 1
            frappe.db.set_value("Demand Letter Demand", demand_letter.name, "used_quantity", new_used_quantity)

    def on_update(self):
        super(EmployeeOverride, self).on_update()
        self.validate_status_change()
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
        self.inform_employee_id_update()
        self.notify_employee_id_update()
        self.remove_user_on_employee_left()
        self.notify_supervisor_of_status_change()
        if self.has_value_changed("status") and self.status == "Not Returned from Leave":
            self.inform_employee_status_update()
            frappe.enqueue(delete_employee_schedules_for_next_7_days, queue='default', timeout=300, employee_id=self.name)

        self.setup_wiki_introduction_for_new_employee()


    def inform_employee_id_update(self):
        """
        Notifies the employee's manager and HR generalists when an employee ID is updated.
        
        This method sends administrative notifications to relevant personnel about the employee ID change.
        It ensures that management is aware of the change and can assist the employee if needed.
        
        Notifications sent:
        - Email to employee's direct manager (reports_to)
        - Email to HR Generalists
        - Push notification to manager's mobile app
        
        Triggers when:
        - Employee ID field has changed (detected via has_value_changed)
        
        Returns:
            None
            
        Raises:
            Logs error to frappe error log if notification fails
        """
        try:
            if self.has_value_changed('employee_id'):
                old_value = self.get_doc_before_save().employee_id
                reports_to = self.get_reports_to_user()
                subject = f"Employee {self.name} employee id changed"
                description = '''
                    The Employee ID for {{employee_name}} has been updated from {{old_value}} to {{employee_id}}.
                    Kindly ensure that the Employee is aware of this change so that they can continue to log in
                '''
                doc_link = "<p><a href='{0}'>Link to Employee Record</a></p>".format(get_url(self.get_url()))
                context = self.as_dict()
                context['old_value'] = old_value
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
        """
        Notifies the employee directly when their employee ID is updated.
        
        This method sends personal notifications to the employee about their own employee ID change.
        It ensures the employee is aware of the change and can continue to access the system.
        
        Notifications sent:
        - Email (if employee prefers company email)
        - Push notification to employee's mobile app
        - WhatsApp message with template
        
        Triggers when:
        - Employee ID field has changed (detected via has_value_changed)
        
        Message content:
        - Informs about residency registration completion
        - Shows old and new employee ID
        - Provides link to employee record
        
        Returns:
            None
            
        Raises:
            Logs error to frappe error log if notification fails
        """
        try:
            if self.has_value_changed('employee_id'):
                context = self.as_dict()
                subject = f"Your  Employee ID changed"
                if self.prefered_contact_email == "Company Email":

                    description = f'''
                        Dear {self.employee_name},
                        Your residency registration process has been completed and your employee id has been updated from {self.get_doc_before_save().employee_id} to {self.employee_id}
                    '''
                    doc_link = "<p><a href='{0}'>Link to Employee Record</a></p>".format(get_url(self.get_url()))
                    context['message_heading'] = ''
                    msg = frappe.render_template(get_standard_notification_template(description, doc_link), context)
                    # sendemail(recipients=[self.user_id], subject=subject, content=msg)
                    send_notification(title=subject,subject=subject,message=msg,category="Alert",recipients=[self.user_id])

                push_message = f"Dear {context.first_name}, Your residency registration process has been completed and your employee ID has been updated to {self.employee_id}."
                push_notification_rest_api_for_checkin(employee_id=self.name,title=subject,body=push_message,checkin=False,arriveLate=False,checkout=False)
                if self.cell_number:
                    if '(' in self.cell_number or ')' in self.cell_number or '+' in self.cell_number:
                        cell_number = "".join(i for i in self.cell_number if i.isdigit())
                    else:
                        cell_number = self.cell_number
                content_variables= {
	                    	'1':context.first_name,
                            '2':self.get_doc_before_save().employee_id or '',
                            '3':self.employee_id or '',
                    	}
                send_whatsapp(sender_id=cell_number,template_name='employee_id_change', content_variables=content_variables)
        except:
            frappe.log_error(title = "Error Notifying Employee",message = frappe.get_traceback())
            frappe.msgprint("Error Notifying Employee, Please check Error Log for Details")

    def get_reports_to_user(self):
        return get_approver_user(self.name)

    def update_subcontract_onboard(self):
        subcontract_onboard = frappe.db.exists("Onboard Subcontract Employee", {"employee": self.name, "enrolled": ['!=', '1']})
        if subcontract_onboard and self.enrolled:
            frappe.db.set_value("Onboard Subcontract Employee", subcontract_onboard, "enrolled", self.enrolled)

    def remove_user_on_employee_left(self):
        if self.status != "Left":
            return
        if "one_fm_password_management" not in frappe.get_installed_apps():
            return
        # Check if status has been changed to 'Left'
        if self.status == "Left" and self.get_doc_before_save().status != "Left":
            if self.user_id:
                try:
                    frappe.db.sql("""
                        DELETE
                        FROM
                            `tabPassword Management User`
                        WHERE
                            user = %s
                    """, (self.user_id))
                    frappe.msgprint(f"User {self.user_id} removed from all Password Management records.")
                except Exception as e:
                    message = f"Failed to remove user {self.user_id} from Password Management {user_access.parent}"
                    frappe.log_error(message=message+f": {e}", title=message)

    def notify_attendance_manager_on_status_change(self):
        last_doc = self.get_doc_before_save()
        if last_doc and last_doc.get('status') == "Active":
            if self.status != "Active":
                NotifyAttendanceManagerOnStatusChange(employee_object=self).notify_authorities()

    def validate_reliever(self):
        reliever_flags = [
            self.custom_is_reliever,
            self.custom_is_weekend_reliever,
            self.custom_is_rambo_reliever,
        ]
        if sum(1 for flag in reliever_flags if flag) > 1:
            frappe.throw(_("Employee can only be marked as one reliever type at a time: Day Off, Weekend, or Rambo."))

    def validate_status_change(self):
        last_doc = self.get_doc_before_save()
        if last_doc and last_doc.get('status') == "Active":
            if self.status != "Active":
                status_validate = StatusChangeVaccumValidate(employee_object=self)
                message = status_validate.message()
                if message:
                    frappe.throw(message)

    def inform_employee_status_update(self):
        try:
            subject = f"Your Employee Status changed to {self.status}"
            message = f"Dear {self.employee_name}, your status has been changed to {self.status}, please contact your supervisor"
            send_push_notification(
                employee_id=self.employee_id,
                title=subject,
                body=message
            )
        except Exception as e:
            frappe.log_error(message=f"Failed to send status update notification: {str(e)}", title="Employee Status Update Notification")

    def clear_schedules(self):
        # clear future employee schedules
        if(self.has_value_changed('relieving_date') or self.has_value_changed('status')):
            if self.status == 'Left' or self.relieving_date:
                frappe.db.sql(f"""
                    DELETE FROM `tabEmployee Schedule` WHERE employee = '{self.name}'
                    AND date > '{self.relieving_date}'
                """)
                frappe.msgprint(f"""
                    Employee Schedule cleared for {self.employee_name} starting from {add_days(self.relieving_date, 1)}
                """)

    def notify_supervisor_of_status_change(self):
        """
        Notify the operations site supervisor when an employee's status changes to Active.

        This method is intended to be called during the employee document lifecycle
        (e.g. on validate/before save). It compares the previous stored version of
        the document with the current one, and proceeds only when:

        - A previous document exists (`get_doc_before_save` returns a value).
        - The employee's status has changed from any non-"Active" value to "Active".
        - The employee is marked as shift working (`self.shift_working` is truthy).
        - The employee has an associated Operations Site with a valid site supervisor
          and that supervisor has a linked user account.

        When these conditions are met, the method sends both a push notification
        (via `send_push_notification`) and an email (via `sendemail`) to the site
        supervisor, informing them that the employee is now Active and should be
        rostered appropriately. Failures to send notifications are logged using
        Frappe's error log.
        """
        last_doc = self.get_doc_before_save()
        
        if not last_doc:
            return
        
        status_changed_to_active = last_doc.get("status") != "Active" and self.status == "Active"
        if not (status_changed_to_active and self.shift_working):
            return
        
        site_supervisor = frappe.db.get_value("Operations Site", self.site, "site_supervisor")
        if not site_supervisor:
            frappe.log_error(f"No site supervisor found for site {self.site}", "Employee Status Change Notification")
            return
        
        supervisor_details = frappe.db.get_value(
            "Employee",
            site_supervisor,
            ["user_id", "employee_id", "employee_name"],
            as_dict=1
        )
        
        if not supervisor_details or not supervisor_details.user_id:
            frappe.log_error(f"Invalid supervisor details for {site_supervisor}", "Employee Status Change Notification")
            return
        
        subject = f"{self.employee_name} (ID: {self.name}) Status Changed to Active"
        message = (
            f"Dear {supervisor_details.employee_name},\n\n"
            f"{self.employee_name} with Employee ID {self.name} has been changed to 'Active'.\n"
            f"Please ensure that they are adequately rostered.\n\n"
            f"Site: {self.site}"
        )
        
        try:
            send_push_notification(
                employee_id=supervisor_details.employee_id,
                title=subject,
                body=message
            )
            sendemail(
                recipients=[supervisor_details.user_id],
                subject=subject,
                message=message
            )
        except Exception as e:
            frappe.log_error(f"Failed to send notification: {str(e)}", "Employee Status Change Notification")

    def setup_wiki_introduction_for_new_employee(self):
        if self.status == 'Active':
            return
        if self.shift_working == 1:
            return
        if self.attendance_by_timesheet == 1:
            return
        if self.auto_attendance == 1:
            return
        if not self.user_id:
            return
        if not self.has_value_changed('user_id'):
            return

        self.set_default_workspace_for_new_user()
        self.create_wiki_introduction_todo()

    def set_default_workspace_for_new_user(self):
        default_workspace = frappe.db.get_value("User", self.user_id, "default_workspace")
        if not default_workspace:
            onboarding_workspace = frappe.db.get_single_value("HR Settings", "onboarding_workspace") or "Wiki"
            frappe.db.set_value("User", self.user_id, "default_workspace", onboarding_workspace, update_modified=False)

    def create_wiki_introduction_todo(self):
        wiki_introduction_doc_link = frappe.db.get_single_value("HR Settings", "wiki_introduction_doc_link")
        if not wiki_introduction_doc_link:
            return
        description = 'Review the "Wiki Introduction" document. Then, review the 14 linked wikis and complete all associated quizzes and feedback forms within one day.'
        # Check if a "Todo" with the same description and for the same user already exists
        if not frappe.db.exists("ToDo", {"allocated_to": self.user_id, "description": ["like", f"%{description}%"]}):
            frappe.get_doc({
                "doctype": "ToDo",
                "allocated_to": self.user_id,
                "description": f'{description} <br> Please review the following document: <a href="{wiki_introduction_doc_link}">Wiki Introduction</a>',
                "date": getdate(),
                "due_date": add_days(getdate(), 30)
            }).insert(ignore_permissions=True)

def create_wiki_assessment_todo_for_employees():
    wiki_assessment_form_link = frappe.db.get_single_value("HR Settings", "wiki_assessment_form_link")
    if not wiki_assessment_form_link:
        return
    description = f'Complete the wiki assessments:'
    employees = frappe.get_all("Employee", filters={
        "status": "Active",
        "shift_working": 0,
        "attendance_by_timesheet": 0,
        "auto_attendance": 0,
        "user_id": ["is", "set"],
        "creation": ["<=", add_days(getdate(), -30)]
    }, fields=["name", "employee_name", "user_id"])
    for employee in employees:
        if not frappe.db.exists("ToDo", {"allocated_to": employee.user_id, "description": ["like", f"%{description}%"]}):
            frappe.get_doc({
                "doctype": "ToDo",
                "allocated_to": employee.user_id,
                "description": f'{description} <a href="{wiki_assessment_form_link}">Wiki Assessments</a>',
                "date": getdate(),
                "due_date": getdate()
            }).insert(ignore_permissions=True)

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
        if doc.status in ['Left','Absconding','Court Case', 'Not Returned from Leave'] and doc.status not in [old_self] and doc.user_id:
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


def update_employee_phone_number(doc):
    if not doc.is_new():
        old_cell_number = doc.get_doc_before_save().cell_number
        if doc.cell_number and doc.cell_number != old_cell_number and doc.user_id:
            user_doc = frappe.get_doc('User', doc.user_id)
            user_doc.phone = doc.cell_number
            user_doc.mobile_no = doc.cell_number
            user_doc.save(ignore_permissions=True)
            frappe.msgprint(f"User {doc.user_id} phone number updated to {doc.cell_number}", alert=True)
            frappe.db.commit()


class NotifyAttendanceManagerOnStatusChange:

    def __init__(self, employee_object: EmployeeOverride) -> None:
        self.employee_object = employee_object

    @property
    def _operations_shift_supervisor(self) -> list:
        return get_supervisor_operations_shifts(self.employee_object.name)

    @property
    def _operations_site_supervisor(self) -> list:
        operation_sites = frappe.db.sql(""" SELECT name from `tabOperations Site` WHERE site_supervisor = %s AND status = 'Active' """, (self.employee_object.name), as_list=1)
        return list(chain.from_iterable(operation_sites)) if operation_sites else list()

    @property
    def _projects_manager(self) -> list:
        projects = frappe.db.sql(""" SELECT name from `tabProject` WHERE project_manager = %s AND is_active = 'Yes' """, (self.employee_object.name), as_list=1)
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
            frappe.log_error(message=frappe.get_traceback(), title="Employee Status Change Notification")
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


class StatusChangeVaccumValidate(NotifyAttendanceManagerOnStatusChange):


    def __init__(self, employee_object: EmployeeOverride):
        super().__init__(employee_object=employee_object)
        self._message = ""

    @property
    def message_header(self):
        return f"""
                <div>
                    <h3>This employee has responsibilities in the following document</h3> """



    def construct_operations_shift_supervisor_message(self):
        shifts = self._operations_shift_supervisor
        if shifts:
            self._message += "<h5>Operations Shift</h5> <ul>"
            for obj in shifts:
                self._message += f""" <li>{obj}</li>"""

            self._message += f""" </ul><br><br>"""

    def construct_operations_site_supervisor_message(self):
        sites = self._operations_site_supervisor
        if sites:
            self._message += "<h5>Operations Site</h5> <ul>"
            for obj in sites:
                self._message += f""" <li>{obj}</li>"""

            self._message += f""" </ul><br><br>"""


    def construct_projects_manager_message(self):
        projects = self._projects_manager
        if projects:
            self._message += "<h5>Project</h5> <ul>"
            for obj in projects:
                self._message += f""" <li>{obj}</li>"""

            self._message += f""" </ul><br><br>"""


    def construct_reports_to_message(self):
        reports_to = self._employee_reports_to
        if reports_to:
            self._message += "<h5>Employee Reports To</h5> <ul>"
            for obj in reports_to:
                self._message += f""" <li>{obj.name} -- {obj.employee_name}</li>"""

            self._message += f""" </ul><br><br>"""



    def construct_attendance_manager_message(self):
        if self._attendance_manager:
            self._message += "<h5>This employee is the attendance manager.</h5> <br><br>"


    def construct_operations_manager_message(self):
        if self._operation_manager:
            self._message += "<h5>This employee is the Operations manager.</h5> <br><br>"



    def message(self):
        if any((self._operations_shift_supervisor, self._operations_site_supervisor, self._projects_manager,
               self._employee_reports_to, self._attendance_manager, self._operation_manager)):
            self._message = self.message_header

            self.construct_operations_shift_supervisor_message()

            self.construct_operations_site_supervisor_message()

            self.construct_projects_manager_message()

            self.construct_reports_to_message()

            self.construct_attendance_manager_message()

            self.construct_operations_manager_message()

            self._message += "<div>"

            return self._message

def has_day_off(employee, date):
    """
        Checks if an employee has a scheduled day off on a specific date.
        Args:
            employee (str): The name of the employee to check for a day off.
            date (str): The date for which to check if the employee has a scheduled day off.
                        Format: "YYYY-MM-DD"
        Returns:
            bool: True if the employee has a scheduled day off on the given date, False otherwise.
    """
    if frappe.db.exists(
        "Employee Schedule",
        {
            "employee":employee,
            "date":date,
            "employee_availability":"Day Off"
        }
    ):
        return True
    return False

def is_employee_on_leave(employee, date):
    """
        Checks if an employee is on leave on a specific date.
        Args:
            employee (str): The name of the employee to check for leave.
            date (str): The date for which to check if the employee is on leave.
                        Format: "YYYY-MM-DD"
        Returns:
            bool: True if the employee is on leave on the given date, False otherwise.
    """
    if frappe.db.exists(
        "Attendance",
        {
            "status": "On Leave",
            "docstatus": 1,
            "employee": employee,
            "attendance_date": date
        }
    ):
        return True
    return False



@frappe.whitelist(methods=["POST"])
def toggle_auto_attendance(employee_names: list | str, status: bool):
    try:
        employee_names = loads(employee_names)
        if any((frappe.db.exists("Has Role", {"role": ["IN", ["HR Manager", "HR Supervisor", "Attendance Manager"]], "parent": frappe.session.user}), frappe.session.user == "Administrator")):
            frappe.db.sql(f"""
                            UPDATE `tabEmployee`
                            SET auto_attendance = {status}
                            WHERE name in {tuple(employee_names)}
                        """)
            return response(message=f"Updated {len(employee_names)} Successfully", status_code=201)
        return response(message="You are not permitted to carry out this action", status_code=400)
    except Exception as e:
        frappe.log_error(title="Error while toggling auto attendance", message=frappe.get_traceback())
        return response(message=str(e), status_code=400)



@frappe.whitelist()
def fetch_accomodation_name(name: str):
    try:
        accomodation = frappe.db.sql("""
            SELECT a.accommodation
            FROM `tabAccommodation Checkin Checkout` acc
            JOIN `tabAccommodation` a ON a.name = acc.accommodation
            WHERE acc.employee = %s
            AND acc.type = 'IN'
            ORDER BY acc.creation DESC
            LIMIT 1
        """, (name,), as_dict=True)
        return response(message="Success", status_code=200, data=dict(accomodation=accomodation[0].get("accommodation", "") if accomodation else ""))
    except Exception as e:
        frappe.log_error(title=f"Error while fetching accommodation name", message=frappe.get_traceback())
        return response(message=str(e), status_code=400)


@frappe.whitelist()
def get_assurance_level_of_employee(doc, method):
    try:
        if doc.one_fm_civil_id:
            verification_level = call_to_get_assurance_level(doc.one_fm_civil_id)
            if verification_level:
                verification_level = verification_level.get("verificationLevel")
                doc.custom_civil_id_assurance_level = verification_level
            return True
    except Exception as e:
            frappe.log_error(message=frappe.get_traceback(), title=f"DSS returned NONE values,No API key")


def delete_employee_schedules_for_next_7_days(employee_id):
        start_date = today()
        end_date = add_days(start_date, 6)

        try:
            frappe.db.sql("""
                DELETE FROM `tabEmployee Schedule`
                WHERE employee = %(employee)s
                AND date BETWEEN %(start_date)s AND %(end_date)s
            """, {
                'employee': employee_id,
                'start_date': start_date,
                'end_date': end_date
            })
            
            frappe.db.commit()

        except Exception as e:
            frappe.log_error(
                message=f"Error deleting schedules: {str(e)}",
                title=f"Employee Schedule Deletion Error - {employee_id}"
            )
            raise