import frappe,json
from frappe import _
from frappe.utils import get_fullname, nowdate, add_to_date
from hrms.hr.doctype.leave_application.leave_application import *
from one_fm.processor import sendemail
from frappe.desk.form.assign_to import add
from one_fm.api.notification import create_notification_log
from frappe.utils import getdate
import pandas as pd
from one_fm.api.api import push_notification_rest_api_for_leave_application
from one_fm.processor import is_user_id_company_prefred_email_in_employee
from hrms.hr.utils import get_holidays_for_employee

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
            frappe.log_error("Error while closing {0}".format(leave))
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
            frappe.log_error(frappe.get_traceback(),"Error Closing ToDos")

    def on_submit(self):
        self.close_todo()
        self.close_shifts()
        self.update_attendance()
        return super().on_submit()


    def close_shifts(self):
        #delete the shifts if a leave application is approved
        try:
            if self.status == "Approved":
                query =f"""DELETE from `tabShift Assignment` where employee = '{self.employee}' and start_date BETWEEN '{self.from_date}' and '{self.to_date}' and docstatus = 1 """
                frappe.db.sql(query)
                frappe.msgprint(msg = f"Shift Assignments for {self.employee_name} between {self.from_date} and {self.to_date} have been deleted",alert=1)
        except:
            frappe.log_error(frappe.get_traceback(),"Error Closing Shifts")
        

    def notify_employee(self):
        template = frappe.db.get_single_value("HR Settings", "leave_status_notification_template")
        if not template:
            frappe.msgprint(_("Please set default template for Leave Status Notification in HR Settings."))
            return
        parent_doc = frappe.get_doc("Leave Application", self.name)
        args = parent_doc.as_dict()
        email_template = frappe.get_doc("Email Template", template)
        message = frappe.render_template(email_template.response, args)
        if is_app_user(self.employee):
            push_notification_rest_api_for_leave_application(self.employee,email_template.subject,message,self.name)
            frappe.msgprint(_("Push notification sent to {0} via mobile application").format(self.employee),alert=True)
        else:
            employee = frappe.get_doc("Employee", self.employee)
            if not employee.user_id:
                return
            sendemail(recipients= [employee.user_id], subject="Leave Application", message=message,
                    reference_doctype=self.doctype, reference_name=self.name, attachments = [])
            frappe.msgprint("Email Sent to Employee {}".format(employee.employee_name))


    def validate(self):
        validate_active_employee(self.employee)
        set_employee_name(self)
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

    def update_attendance(self):
        if self.status != "Approved":
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
                        print('True')
                        attendance.db_set('status','Holiday')
                        frappe.db.commit()
                else:
                    self.create_or_update_attendance(attendance_name, date, 'Holiday')
            else:
                self.create_or_update_attendance(attendance_name, date, 'On Leave')
            

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
        if self.leave_approver:
            parent_doc = frappe.get_doc('Leave Application', self.name)
            args = parent_doc.as_dict() #fetch fields from the doc.
            args.update({"base_url": frappe.utils.get_url()})

            #Fetch Email Template for Leave Approval. The email template is in HTML format.
            template = frappe.db.get_single_value('HR Settings', 'leave_approval_notification_template')
            if not template:
                frappe.msgprint(_("Please set default template for Leave Approval Notification in HR Settings."))
                return
            email_template = frappe.get_doc("Email Template", template)
            message = frappe.render_template(email_template.response_html, args)

            if self.proof_documents:
                proof_doc = self.proof_documents
                for p in proof_doc:
                    message+=f"<hr><img src='{p.attachments}' height='400'/>"

            # attachments = get_attachment(doc) // when attachment needed

            #send notification
            sendemail(recipients= [self.leave_approver], subject="Leave Application", message=message,
                    reference_doctype=self.doctype, reference_name=self.name, attachments = [])

            employee_id = frappe.get_value("Employee", {"user_id":self.leave_approver}, ["name"])

            if self.total_leave_days == 1:
                date = "for "+cstr(self.from_date)
            else:
                date = "from "+cstr(self.from_date)+" to "+cstr(self.to_date)

            push_notication_message = self.employee_name+" has applied for "+self.leave_type+" "+date+". Kindly, take action."
            push_notification_rest_api_for_leave_application(employee_id,"Leave Application", push_notication_message, self.name)

    def after_insert(self):
        self.assign_to_leave_approver()
        self.update_attachment_name()
        self.notify_leave_approver()

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
                    if self.name and self.leave_type =="Sick Leave":
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
                    frappe.log_error(frappe.get_traceback(),"Error assigning to User")
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
                frappe.log_error(frappe.get_traceback(),"Error Sending Notification")

    def on_cancel(self):
        if self.status == "Cancelled"  and self.leave_type == 'Annual Leave' and getdate(self.from_date) <= getdate() <= getdate(self.to_date):
            emp = frappe.get_doc("Employee", self.employee)
            emp.status = "Active"
            emp.save()
            frappe.db.commit()
        self.create_leave_ledger_entry(submit=False)
		# notify leave applier about cancellation
        self.cancel_attendance()


    def on_update(self):
        if self.status=='Rejected':
            self.notify_employee()
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
            if getdate(self.from_date) <= getdate() <= getdate(self.to_date):
                emp = frappe.get_doc("Employee", self.employee)
                emp.status = "Vacation"
                emp.save()
                frappe.db.commit()
            if frappe.db.exists("Attendance Check",{'employee':self.employee, 'date': ['between', (getdate(self.from_date), getdate(self.to_date))]}):
                att_check = frappe.get_doc("Attendance Check",{'employee':self.employee, 'date': ['between', (getdate(self.from_date), getdate(self.to_date))]})
                att_check.db_set("workflow_state", "Approved")
                att_check.db_set('attendance_status','On Leave')
                frappe.db.commit()

@frappe.whitelist()
def get_leave_approver(employee):
    leave_approver, department = frappe.db.get_value(
        "Employee", employee, ["leave_approver", "department"]
    )

    if not leave_approver and department:
        leave_approver = frappe.db.get_value(
            "Department Approver",
            {"parent": department, "parentfield": "leave_approvers", "idx": 1},
            "approver",
        )

    return leave_approver

@frappe.whitelist()
def employee_leave_status():
    """
    This method is to change the status of employee Doc from Active to Vacation, when Leave starts.
    It also changes it back to Active when the leave ends.
    The method is called as a cron job before  assigning shift.
    """
    today = getdate()
    yesterday = add_to_date(today, days=-1)

    start_leave = frappe.get_list("Leave Application", {'from_date': today, 'status':'Approved'}, ['employee'])
    end_leave = frappe.get_list("Leave Application", {'to_date': yesterday, 'status':'Approved'}, ['employee'])

    frappe.enqueue(process_change,start_leave=start_leave,end_leave=end_leave, is_async=True, queue="long")




def process_change(start_leave, end_leave):
    change_employee_status(start_leave, "Vacation")
    change_employee_status(end_leave, "Active")

def change_employee_status(employee_list, status):
    for e in employee_list:
        emp = frappe.get_doc("Employee", e.employee)
        emp.status = status
        emp.save()
    frappe.db.commit()
