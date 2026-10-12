# -*- coding: utf-8 -*-
# Copyright (c) 2021, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import date
from one_fm.api.notification import create_notification_log
from one_fm.utils import send_push_notification
from frappe.model.document import Document
from frappe.utils import today, get_url, date_diff, getdate, format_datetime
from one_fm.grd.doctype.medical_insurance import medical_insurance
from frappe.utils import get_datetime, add_to_date, getdate, get_link_to_form, now_datetime, nowdate, cstr
from one_fm.processor import sendemail
from one_fm.operations.doctype.operations_shift.operations_shift import get_shift_supervisor_user


class FingerprintAppointment(Document):

    def before_save(self):
        self.set_gr_operator()

    def set_gr_operator(self):
        if self.is_new() and not self.government_relations_operator:
            self.db_set('government_relations_operator', frappe.session.user)

    def validate(self):
        self.validate_pickup_requirements()
        self.validate_pick_up_location()

    
    def validate_pick_up_location(self):
        if not self.is_new():
            previous_doc = self.get_doc_before_save()
            if previous_doc.workflow_state == "Set Pick-up as Accommodation (Supervisor)" and self.workflow_state == "Pending Transportation Supervisor":
                if self.pickup_location != "Accommodation" or not self.accommodation:
                    frappe.throw("Pickup Location must be 'Accommodation' and Accommodation details must be provided to proceed")

    def validate_pickup_requirements(self):
        previous_doc = self.get_doc_before_save()
        if not previous_doc:
            return
        
        
        if previous_doc.workflow_state == "Pending Supervisor" and self.workflow_state not in {"Pending Supervisor", "Rejected"} and self.required_transportation == "Yes":
            if not self.pickup_location:
                frappe.throw("Pickup Location is required before proceeding")
            
            if not self.roster_action:
                frappe.throw("Roster Action is required before proceeding")
            
            if self.pickup_location == "Accommodation" and not self.accommodation:
                frappe.throw("Accommodation is required when Pickup Location is Accommodation")
            
            if self.pickup_location == "Operations Site" and not self.operations_site:
                frappe.throw("Operations Site is required when Pickup Location is Operations Site")


    def on_update(self):
        self.handle_workflow_state_change()

    def handle_workflow_state_change(self):
        if self.has_value_changed('workflow_state'):
            previous_doc = self.get_doc_before_save()
            previous_state = previous_doc.workflow_state if previous_doc else None
            
            if self.workflow_state in {"Pending Transportation Supervisor", "Pending PRO"}:
                self.update_employee_schedule()
            
            if self.workflow_state == "Pending PRO" and self.pickup_location:
                self.notify_employee_of_appointment()
            
            if previous_state == "Pending GR Operator" and self.workflow_state == "Set Pick-up as Accommodation (Supervisor)":
                self.notify_supervisor_of_gr_rejection()



    def notify_supervisor_of_gr_rejection(self):
        if not self.employee_supervisor:
            frappe.log_error(
                title=f"No supervisor found for {self.name}",
                message="Fingerprint Appointment Notification Error"
            )
            return
        

        formatted_datetime = format_datetime(self.date_and_time_confirmation, format_string="dd-MM-yyyy hh:mm a") if self.date_and_time_confirmation else 'Not specified'
        
        subject = 'Site Pickup Request Rejected - Fingerprint Appointment'
        message = f"""
            <p>This is to inform you that your request for site pickup for a fingerprint appointment has been rejected. You can change the pickup location to Accommodation.</p>
            <br>
            <p><strong>Employee Name:</strong> {self.full_name}</p>
            <p><strong>Date and Time Confirmation:</strong> {formatted_datetime}</p>
        """
        
        create_notification_log(subject, message, [self.employee_supervisor], self)

    def notify_employee_of_appointment(self):
        if self.workflow_state != "Pending PRO":
            return
        
        if not self.pickup_location:
            return
        
        if not self.date_and_time_confirmation:
            frappe.log_error(
                title=f"Date and Time Confirmation is missing for {self.name}",
                message="Fingerprint Appointment Notification Error"
            )
            return
        
        employee_user = frappe.db.get_value('Employee', self.employee, ['user_id', "employee_id"], as_dict=True)
        
        if not employee_user:
            frappe.log_error(
                title=f"No user found for employee {self.employee}",
                message="Fingerprint Appointment Notification Error"
            )
            return
        
        if self.pickup_location == "Accommodation":
            pickup_details = f"{self.pickup_location}: {self.accommodation_name or self.accommodation}"
        elif self.pickup_location == "Operations Site":
            site_name = frappe.db.get_value('Operations Site', self.operations_site, 'site_name')
            pickup_details = f"{self.pickup_location}: {site_name or self.operations_site}"
        else:
            pickup_details = self.pickup_location
        
        formatted_datetime = format_datetime(self.date_and_time_confirmation, format_string="dd-MM-yyyy hh:mm a")
        
        subject = 'Fingerprint Appointment Scheduled'
        message = f"""
            <p>Good day,</p>
            <p>Please be informed that you have been scheduled for a fingerprint appointment on <strong>{formatted_datetime}</strong> and will be picked up at the <strong>{pickup_details}</strong>.</p>
            <p>Please ensure to take your original passport with you.</p>
        """
        
        create_notification_log(subject, message, [employee_user.user_id], self)
        send_push_notification(employee_user.employee_id, subject, message)

    def update_employee_schedule(self):
        if not self.employee or not self.date_and_time_confirmation or self.roster_action == "No":
            return

        appointment_date = self.fetch_appointment_date

        existing_schedule = frappe.db.get_value('Employee Schedule',
            {
                'employee': self.employee,
                'date': appointment_date
            },
            ['name', 'roster_type'],
            as_dict=True
        )
        
        if existing_schedule:
            frappe.db.set_value('Employee Schedule', existing_schedule.name, {
                'employee_availability': 'Fingerprint Appointment',
                'operations_role': '',
                'shift': '',
                'site': '',
                'shift_type': '',
                'project': '',
                "reference_doctype": self.doctype,
                "reference_docname": self.name
            })
            frappe.msgprint(
                _('Employee Schedule {0} updated for Fingerprint Appointment').format(existing_schedule.name),
                indicator='blue'
            )
        else:
            
            new_schedule = frappe.get_doc({
                'doctype': 'Employee Schedule',
                'employee': self.employee,
                'date': appointment_date,
                'employee_availability': 'Fingerprint Appointment',
                'roster_type': 'Basic',
                'operations_role': '',
                'shift': '',
                'site': '',
                'shift_type': '',
                'project': '',
                'reference_doctype': self.doctype,
                'reference_docname': self.name
            })
            new_schedule.insert(ignore_permissions=True)
            frappe.msgprint(
                _('Employee Schedule {0} created for Fingerprint Appointment').format(new_schedule.name),
                indicator='green'
            )
        
        self.create_or_update_attendance(appointment_date)
        frappe.db.commit()

    def create_or_update_attendance(self, appointment_date):
        existing_attendance = frappe.db.get_value('Attendance',
            {
                'employee': self.employee,
                'attendance_date': appointment_date
            },
            'name'
        )
        
        if existing_attendance:
            frappe.db.set_value('Attendance', existing_attendance, 'status', 'On Hold')
            frappe.msgprint(
                _('Attendance {0} marked as On Hold').format(existing_attendance),
                indicator='orange'
            )
        else:
            new_attendance = frappe.get_doc({
            'doctype': 'Attendance',
            'employee': self.employee,
            'attendance_date': appointment_date,
            'status': 'On Hold',
            "reference_doctype": self.doctype,
            "reference_docname": self.name
            })
            new_attendance.insert(ignore_permissions=True)
            new_attendance.submit()
            frappe.msgprint(
            _('Attendance {0} created with On Hold status').format(new_attendance.name),
            indicator='green'
            )
            

    def on_submit(self):
        self.notify_grd_operator_of_rejection()
        self.validate_update_attendance_pro()
        self.db_set('completed_on', now_datetime())
        # if self.work_permit_type == "Local Transfer":
        #     self.recall_create_medical_insurance_transfer()

    def notify_grd_operator_of_rejection(self):
        if self.workflow_state != "Rejected":
            return
        
        document_creator = self.owner
        
        if not document_creator or document_creator == "Guest":
            frappe.log_error(
                title=f"No valid creator found for rejection notification",
                message="Fingerprint Appointment Notification Error"
            )
            return
        
        subject = f'Fingerprint Appointment Rejected - {self.full_name}'
        message = f"""
            <p>This is to inform you that a fingerprint appointment has been rejected.</p>
            <br>
            <p><strong>Employee Name:</strong> {self.full_name}</p>
            <p><strong>Date and Time Confirmation:</strong> {self.date_and_time_confirmation or 'Not specified'}</p>
            <p><strong>Reason for Rejection:</strong> {self.reason_for_rejection or 'Not provided'}</p>
        """
        
        create_notification_log(subject, message, [document_creator], self)

    

    def recall_create_medical_insurance_transfer(self):
        medical_insurance.creat_medical_insurance_for_transfer(self.employee)


    def before_one_day_of_appointment_date(self):
        today = date.today()
        if date_diff(getdate(self.date_and_time_confirmation),today) == -1 and self.preparing_documents == "No":
            self.notify_operator_to_prepare_for_fp()


    def notify_site_supervisor(self):
        """Notify site supervisor with the employee's appointment"""
        site = frappe.db.get_value("Employee",{'one_fm_civil_id':self.civil_id},['site'])
        if site:
            site_doc = frappe.get_doc("Operations Site",site)
            if site_doc:
                employee = frappe.get_doc("Employee", site_doc.site_supervisor)
                send_email_notification(self, [employee.user_id])

    def notify_shift_supervisor(self):
        """Notify shift supervisor with the employee's appointment"""
        shift = frappe.db.get_value("Employee",{"one_fm_civil_id":self.civil_id},"shift")
        if shift:
            shift_supervisor_user = get_shift_supervisor_user(shift)
            if shift_supervisor_user:
                send_email_notification(self, [shift_supervisor_user])

    @property
    def fetch_appointment_date(self):
        return get_datetime(self.date_and_time_confirmation).date()
        
    
    def validate_update_attendance_pro(self):
        if not self.is_new() and self.roster_action == "Yes":
            previous_doc = self.get_doc_before_save()
            
            if (previous_doc.workflow_state == "Pending PRO" and 
                self.workflow_state in {"Completed", "Reschedule Requested"}):
                
                if not self.date_and_time_confirmation:
                    frappe.throw(
                        _("Date and Time Confirmation is required"),
                        title=_("Missing Information")
                    )

                appointment_date = getdate(self.fetch_appointment_date)
                if appointment_date > getdate():
                    frappe.throw(
                        _("You cannot confirm fingerprint capturing before the appointment date."),
                        title=_("Future Appointment Date")
                    )
                
                new_status = "Fingerprint Appointment" if self.workflow_state == "Completed" else "Absent"
                
                updated_count = frappe.db.sql("""
                    UPDATE `tabAttendance`
                    SET status = %s, modified = NOW(), modified_by = %s
                    WHERE status = %s
                    AND attendance_date = %s
                    AND employee = %s
                """, (new_status, frappe.session.user, "On Hold", appointment_date, self.employee))
                
                if updated_count:
                    frappe.msgprint(
                        _("Updated {0} attendance record(s) to {1}").format(updated_count, new_status),
                        indicator="green"
                    )

    

def before_one_day_of_appointment_date():
    today = date.today()
    query = frappe.db.sql("""
        SELECT name FROM `tabFingerprint Appointment`
        WHERE
        DATEDIFF(date_and_time_confirmation, '{today}')=-1 AND preparing_documents='No'
    """, as_dict=1)
    for row in query:
        frappe.get_doc("Fingerprint Appointment", row.name).notify_operator_to_prepare_for_fp()

def nationality_requires_fp():
    """Getting the nationality that requires Fingerprint"""
    nationalities = frappe.db.get_single_value('Fingerprint Appointment Settings','nationality')
    array = nationalities.split(",")
    return array

# Create fingerprint appointment record once a month for renewals list
def creat_fp_record(preparation_name):
    nationalities = nationality_requires_fp()
    employee_in_preparation = frappe.get_doc('Preparation',preparation_name)
    if employee_in_preparation.preparation_record:
        for employee in employee_in_preparation.preparation_record:
            if employee.nationality in nationalities:
                if employee.renewal_or_extend == "Renewal" or employee.renewal_or_extend == "Local Transfer":
                    creat_fp(frappe.get_doc('Employee',employee.employee),employee.renewal_or_extend,preparation_name)

#Auto generated everyday at 8am
def get_employee_list():
    today = date.today()
    employee_list = frappe.db.get_list('Employee',['employee','residency_expiry_date'])
    for employee in employee_list:
        if date_diff(employee.residency_expiry_date,today) == -45:
            creat_fp(frappe.get_doc('Employee',employee.employee))

def creat_fp(employee,type,preparation):
    if type == "Renewal":
        fingerprint_appointment_type = "Renewal"
    if type == "Local Transfer":
        fingerprint_appointment_type = "Local Transfer"

    today = date.today()
    fp = frappe.new_doc('Fingerprint Appointment')
    fp.employee = employee.name
    fp.preparation = preparation
    fp.fingerprint_appointment_type = fingerprint_appointment_type
    fp.date_of_application = today
    fp.save(ignore_permissions=True)

def to_do_to_grd_users(subject, description, user):
    frappe.get_doc({
        "doctype": "ToDo",
        "subject": subject,
        "description": description,
        "allocated_to": user,
        "owner": user,
        "date": today(),
        "role":"Government Relations Operator",
        "reference_type":"Fingerprint Appointment"
    }).insert(ignore_permissions=True)

def send_email_notification(doc, recipients):
	page_link = get_url(doc.get_url())
	message = "<p>Please Review the Fingerprint Appointment for employee: {0} at {1}<a href='{2}'>{3}</a>.</p>".format(doc.employee_id,doc.date_and_time_confirmation,page_link, doc.name)
	sendemail(
		recipients= recipients,
		subject='{0} Fingerprint Appointment for employee Name:{1} - {2}'.format(doc.workflow_state, doc.full_name,doc.employee_id),
		message=message,
		reference_doctype=doc.doctype,
		reference_name=doc.name
	)

def send_email(doc, recipients, message, subject):
	sendemail(
		recipients= recipients,
		subject=subject,
		message=message,
		reference_doctype=doc.doctype,
		reference_name=doc.name
	)


def create_notification_log(subject, message, for_users, reference_doc):
    for user in for_users:
        frappe.get_doc({
            'doctype': 'Notification Log',
            'subject': subject,
            'email_content': message,
            'for_user': user,
            'document_type': 'Fingerprint Appointment',
            'document_name': reference_doc.name,
            'from_user': reference_doc.modified_by
        }).insert(ignore_permissions=True)



@frappe.whitelist()
def get_rejection_reason_options():
    try:
        meta = frappe.get_meta('Fingerprint Appointment')
        field = meta.get_field('reason_for_rejection')
        
        if field and field.options:
            return field.options
        return None
    except Exception as e:
        frappe.log_error(title=f"Error fetching rejection options: {str(e)}", message="Rejection Options Error")
        return None
    

def notify_supervisor_of_pending_fingerprint_appointment():
    appointments = frappe.db.sql("""
        SELECT 
            fa.name,
            fa.employee_supervisor,
            fa.employee,
            fa.modified_by,
            COALESCE(e.employee_name, fa.employee) as employee_name
        FROM `tabFingerprint Appointment` fa
        LEFT JOIN `tabEmployee` e ON fa.employee = e.name
        WHERE fa.workflow_state = 'Pending Supervisor'
    """, as_dict=1)
    
    for obj in appointments:
        if obj.employee_supervisor:
            create_notification_log(
                subject=f'Reminder: Action Required on Fingerprint Appointment for {obj.employee_name}',
                message=f'Reminder: You need to take action on {get_link_to_form("Fingerprint Appointment", obj.name, label="Fingerprint Appointment")} for {obj.employee_name}.',
                for_users=[obj.employee_supervisor],
                reference_doc=obj
            )