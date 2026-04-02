from ast import literal_eval
import frappe,json
import pandas as pd
from datetime import date

from frappe import _
from frappe.utils import (
    get_fullname, nowdate, getdate, date_diff, add_days,
    get_url_to_form, get_date_str, today, cint, flt
)

from hrms.hr.doctype.leave_application.leave_application import *
from one_fm.processor import sendemail
from erpnext.crm.utils import get_open_todos
from one_fm.api.api import push_notification_rest_api_for_leave_application
from one_fm.overrides.employee import NotifyAttendanceManagerOnStatusChange
from one_fm.utils import get_approver_user, leave_application_on_cancel, fetch_leave_types_update_employee_status, get_workflow_action_buttons_html, cancel_calendar_event, disable_out_of_office
from hrms.hr.utils import get_holidays_for_employee
from one_fm.one_fm.doctype.reliever_assignment.reliever_assignment import ReassignRelieverAssignment, reassign_responsibilities
from frappe.workflow.doctype.workflow_action.workflow_action import apply_workflow
from frappe.query_builder import DocType

def validate_active_staff(doc,event):
    emp_details = frappe.get_value("Employee",doc.employee,['status','relieving_date'],as_dict =1 )
    if emp_details.status != "Active" and emp_details.relieving_date:
        if getdate(emp_details.relieving_date)<getdate(doc.to_date):
            frappe.throw("The Employee Specified in the leave application is not Active.\nAlso, the leave application date exceeds the employee relieving date")


def close_leaves(leave_ids, user=None):
    approved_leaves = leave_ids
    not_approved_leaves = []
    for leave in leave_ids:
        try:
            leave_doc = frappe.get_doc("Leave Application", leave)
            leave_doc.status = "Approved"
            leave_doc.flags.ignore_validate = True
            leave_doc.submit()
        except:
            frappe.log_error(title="Error while closing {0}".format(leave))
            approved_leaves.remove(leave)
            not_approved_leaves.append(leave)
            continue
    frappe.db.commit()
    if user:
        message = "Please note that,"
        if approved_leaves and len(approved_leaves)>0:
            message += "<br/>the approved leave(s) are {0}".format(approved_leaves)
        if not_approved_leaves and len(not_approved_leaves)>0:
            message += "<br/>not approved leave(s) are {0}".format(not_approved_leaves)
        doc = frappe.new_doc('Notification Log')
        doc.subject = 'Close selected leave application'
        doc.email_content = message
        doc.for_user = user
        doc.save(ignore_permissions=True)

@frappe.whitelist()
def fix_sick_leave(names):
    selected_leaves = json.loads(names)
    if selected_leaves:
        if len(selected_leaves) <= 5:
            close_leaves(selected_leaves, frappe.session.user)
        else:
            frappe.enqueue(method=close_leaves, user=frappe.session.user, leave_ids=selected_leaves, queue='long',timeout=1200,job_name='Closing Leaves')
    else:
        frappe.throw("Please select atleast 1 row")

def is_app_user(emp):
    #Returns true if an employee is an app user or has a valid email address
    try:
        is_app_user = False
        user_details = frappe.get_all("Employee",{'name':emp},['user_id','employee_id'])
        if user_details:
            user_id = user_details[0].get("user_id")
            emp_id = user_details[0].get("employee_id")
            if user_id.split("@")[0].lower() == emp_id.lower():
                is_app_user = True
        return is_app_user
    except:
        pass


class LeaveApplicationOverride(LeaveApplication):
    def onload(self):
        super(LeaveApplicationOverride, self).onload()
        leave_attendances_count = 0
        if self.from_date and self.to_date and self.employee:
            leave_attendances_count = frappe.db.count(
                "Attendance",
                {
                    "employee": self.employee,
                    "attendance_date": ["between", (self.from_date, self.to_date)],
                    "leave_application": self.name,
                    "docstatus": ["<", 2]
                }
            )
        attendance_not_created = False
        if flt(self.total_leave_days) > leave_attendances_count:
            attendance_not_created = True
        self.set_onload("attendance_not_created", attendance_not_created)

    def close_todo(self):
        """Close the Todo document linked with a leave application
        """
        try:
            leave_todo = frappe.get_all("ToDo",{'reference_name':self.name},['name'])
            if leave_todo:
                for each in leave_todo:
                    frappe.db.set_value("ToDo",each.get("name"),'status','Closed')
                frappe.db.commit()
        except:
            frappe.log_error(message=frappe.get_traceback(), title="Error Closing ToDos")

    def on_submit(self):
        self.close_todo()
        self.close_shifts()
        self.validate_back_dated_application()
        self.update_attendance()
        self.close_leave_acknowledgement_if_below_threshold()

		# notify leave applier about approval
        if frappe.db.get_single_value("HR Settings", "send_leave_notification"):
            self.notify_employee()

        self.create_leave_ledger_entry()
        self.reload()

    def close_leave_acknowledgement_if_below_threshold(self):
        if self.leave_type == "Annual Leave":
            leave_balance = self.leave_balance or 0
            threshold = frappe.db.get_single_value("HR Settings", "annual_leave_threshold") or 60
            if leave_balance - self.total_leave_days <= threshold:
                query = """ 
                    UPDATE `tabLeave Acknowledgement Form`
                    SET is_active = 0
                    WHERE employee = %s
                    AND is_active = 1
                    """
                frappe.db.sql(query, (self.employee,))


    def validate_applicable_after(self):
        if self.leave_type:
            leave_type = frappe.get_doc("Leave Type", self.leave_type)
            if leave_type.applicable_after > 0:
                date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")
                leave_days = get_approved_leaves_for_period(
                    self.employee, False, date_of_joining, self.from_date
                )
                number_of_days = date_diff(getdate(self.from_date), date_of_joining)
                if number_of_days >= 0:
                    number_of_days = number_of_days - leave_days
                    if number_of_days < leave_type.applicable_after:
                        frappe.throw(
                            _("{0} applicable after {1} working days").format(
                                self.leave_type, leave_type.applicable_after
                            )
                        )

    def validate_reliever(self):
        if self.custom_reliever_ == self.employee:
            frappe.throw("Oops! You can't assign yourself as the reliever!")
        employee = frappe.get_value("Employee", self.employee, ["reports_to", "user_id"], as_dict=1)
        super_user_role = frappe.db.get_single_value("ONEFM General Setting", "super_user_role")
        user_roles = frappe.get_roles(employee.user_id)
        # If Reports to set or Super user role, then reliever is mandatory
        if (self.leave_type == 'Annual Leave' and (employee.reports_to or (super_user_role in user_roles)) and not self.custom_reliever_):
            frappe.throw(msg=_("Please ensure that a Reliever is set"), title=_("No Reliever set"))

    def close_shifts(self):
        #delete the shifts if a leave application is approved
        try:
            if self.status == "Approved":
                shift_assignment = frappe.db.sql(f"""SELECT name from `tabShift Assignment` where employee = '{self.employee}' and start_date BETWEEN '{self.from_date}' and '{self.to_date}' and docstatus = 1 """, as_dict=True)
                for shift in shift_assignment:
                    #unlink from attendance check
                    self.unlink_attendance_check(shift.name)
                    query =f"""DELETE from `tabShift Assignment` where name = '{shift.name}' and docstatus = 1 """
                    frappe.db.sql(query)
                frappe.msgprint(msg = f"Shift Assignments for {self.employee_name} between {self.from_date} and {self.to_date} have been deleted",alert=1)
        except:
            frappe.log_error(message=frappe.get_traceback(), title="Error Closing Shifts")

    def unlink_attendance_check(self, shift):
        attcheck_exists = frappe.db.exists("Attendance Check",  {"shift_assignment": shift})
        if attcheck_exists:
            frappe.db.set_value("Attendance Check", attcheck_exists, {'shift_assignment': "",'has_shift_assignment': 0})
        frappe.db.commit()

    def custom_notify_employee(self):
        try:
            template = frappe.db.get_single_value("HR Settings", "leave_status_notification_template")
            if not template:
                frappe.msgprint(_("Please set default template for Leave Status Notification in HR Settings."))
                return
            parent_doc = self
            employee = frappe.db.get_value("Employee", self.employee, "employee_name_in_arabic", as_dict=True) or {}
            leave_approver = frappe.db.get_value("Employee", {"company_email": self.leave_approver}, ["employee_name_in_arabic", "employee_name"], as_dict=True) or {}
            leave_type_in_arabic = frappe.db.get_value('Leave Type', self.leave_type, 'custom_leave_type_name_in_arabic')
            args = parent_doc.as_dict()
            args["employee_name_in_arabic"] = employee.get("employee_name_in_arabic")
            args["leave_approver_in_arabic"] = leave_approver.get("employee_name_in_arabic")
            args["leave_approver_in_english"] = leave_approver.get("employee_name")
            args["status"] = "Pending" if args.get("status") == "Open" else "Approved"

            get_translated_status = frappe.db.sql(
                """
                SELECT translated_text
                FROM `tabTranslation`
                WHERE LOWER(source_text) = LOWER(%s)
                """,
                (args.get('status'),),
                as_dict=True
            )
            translated_status = next(iter(get_translated_status or []), {})
            args["status_in_arabic"] = translated_status.get("translated_text", args.get("status"))
            args["leave_type_in_arabic"] = leave_type_in_arabic if leave_type_in_arabic else self.leave_type
            args["doc_url"] = get_url_to_form("Leave Application", self.name)
            email_template = frappe.get_doc("Email Template", template)
            if args.get("status") == "Approved":
                email_template = frappe.get_doc("Email Template", "Leave Employee Approval Notification")

            if not email_template:
                frappe.msgprint(_("Please set default template for Leave Status Notification in HR Settings."))
                return
            message = frappe.render_template(email_template.response_html, args)
            if is_app_user(self.employee):
                push_notification_rest_api_for_leave_application(self.employee,email_template.subject,message,self.name)
                frappe.msgprint(_("Push notification sent to {0} via mobile application").format(self.employee),alert=True)
            else:
                employee = frappe.get_doc("Employee", self.employee)
                if not employee.user_id:
                    return
                personal_email = employee.personal_email or ""
                sendemail(recipients= [employee.user_id, personal_email], subject="ا  طلب الإجازة تمت الموافقة عليه – تأكيد  Leave Application Approved – Confirmation",
                           message=message, reference_doctype=self.doctype, reference_name=self.name, attachments = [])
                frappe.msgprint("Email Sent to Employee {}".format(employee.employee_name))
        except Exception as e:
            frappe.log_error(message=frappe.get_traceback(), title="Leave Notification")


    def notify_employee(self):
        self.enqueue_notification_method(self.custom_notify_employee)

    def validate(self):
        validate_active_employee(self.employee)
        set_employee_name(self)
        self.validate_reliever()
        self.validate_dates()
        self.update_attachment_name()
        self.validate_balance_leaves()
        self.validate_leave_overlap()
        self.validate_max_days()
        self.show_block_day_warning()
        self.validate_block_days()
        self.validate_salary_processed_days()
        self.validate_attendance()
        self.set_half_day_date()
        if frappe.db.get_value("Leave Type", self.leave_type, "is_optional_leave"):
            self.validate_optional_leave()
        self.validate_applicable_after()
        self.validate_leave_application_operator()
        self.reset_status_on_amend()
        self.validate_loan_repayment()

    def validate_loan_repayment(self):
        if self.leave_type != "Annual Leave":
            return
        # Check if employee has unpaid loan >50%
        unpaid_loans = frappe.get_all("Loan",
            filters={
                "applicant": self.employee,
                "applicant_type": "Employee",
                "docstatus": 1,
                "status": ["!=", "Closed"]
            },
            fields=["name", "loan_amount", "total_amount_paid"]
        )

        # Filter loans where less than 50% has been repaid
        loans_under_50_percent = [
            loan for loan in unpaid_loans
            if flt(loan.total_amount_paid) < (flt(loan.loan_amount) * 0.5)
        ]

        if loans_under_50_percent:
            loan_names = [d.name for d in loans_under_50_percent]
            frappe.throw(
                f"Employee has not repaid at least 50% of the following loans: {', '.join(loan_names)}",
                title="Unpaid Loans"
            )

    @frappe.whitelist()
    def update_attendance(self):
        if self.status != "Approved" and not (self.status == "Open" and self.custom_leave_extension_request):
            return

        if self.total_leave_days > 20:
            frappe.enqueue(update_attendance_recods, self=self, is_async=True)
        else:
            update_attendance_recods(self)

    def create_or_update_attendance(self, attendance_name, date, status):
        if attendance_name:
            # update existing attendance, change absent to on leave
            doc = frappe.get_doc("Attendance", attendance_name)
            if doc.status != status and status == 'On Leave':
                doc.db_set({"status": status, "leave_type": self.leave_type, "leave_application": self.name})
            if doc.status != status and status == 'Holiday':
                doc.db_set({"status": status})
        else:
            # make new attendance and submit it
            doc = frappe.new_doc("Attendance")
            doc.employee = self.employee
            doc.employee_name = self.employee_name
            doc.attendance_date = date
            doc.company = self.company
            if status == "On Leave":
                doc.leave_type = self.leave_type
                doc.leave_application = self.name
            doc.status = status
            doc.flags.ignore_validate = True
            doc.insert(ignore_permissions=True)
            doc.save()
            doc.submit()


    @frappe.whitelist()
    def notify_leave_approver(self):
        """
        This function is to notify the leave approver and request his action.
        The Message sent through mail consist of 2 action: Approve and Reject.(It is sent only when the not sick leave.)

        Param: doc -> Leave Application Doc (which needs approval)

        It's a action that takes place on update of Leave Application.
        """
        #If Leave Approver Exist
        if self.workflow_state == "Pending Approval":
            try:
                employee =  frappe.db.get_values("Employee", self.employee, ["employee_name_in_arabic", "employee_id"], as_dict=1)
                line_manager = frappe.db.get_value("Employee", {"user_id": self.leave_approver}, "employee_name_in_arabic")
                args = frappe._dict({
                    "employee_name_in_arabic": employee[0].employee_name_in_arabic,
                    "employee_name": self.employee_name,
                    "line_manager": self.leave_approver_name,
                    "line_manager_in_arabic": line_manager,
                    "employee_id": employee[0].employee_id,
                    "leave_type": self.leave_type,
                    "from_date": self.from_date,
                    "to_date": self.to_date,
                    "total_leave_days": self.total_leave_days,
                    "workflow_state": self.workflow_state,
                    "posting_date": self.posting_date,
                    "base_url": frappe.utils.get_url(),
                    "doc_type":self.doctype,
                    "doc_name": self.name
                })
                template = frappe.db.get_single_value('HR Settings', 'leave_approval_notification_template')
                if not template:
                    frappe.msgprint(_("Please set default template for Leave Approval Notification in HR Settings."))
                    return
                email_template = frappe.get_doc("Email Template", template)

                if email_template.get("add_workflow_action_buttons_to_email"):
                    doc = frappe.get_doc(self.doctype, self.name)
                    user = self.leave_approver or ""
                    args["show_workflow_buttons"] = 1
                    args["workflow_buttons_html"] = get_workflow_action_buttons_html(doc, user)
                else:
                    args["show_workflow_buttons"] = 0
                    args["workflow_buttons_html"] = ""

                message = frappe.render_template(email_template.response_html, args)
                subject = f'طلب الإجازة تم تقديمه للموافقة – {employee[0].employee_name_in_arabic} | Leave Application Submitted for Approval  – {self.employee_name}'
                sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
                sendemail(sender=sender, recipients= [self.leave_approver],message=message, subject=subject, delayed=False, is_scheduler_email=False,is_external_mail=True)
            except Exception as e:
                frappe.log_error(message=frappe.get_traceback(), title="Leave Notification")

    def after_insert(self):
        self.assign_to_leave_approver()
        self.update_attachment_name()
        # self.enqueue_notification_method(self.notify_leave_approver)
        self.enqueue_notification_method(self.notify_employee)

    def enqueue_notification_method(self,method):
        frappe.enqueue(method,is_async=True, job_name= str("Leave Notification"),  queue="short")

    def update_attachment_name(self):
        if self.proof_documents:
            for each in self.proof_documents:
                if each.attachments:
                    all_files = frappe.get_all("File",{'file_url':each.attachments},['attached_to_name','name'])
                    if all_files and 'new' in all_files[0].attached_to_name:
                        frappe.db.set_value("File",all_files[0].name,'attached_to_name',self.name)

    def validate_attendance(self):
        pass

    def assign_to_leave_approver(self):
        #This function is meant to create a TODO for the leave approver
                try:
                    if self.name and self.leave_type == "Sick Leave" and self.workflow_state == "Pending Approval":
                        existing_assignment = frappe.get_all("ToDo",{'allocated_to':self.leave_approver,'reference_name':self.name})
                        if not existing_assignment:
                            frappe.get_doc(
                                {
                                    "doctype": "ToDo",
                                    "allocated_to": self.leave_approver,
                                    "reference_type": "Leave Application",
                                    "reference_name": self.name,
                                    "description": f'Please note that leave application {self.name} is awaiting your approval',
                                    "priority": "Medium",
                                    "status": "Open",
                                    "date": nowdate(),
                                    "assigned_by": frappe.session.user,
                                }
                            ).insert(ignore_permissions=True)
                except:
                    frappe.log_error(message=frappe.get_traceback(), title="Error assigning to User")
                    frappe.throw("Error while assigning leave application")

    def validate_dates(self):
        if frappe.db.get_single_value("HR Settings", "restrict_backdated_leave_application"):
            if self.from_date and getdate(self.from_date) < getdate(self.posting_date):
                allowed_role = frappe.db.get_single_value(
                    "HR Settings", "role_allowed_to_create_backdated_leave_application"
                )
                user = frappe.get_doc("User", frappe.session.user)
                user_roles = [d.role for d in user.roles]
                if not allowed_role:
                    frappe.throw(
                        _("Backdated Leave Application is restricted. Please set the {} in {}").format(
                            frappe.bold("Role Allowed to Create Backdated Leave Application"),
                            get_link_to_form("HR Settings", "HR Settings"),
                        )
                    )

                if allowed_role and allowed_role not in user_roles:
                    frappe.throw(
                        _("Only users with the {0} role can create backdated leave applications").format(
                            allowed_role
                        )
                    )

        if self.from_date and self.to_date and (getdate(self.to_date) < getdate(self.from_date)):
            frappe.throw(_("To date cannot be before from date"))

        if self.half_day and self.half_day_date:
            half_day_date = getdate(self.half_day_date)
            if half_day_date < getdate(self.from_date) or half_day_date > getdate(self.to_date):
                frappe.throw(_("Half Day Date should be between From Date and To Date"))

        if not is_lwp(self.leave_type):
            self.validate_dates_across_allocation()
            self.validate_back_dated_application()

    @frappe.whitelist()
    def notify(self, args):
        args = frappe._dict(args)
        # args -> message, message_to, subject
        if cint(self.follow_via_email):
            contact = args.message_to
            if not isinstance(contact, list):
                if not args.notify == "employee":
                    contact = frappe.get_doc("User", contact).email or contact

            sender = dict()
            sender["email"] = frappe.get_doc("User", frappe.session.user).email
            sender["full_name"] = get_fullname(sender["email"])
            # if is_user_id_company_prefred_email_in_employee(contact):
            try:
                sendemail(
                    recipients=[contact],
                    sender=sender["email"],
                    subject=args.subject,
                    message=args.message,
                )

                frappe.msgprint(_("Email sent to {0}").format(contact))
            except frappe.OutgoingEmailError:
                pass
            except:
                frappe.log_error(message=frappe.get_traceback(), title="Error Sending Notification")

    def on_cancel(self):
        emp = frappe.get_doc("Employee", self.employee)
        if self.status == "Cancelled"  and self.leave_type == 'Annual Leave' and getdate(self.from_date) <= getdate() <= getdate(self.to_date):
            emp.status = "Active"
            emp.save()
            frappe.db.commit()
        if self.custom_reliever_ and frappe.db.exists("Reliever Assignment", {"name": self.name}):frappe.enqueue(reassign_responsibilities, leave_application=self.name)
        self.create_leave_ledger_entry(submit=False)
        # notify leave applier about cancellation
        leave_application_on_cancel(self,"on_cancel")
        self.cancel_attendance()
        self.validate_cancel()
        send_leave_cancellation_email_to_leave_approver(self)
        frappe.enqueue(disable_out_of_office, employee_email=emp.user_id, queue='short', timeout=1200, is_async=True)
        frappe.enqueue(cancel_calendar_event, employee_email=emp.user_id, leave_application_name=self.name, queue='short', timeout=1200, is_async=True)

    def on_update(self):
        # from one_fm.utils import set_out_of_office
        if self.workflow_state == "New Dates Proposed":
            send_proposed_date_email(self.name)
        if self.status=='Rejected':
            attendance_range = []
            for i in pd.date_range(self.from_date, self.to_date):
                attendance_range.append(getdate(i))
            for i in attendance_range:
                if getdate()>i:
                    if frappe.db.exists("Attendance", {
                        'employee':self.employee,
                        'attendance_date': str(i),
                        'docstatus':1
                        }):
                        frappe.db.sql(f"""
                            UPDATE `tabAttendance` SET status='Absent', comment="Leave Appication {self.name} Rejected"
                            WHERE attendance_date='{str(i)}' and employee='{self.employee}'
                        """)
                    else:
                        frappe.get_doc({
                            'doctype':'Attendance',
                            'employee':self.employee,
                            'attendance_date':str(i),
                            'roster_type':'Basic',
                            'status':'Absent'
                        }).submit()

                    frappe.db.commit()
        if self.status == "Approved":
            today = getdate()

            if self.custom_reliever_:
                employee = frappe.get_doc("Employee", self.employee)
                custom_reliever = frappe.get_doc("Employee", self.custom_reliever_)
                employee_email = employee.company_email
                from_date = getdate(self.from_date)
                to_date = getdate(self.to_date)
                custom_reliever_name = self.custom_reliever_name
                custom_reliever = custom_reliever.user_id
                employee_name = self.employee_name

                # if today == from_date:
                #     set_out_of_office(employee_email, from_date, to_date, custom_reliever_name, custom_reliever, employee_name)

            if getdate(self.from_date) <= getdate() <= getdate(self.to_date):
                # frappe.db.set_value(), will not call the validate.
                if self.leave_type in fetch_leave_types_update_employee_status():
                    frappe.db.set_value("Employee", self.employee, "status", "Vacation")
            self.approve_attendance_check()
        self.clear_employee_schedules()

        # When workflow state changes from 'Draft' to 'Pending Approval'
        if self.has_value_changed('workflow_state') and self.workflow_state == 'Pending Approval':
            send_leave_details_email_to_employee(self)
            self.notify_leave_approver()

    def approve_attendance_check(self):
        """
            Approve attendance checks if there are any draft attendance checks for the period of leave
        """
        try:
            if frappe.db.exists("Attendance Check",{'docstatus':0,'employee':self.employee, 'date': ['between', (getdate(self.from_date), getdate(self.to_date))]}):
                att_checks = frappe.get_all("Attendance Check",{'docstatus':0,'employee':self.employee, 'date': ['between', (getdate(self.from_date), getdate(self.to_date))]},['name'])
                if att_checks:
                    for each in att_checks:
                        doc = frappe.get_doc("Attendance Check",each.name)
                        frappe.db.set_value("Attendance Check", doc.name, 'attendance_status', 'On Leave')
                        apply_workflow(doc, "Approve")
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(title = "Error Updating Attendance Check", message=frappe.get_traceback())
            frappe.throw("An Error Occured while updating Attendance Checks. Please review the error logs")

    def clear_employee_schedules(self):
        last_doc = self.get_doc_before_save()
        if last_doc and last_doc.get('workflow_state') != self.workflow_state:
            if self.workflow_state == "Approved":
                frappe.db.sql(
                    '''
                    DELETE FROM `tabEmployee Schedule` WHERE
                    employee = %s AND
                    date BETWEEN %s AND %s;
                    ''', (self.employee, self.from_date, self.to_date)
                )


    def validate_leave_application_operator(self):
        leave_application_operator = frappe.db.get_single_value("HR and Payroll Additional Settings", "default_leave_application_operator")

        if not leave_application_operator:
            frappe.throw(_("Leave Application Operator must be set in HR and Payroll Additional Settings"))

        self.custom_default_leave_application_operator = leave_application_operator


    def reset_status_on_amend(self):
        if self.amended_from and self.status == "Cancelled":
            self.status = "Open"
            self.custom_reason_for_cancel = ""
        elif self.workflow_state == "Approved":
            self.status = "Approved"


    def validate_cancel(self):
        if (self.workflow_state == "Approved" and self.custom_is_paid and not "System Manager" in frappe.get_roles()):
            frappe.throw(
                _("This leave application has been paid and cannot be canceled. Please contact the Administrator.")
            )

    @frappe.whitelist()
    def get_leave_extension_request(self):
        leave_extension_requests = frappe.get_all("Leave Extension Request", filters={"leave_application": self.name}, fields=["*"])
        return leave_extension_requests[0] if leave_extension_requests else None

    @frappe.whitelist()
    def create_leave_extension_request(self, new_resumption_date):
        designation, department, civil_id_assurance_level = frappe.db.get_value("Employee", self.employee, ["designation", "department", "custom_civil_id_assurance_level"])

        leave_extension_request = frappe.new_doc("Leave Extension Request")
        leave_extension_request.leave_application = self.name
        leave_extension_request.designation = designation
        leave_extension_request.civil_id_assurance_level = civil_id_assurance_level
        leave_extension_request.department = department
        leave_extension_request.new_resumption_date = new_resumption_date
        leave_extension_request.save()

        return leave_extension_request


def update_attendance_recods(self):
    if self.status != "Approved" and not (self.status == "Open" and self.custom_leave_extension_request):
        return

    holiday_dates = []
    if self.leave_type == 'Annual Leave' :
        holidays = get_holidays_for_employee(employee=self.employee, start_date=self.from_date, end_date=self.to_date, only_non_weekly=True)
        holiday_dates = [cstr(h.holiday_date) for h in holidays]

    for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
        date = dt.strftime("%Y-%m-%d")
        attendance_name = frappe.db.exists(
            "Attendance", dict(employee=self.employee, attendance_date=date, docstatus=("!=", 2))
        )

        # don't mark attendance for holidays
        # if leave type does not include holidays within leaves as leaves
        if date in holiday_dates:
            if attendance_name:
                # cancel and delete existing attendance for holidays
                attendance = frappe.get_doc("Attendance", attendance_name)
                attendance.flags.ignore_permissions = True
                if attendance.docstatus == 1:
                    attendance.db_set('status','Holiday')
                    frappe.db.commit()
            else:
                self.create_or_update_attendance(attendance_name, date, 'Holiday')
        else:
            self.create_or_update_attendance(attendance_name, date, 'On Leave')

    frappe.msgprint(_("Attendance are created for the leave Appication {0}!".format(self.name)), alert=True)

@frappe.whitelist()
def get_leave_details(employee, date):
    allocation_records = get_leave_allocation_records(employee, date)
    leave_allocation = {}
    precision = cint(frappe.db.get_single_value("System Settings", "float_precision", cache=True))

    for d in allocation_records:
        allocation = allocation_records.get(d, frappe._dict())
        remaining_leaves = get_leave_balance_on(
            employee, d, date, to_date=allocation.to_date, consider_all_leaves_in_the_allocation_period=True
        )

        end_date = allocation.to_date
        leaves_taken = get_leaves_for_period(employee, d, allocation.from_date, end_date) * -1
        leaves_pending = get_leaves_pending_approval_for_period(
            employee, d, allocation.from_date, end_date
        )
        expired_leaves = allocation.total_leaves_allocated - (remaining_leaves + leaves_taken)

        leave_allocation[d] = {
            "total_leaves": flt(allocation.total_leaves_allocated, precision),
            "expired_leaves": flt(expired_leaves, precision) if expired_leaves > 0 else 0,
            "leaves_taken": flt(leaves_taken, precision),
            "leaves_pending_approval": flt(leaves_pending, precision),
            "remaining_leaves": flt(remaining_leaves, precision),
        }

    # is used in set query
    lwp = frappe.get_list("Leave Type", filters={"is_lwp": 1}, pluck="name")

    return {
        "leave_allocation": leave_allocation,
        "leave_approver": get_leave_approver(employee),
        "lwps": lwp,
    }

@frappe.whitelist()
def get_leave_approver(employee):
    approver = get_approver_user(employee)
    return approver

@frappe.whitelist()
def send_proposed_date_email(doc_name):
    frappe.db.set_value("Leave Application",doc_name,'workflow_state',"New Dates Proposed")
    doc = frappe.get_doc("Leave Application", doc_name)
    employee =  frappe.db.get_values("Employee", doc.employee, ["employee_name_in_arabic", "employee_id"], as_dict=1)
    args = frappe._dict({
                    "employee_name_in_arabic": employee[0].employee_name_in_arabic,
                    "employee_name": doc.employee_name,
                    "employee_id": employee[0].employee_id,
                    "leave_type": doc.leave_type,
                    "from_date": doc.from_date,
                    "to_date": doc.to_date,
                    "total_leave_days": doc.total_leave_days,
                    "suggested_start_date" : doc.custom_propose_from_date,
                    "suggested_end_date" : doc.custom_propose_to_date,
                    "total_suggected_days" : doc.custom_total_propose_leave_days,
                    "workflow_state": doc.workflow_state,
                    "posting_date": doc.posting_date,
                    "base_url": frappe.utils.get_url(),
                    "doc_type":doc.doctype,
                    "doc_name": doc.name
                })
    message = frappe.render_template('one_fm/templates/emails/leave_proposal_status.html', args)
    subject = "طلب الإجازة – اقتراح تعديل تواريخ الإجازة|Leave Application – Suggested Adjustment to Leave Dates"
    sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
    employee = frappe.db.get_value("Employee", doc.employee, ["personal_email", "company_email","prefered_email"], as_dict=1)
    recipient = list({value for value in employee.values() if value is not None})
    sendemail(sender=sender, recipients= recipient,
            message=message, subject=subject, delayed=False, is_scheduler_email=False,is_external_mail=True)

@frappe.whitelist()
def send_leave_details_email_to_employee(self):
    employee_info = frappe.db.get_value("Employee", self.employee, ["employee_name_in_arabic","personal_email", "company_email","prefered_email"], as_dict=1)

    header_eng = "Leave Application Details – Confirmation"
    header_arabic = "تفاصيل طلب الإجازة - تأكيد"

    line_manager = frappe.db.get_value("Employee", {"user_id": self.leave_approver}, "employee_name_in_arabic")

    args = frappe._dict({
                    "doc_name": self.name,
                    "doc_type": self.doctype,
                    "header_eng": header_eng,
                    "header_arabic": header_arabic,
                    "employee_name_eng" : self.employee_name,
                    "employee_name_arabic" : employee_info.get("employee_name_in_arabic") or "",
                    "employee_id" : self.employee,
                    "leave_type_eng" : self.leave_type,
                    "from_date" : self.from_date,
                    "to_date" : self.to_date,
                    "total_leave_days" : self.total_leave_days,
                    "date_of_application" : self.posting_date,
                    "leave_approver" : self.leave_approver_name,
                    "leave_approver_in_arabic": line_manager,
                    "status":self.workflow_state,
                    "doc_link": get_url_to_form("Leave Application", self.name)
                })
    sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
    message = frappe.render_template('one_fm/templates/emails/leave_application_details_for_employee.html', args)
    subject = f"{header_arabic} | {header_eng}"
    recipients = list(set(filter(None, [
        employee_info.get("personal_email"),
        employee_info.get("company_email"),
        employee_info.get("prefered_email"),
    ])))
    sendemail(sender=sender, recipients= recipients,
            message=message, subject=subject, delayed=False, is_scheduler_email=False,is_external_mail=True)

@frappe.whitelist()
def send_leave_cancellation_email_to_leave_approver(self):
    employee_info = frappe.db.get_value("Employee", self.employee, ["employee_name_in_arabic"], as_dict=1)
    approver_info = frappe.db.get_value("Employee", {"user_id": self.leave_approver}, ["employee_name_in_arabic", "prefered_email"], as_dict=1)

    employee_arabic_name = employee_info.get('employee_name_in_arabic') if employee_info else ""
    approver_arabic_name = approver_info.get('employee_name_in_arabic') if approver_info else ""

    header_eng = f"Leave Cancellation Notification – {self.employee_name}"
    header_arabic = f"إشعار إلغاء الإجازة - {employee_arabic_name}"

    args = frappe._dict({
                    "doc_name": self.name,
                    "doc_type": self.doctype,
                    "header_eng": header_eng,
                    "header_arabic": header_arabic,
                    "approver_name_eng" : self.leave_approver_name,
                    "approver_name_arabic" : approver_arabic_name,
                    "employee_name_eng" : self.employee_name,
                    "employee_name_arabic" : employee_arabic_name,
                    "employee_id" : self.employee,
                    "leave_type_eng" : self.leave_type,
                    "from_date" : self.from_date,
                    "to_date" : self.to_date,
                    "total_leave_days" : self.total_leave_days,
                    "date_of_application" : self.posting_date,
                    "date_of_cancellation" : get_date_str(getdate(self.modified)),
                    "reason_of_cancellation" : self.custom_reason_for_cancel,
                    "doc_link": get_url_to_form("Leave Application", self.name)
                })

    sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
    message = frappe.render_template('one_fm/templates/emails/leave_cancellation_email.html', args)
    subject = f"{header_arabic} | {header_eng}"

    approver_email = approver_info.get("prefered_email") if approver_info else None
    sendemail(sender=sender, recipients = list(set(filter(None, [approver_email,]))),
            message=message, subject=subject, delayed=False, is_scheduler_email=False,is_external_mail=True)


class ReassignDutiesToReliever(NotifyAttendanceManagerOnStatusChange):


    def __init__(self, reliever: dict, leave_name: str, employee_object: dict) -> None:
        super().__init__(employee_object)
        self._reliever = reliever
        self._reassigned_documents = dict()
        self._leave_name = leave_name

    def reassign_operations_shift_supervisor(self):
        operation_shift_supervisors = self._operations_shift_supervisor
        if operation_shift_supervisors:
            for obj in operation_shift_supervisors:
                frappe.db.set_value("Operations Shift", obj, "supervisor", self._reliever.name)
            self._reassigned_documents.update({"Operations Shift": operation_shift_supervisors})


    def reassign_operations_site_supervisor(self):
        operations_site_supervisor = self._operations_site_supervisor
        if operations_site_supervisor:
            for obj in operations_site_supervisor:
                frappe.db.set_value("Operations Site", obj, "site_supervisor", self._reliever.name)
            self._reassigned_documents.update({"Operations Site": operations_site_supervisor})


    def reassign_projects_manager(self):
        projects_manager = self._projects_manager
        if projects_manager:
            for obj in projects_manager:
                frappe.db.set_value("Project", obj, "project_manager", self._reliever.name)
            self._reassigned_documents.update({"Project": projects_manager})

    def reassign_reports_to(self):
        reports_to = self._employee_reports_to
        if reports_to:
            for obj in reports_to:
                frappe.db.set_value("Employee", obj, "reports_to", self._reliever.name)
            self._reassigned_documents.update({"Employee": [obj.name for obj in reports_to]})


    def reassign_operations_manager(self):
        if self._operation_manager:
            frappe.db.set_value("Operation Settings", "Operation Settings", "default_operation_manager", self._reliever.user_id)
            self._reassigned_documents.update({"Operation Settings": ["default_operation_manager", ]})

    def reassign_attendance_manager(self):
        if self._attendance_manager:
            frappe.db.set_value("ONEFM General Setting", "ONEFM General Setting", "attendance_manager", self._reliever.name)
            self._reassigned_documents.update({"ONEFM General Setting": ["attendance_manager",]})


    def reassign(self):
        self.reassign_operations_shift_supervisor()
        self.reassign_operations_site_supervisor()
        self.reassign_projects_manager()
        self.reassign_reports_to()
        self.reassign_operations_manager()
        self.reassign_attendance_manager()
        if self._reassigned_documents:
            for key, value in self._reassigned_documents.items():
                reassigned_documents = frappe.new_doc('Reassigned Documents')
                reassigned_documents.parent=self._leave_name,
                reassigned_documents.parentfield="custom_reassigned_documents"
                reassigned_documents.parenttype="Leave Application"
                reassigned_documents.reassigned_doctype=key
                reassigned_documents.names=str(value)
                reassigned_documents.insert()


class ReassignDocumentToLeaveApplicant:

    def __init__(self, reassigned_documents: list, employee: dict):
        self._employee = employee
        self._reassigned_documents = reassigned_documents


    def reassign_operations_site(self, sites: list):
        for obj in sites:
            frappe.db.set_value("Operations Site", obj, "site_supervisor", self._employee.name)


    def reassign_operation_shift(self, shifts: list):
        for obj in shifts:
            frappe.db.set_value("Operations Shift", obj, "supervisor", self._employee.name)

    def reassign_projects(self, projects: list):
        for obj in projects:
            frappe.db.set_value("Project", obj, "project_manager", self._employee.name)

    def reassign_reports_to(self, reports_to: list):
        for obj in reports_to:
            frappe.db.set_value("Employee", obj, "reports_to", self._employee.name)

    def reassign_general_settings(self, settings: list):
        for obj in settings:
            frappe.db.set_value("Operation Settings", "Operation Settings", obj, self._employee.user_id)

    def reassign_operation_settings(self, settings: list):
        for obj in settings:
            frappe.db.set_value("ONEFM General Setting", "ONEFM General Setting", obj, self._employee.name)


    def reassign(self):
        documents = {obj.get("reassigned_doctype"): literal_eval(obj.get("names"))for obj in self._reassigned_documents}
        for key, value in documents.items():
            if key == "Operations Site":
                self.reassign_operations_site(sites=value)

            if key == "Operations Shift":
                self.reassign_operation_shift(shifts=value)

            if key == "Project":
                self.reassign_projects(projects=value)

            if key == "Employee":
                self.reassign_reports_to(reports_to=value)

            if key == "Operation Settings":
                self.reassign_general_settings(settings=value)

            if key == "ONEFM General Setting":
                self.reassign_operation_settings(settings=value)


@frappe.whitelist()
def validate_leave_overlap(employee, from_date, to_date, name=None):
    overlapping_leave = frappe.db.sql("""
        SELECT name FROM `tabLeave Application`
        WHERE employee = %(employee)s
        AND docstatus < 2
        AND status IN ('Open', 'Approved')
        AND to_date >= %(from_date)s
        AND from_date <= %(to_date)s
        AND name != %(name)s
    """, {
        "employee": employee,
        "from_date": from_date,
        "to_date": to_date,
        "name": name
    }, as_dict=True)

    if overlapping_leave:
        frappe.throw("Employee {0} has already applied between {1} and {2}".format(name,from_date,to_date))
    return "valid"

def update_employee_status_after_leave():
    today_date = getdate(today())
    
    leave_applications = frappe.get_all(
        "Leave Application",
        filters={
            "resumption_date": today_date,
            "status": "Approved",
            "docstatus": 1,
            "leave_type": "Annual Leave"
        },
        fields=["name", "employee", "from_date", "leave_type"]
    )
    
    if not leave_applications:
        return
    
    employee_ids = [la.employee for la in leave_applications if la.get("employee")]
    employee_map = {}
    if employee_ids:
        employees = frappe.get_all(
            "Employee",
            filters={"name": ["in", employee_ids]},
            fields=["name", "shift_working", "one_fm_provide_accommodation_by_company", "status"]
        )
        employee_map = {emp.name: emp for emp in employees}
    
    for leave_app in leave_applications:
        try:
            employee_doc = employee_map.get(leave_app.employee)
            if not employee_doc:
                continue
            
            new_status = None
            shift_working = employee_doc.shift_working
            provide_accommodation = employee_doc.one_fm_provide_accommodation_by_company
            
            if not shift_working:
                new_status = "Active"

            elif shift_working and not provide_accommodation:
                new_status = "Not Returned from Leave"

            elif shift_working and provide_accommodation:
                has_checkin = frappe.db.exists(
                    "Accommodation Checkin Checkout",
                    {
                        "type": "IN",
                        "employee": employee_doc.name,
                        "checkin_checkout_date_time": [">", leave_app.from_date],
                    }
                )
                new_status = "Active" if has_checkin else "Not Returned from Leave"
            
            if new_status and employee_doc.status != new_status:
                old_status = employee_doc.status
                frappe.db.set_value("Employee", employee_doc.name, "status", new_status)

                try:
                    frappe.get_doc({
                        "doctype": "Comment",
                        "comment_type": "Info",
                        "reference_doctype": "Employee",
                        "reference_name": employee_doc.name,
                        "content": f"Status changed from {old_status} to {new_status} after leave resumption. Leave Application: {leave_app.name}"
                    }).insert(ignore_permissions=True)
                except Exception as e:
                    frappe.log_error(
                        message=frappe.get_traceback(),
                        title=f"Error creating status update comment for employee {employee_doc.name}"
                    )
        except Exception as e:
            frappe.log_error(
                message=frappe.get_traceback(),
                title=f"Error updating status for employee {leave_app.employee}"
            )
    
    frappe.db.commit()

def remind_annual_leave_employees_to_helpdesk_user():
    """
        Send a reminder email to helpdesk user with the list of employees whose leave ends soon.
    """
    helpdesk_email = frappe.db.get_single_value("HR Settings", "helpdesk_email")
    if not helpdesk_email:
        return

    employees_on_annual_leave = get_employees_whose_leave_ends_in(leave_ends_in=6)

    if not employees_on_annual_leave:
        return

    message = frappe.render_template("one_fm/templates/emails/reminder_employees_on_annual_leave.html", {"employees": employees_on_annual_leave})
    sendemail(
        recipients=[helpdesk_email],
        subject="Reminder: Employees' Annual Leave Ending in 7 Days",
        message=message,
        is_external_mail=True
    )

def get_employees_whose_leave_ends_in(leave_ends_in=0, leave_type="Annual Leave", shift_working=1):
    to_date = add_days(getdate(today()), leave_ends_in)

    LeaveApplication = DocType("Leave Application")
    Employee = DocType("Employee")

    employees_on_leave = (
        frappe.qb.from_(LeaveApplication)
        .join(Employee)
        .on(LeaveApplication.employee == Employee.name)
        .select(
            LeaveApplication.employee,
            LeaveApplication.employee_name,
            LeaveApplication.from_date,
            LeaveApplication.to_date,
            LeaveApplication.leave_type,
            Employee.designation,
            Employee.department
        )
        .where(
            (LeaveApplication.docstatus == 1) &
            (LeaveApplication.status == "Approved") &
            (LeaveApplication.leave_type == leave_type) &
            (LeaveApplication.to_date == to_date) &
            (Employee.shift_working == shift_working)
        )
    ).run(as_dict=True)

    return employees_on_leave
