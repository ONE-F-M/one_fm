# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt
from datetime import datetime, timedelta
from itertools import chain

from frappe.model.document import Document
import frappe,json
from frappe import _
from frappe.desk.form.assign_to import add as add_assignment
from frappe.utils import nowdate, add_to_date, cstr, add_days, today, format_date, now, get_url_to_form
from one_fm.utils import (
    production_domain, 
    fetch_attendance_manager_user_obj,
    get_approver
)

class AttendanceCheck(Document):
    def before_insert(self):
        attendance_exist = frappe.db.get_value(self.doctype, {
            'employee':self.employee, 'date':self.date, 'roster_type':self.roster_type
        }, ["name", "workflow_state"], as_dict=1)
        if attendance_exist:
            frappe.throw(f"""{self.doctype} already exist for {self.employee} on {self.date} with name {attendance_exist.name}""")
        employee = frappe.get_doc("Employee", self.employee)
        # set shift assignment
        shift_assignment = frappe.db.get_value("Shift Assignment", {
            "employee":self.employee, "start_date":self.date, "roster_type":self.roster_type, "status":"Active", "docstatus":1},
            ["name", "start_date", "start_datetime", "end_datetime"],
            as_dict=1
        )
        if shift_assignment:
            self.shift_assignment = shift_assignment.name
            self.start_time = shift_assignment.start_datetime
            self.end_time = shift_assignment.end_datetime

            # check checkin logs
            checkins = frappe.db.sql(f"""
                SELECT ec.name, ec.owner, ec.creation, ec.modified, ec.modified_by, 
                    ec.docstatus, ec.idx, ec.employee, ec.employee_name, ec.log_type, 
                    ec.late_entry, ec.early_exit, ec.time, ec.date, ec.skip_auto_attendance, 
                    ec.shift_actual_start, ec.shift_actual_end, ec.shift_assignment, 
                    ec.operations_shift, ec.shift_type, ec.roster_type, ec.operations_site, 
                    ec.project, ec.company, ec.operations_role, ec.post_abbrv,ec.shift_permission, 
                    ec.actual_time, 
                    MIN(CASE WHEN ec.log_type = 'IN' THEN ec.time END) AS earliest_time,
                    MAX(CASE WHEN ec.log_type = 'OUT' THEN ec.time END) AS latest_time,
                    MIN(CASE WHEN ec.log_type = 'IN' THEN ec.name END) AS in_name, 
                    MAX(CASE WHEN ec.log_type = 'OUT' THEN ec.name END) AS out_name
                FROM 
                    `tabEmployee Checkin` ec
                WHERE 
                    ec.shift_assignment="{self.shift_assignment}"
                GROUP BY 
                    ec.shift_assignment;
            """, as_dict=1)
            if checkins:
                if checkins[0].in_name:
                    self.checkin_record=checkins[0].in_name
                if checkins[0].out_name:
                    self.checkout_record=checkins[0].out_name

        attendance_request = frappe.db.sql(f"""
            SELECT * FROM `tabAttendance Request`
            WHERE '{self.date}' BETWEEN from_date AND to_date
            AND docstatus=1
        """, as_dict=1)
        if attendance_request:
            self.attendance_request=attendance_request[0].name
        
        # check shift permission
        shift_permission = frappe.db.get_value("Shift Permission", {
            "employee":self.employee, "date":self.date, "roster_type":self.roster_type, "docstatus":["!=", 0]},
            ["name"], as_dict=1
        )
        if shift_permission:
            self.shift_permission = shift_permission
            self.has_shift_permissions = 1

        # get approver
        if employee.reports_to:
            self.reports_to = employee.reports_to
        if employee.shift:
            shift_supervisor = frappe.db.get_value('Operations Shift', employee.shift, 'supervisor')
            self.shift_supervisor = shift_supervisor 
        if employee.site:
            site_supervisor = frappe.db.get_value('Operations Site', employee.site, 'account_supervisor')
            self.site_supervisor = site_supervisor              
        
    def after_insert(self):
        """
            Assign document to supervisors
        """
        pass


    def validate(self):
        self.validate_justification()

    def validate_justification(self):
        '''
            The method is used to validate the justification and its dependend fields
        '''
        if self.attendance_status == 'Present':
            if not self.justification:
                frappe.throw("Please select Justification")

            if self.justification != "Other":
                self.other_reason = ""

            if self.justification == "Other":
                if not self.other_reason:
                    frappe.throw("Please write the other Reason")

            if self.justification != "Mobile isn't supporting the app":
                self.mobile_brand = ""
                self.mobile_model = ""


            if self.justification == "Mobile isn't supporting the app":
                if not self.mobile_brand:
                    frappe.throw("Please select mobile brand")
                if not self.mobile_model:
                    frappe.throw("Please Select Mobile Model")

            if self.justification not in ["Invalid media content","Out-of-site location", "User not assigned to shift", "Other"]:
                self.screenshot = ""

            if self.justification in ["Invalid media content","Out-of-site location", "User not assigned to shift"]:
                if not self.screenshot:
                    frappe.throw("Please Attach ScreenShot")
        else:
            self.justification = ""

        if self.justification == "Approved by Administrator":
            if not check_attendance_manager(email=frappe.session.user):
                frappe.throw("Only the Attendance manager can select 'Approved by Administrator' ")


    def validate_unscheduled_check(self):
        #If Check is unscheduled,confirmed user roles before submitting
        if self.is_unscheduled:
            if check_attendance_manager(frappe.session.user):
                return
            elif "Shift Supervisor" in frappe.get_roles(frappe.session.user) or "Site Supervisor" in frappe.get_roles(frappe.session.user):
                shift_assignments = frappe.db.get_list("Shift Assignment", filters={'docstatus':1,'start_date':self.date,'employee':self.employee}, fields="*")
                if not shift_assignments:
                    frappe.throw(f"No Shift Assignments found for {self.employee_name} on {self.date} Please create one")
            else:
                frappe.throw("Only Shift/Site Supervisors and Attendance Managers have permission to submit unscheduled Attendance Checks")

    def on_submit(self):
        shift_working = frappe.db.get_value("Employee", self.employee, "shift_working")
        if self.attendance_status == "Present" and shift_working:
            self.validate_unscheduled_check()
        if self.attendance_status == "On Leave":
            self.check_on_leave_record()
        if self.attendance_status == "Day Off" and shift_working:
            validate_day_off(self,convert=0)
        self.validate_justification_and_attendance_status()
        self.mark_attendance()

    def mark_attendance(self):
        if self.workflow_state == 'Approved':
            comment = ""
            logs = []
            check_attendance = frappe.db.get_value('Attendance',
                {'attendance_date': self.date, 'employee': self.employee, 'docstatus': ['<', 2],
                'roster_type':self.roster_type
                }, ["status", "name"], as_dict=1)
            comment = "Created from Attendance Check"
            if check_attendance:
                if check_attendance.status == "Absent":
                    if self.attendance_status == "Absent":
                        pass
                    elif self.attendance_status in ["Present", "Day Off", "On Leave"]:
                        working_hours=0
                        if self.shift_assignment:
                            working_hours = frappe.db.get_value("Operations Shift",
                                frappe.db.get_value("Shift Assignment", self.shift_assignment, 'shift'), 'duration')
                        else:
                            working_hours = 8 if self.attendance_status == 'Present' else 0
                        frappe.db.sql(f"""UPDATE `tabAttendance`
                            SET status = '{self.attendance_status}',
                            reference_doctype="{self.doctype}",
                            reference_docname="{self.name}",
                            modified="{str(now())}",
                            working_hours={working_hours},
                            modified_by="{frappe.session.user}",
                            comment="{comment}"
                            WHERE name = "{check_attendance.name}"
                            """
                        )
                        frappe.db.commit()
            else:
                att = frappe.new_doc("Attendance")
                att.employee = self.employee
                att.employee_name = self.employee_name
                att.attendance_date = self.date
                att.status = self.attendance_status
                att.roster_type = self.roster_type
                att.reference_doctype = "Attendance Check"
                att.reference_docname = self.name
                att.comment = comment
                if not frappe.db.get_value("Employee", self.employee, "attendance_by_timesheet"):
                    if self.shift_assignment:
                        att.shift_assignment = self.shift_assignment
                    else:
                        shift_assignment = frappe.db.exists("Shift Assignment", {
                                'employee':self.employee, 'start_date':self.date, 'roster_type':self.roster_type
                            })
                        if shift_assignment:
                            att.shift_assignment = shift_assignment
                    if att.shift_assignment and att.status=='Present':
                        att.working_hours = frappe.db.get_value("Operations Shift",
                            frappe.db.get_value("Shift Assignment", att.shift_assignment, 'shift'), 'duration')
                if att.status != 'Day Off':
                    if not att.working_hours:
                        att.working_hours = 8 if self.attendance_status == 'Present' else 0
                att.insert(ignore_permissions=True)
                att.submit()
                for i in logs:
                    frappe.db.set_value("Employee Checkin", i.name, "attendance", att.name)


    def validate_justification_and_attendance_status(self):
        if not self.attendance_status:
            frappe.throw(_('To Approve the record set Attendance Status'))

    def check_on_leave_record(self):
        submited_leave_record = frappe.db.sql(f"""SELECT leave_type
            FROM `tabLeave Application`
            WHERE employee = '{self.employee}'
                AND '{self.date}' >= from_date AND '{self.date}' <= to_date
                AND workflow_state = 'Approved'
                AND docstatus = 1
        """,as_dict=True)

        if  submited_leave_record:
            return
        else:
            draft_leave_records = frappe.db.sql(f"""select employee_name,leave_approver_name,name
                FROM `tabLeave Application`
                WHERE employee = '{self.employee}'
                    AND '{self.date}' >= from_date AND '{self.date}' <= to_date
                    AND docstatus = 0
            """,as_dict=True)
            if draft_leave_records:
                doc_url = get_url_to_form('Leave Application',draft_leave_records[0].get('name'))
                error_template = frappe.render_template('one_fm/templates/emails/attendance_check_alert.html',context={'doctype':'Leave Application','current_user':frappe.session.user,'date':self.date,'approver':draft_leave_records[0].get('leave_approver_name'),'page_link':doc_url,'employee_name':self.employee_name})
                frappe.throw(error_template)
            else:
                frappe.throw(f"""
                <p>Please note that a Leave Application has not been created for <b>{self.employee_name}</b>.</p>
                <hr>
                To create a leave application <a class="btn btn-primary btn-sm" href="{frappe.utils.get_url('/app/leave-application/new-leave-application-1')}?doc_id={self.name}&doctype={self.doctype}" target="_blank" onclick=" ">Click Here</a>
                 """)



def get_attendance_by_timesheet_employees(employees,attendance_date):
    #Get the applicable employees if the current date falls on a public holiday
    try:
        default_company = frappe.defaults.get_defaults().company
        cond = ''
        if not default_company:
            default_company = frappe.get_last_doc("Company").name
        holiday_lists = frappe.db.sql(f"""SELECT  h.parent from `tabHoliday` h
                                WHERE  h.holiday_date = '{attendance_date}'
                            """, as_dict=1)
        if holiday_lists:
            default_holiday_list = frappe.get_value("Company",default_company,'default_holiday_list')
            holiday_lists =[i.parent for i in holiday_lists]
            if default_holiday_list in holiday_lists:
                if len(holiday_lists)>1:
                    cond += f"  and holiday_list not in {tuple(holiday_lists)}"
                else:
                    cond += f"  and holiday_list !='{holiday_lists[0]}'"
            else:
                if len(holiday_lists)>1:
                    cond+=f" and holiday_list is Not NULL and holiday_list not in {tuple(holiday_lists)}"
                else:
                    cond+=f" and holiday_list is Not NULL and holiday_list != '{holiday_lists[0]}'"
            if employees:
                if len(employees)==1:
                    cond+=f" and name !='{employees[0]}'"
                else:
                    cond+= f" and name not in {tuple(employees)}"

            ts_employees = frappe.db.sql(f"""SELECT name from  `tabEmployee` where status = "Active" AND date_of_joining <= '{attendance_date}' and attendance_by_timesheet = 1 {cond}""",as_dict=1)
            return [i.name for i in ts_employees]
        return [i.name for i in frappe.get_all("Employee",{"status":"Active",'date_of_joining':['<=',attendance_date],'attendance_by_timesheet':1,'name':['NOT IN',employees]},['name'])]
    except:
        frappe.log_error(title = "Attendance Check Error for Timesheet",message = frappe.get_traceback())
        #Ensure that a value is returned regardless of what happens here
        return []


def create_attendance_check(attendance_date=None):
    if production_domain():
        if not attendance_date:
            attendance_date = add_days(today(), -1)
            
        absentees = frappe.get_all("Attendance", filters={
            'docstatus':1,
            'status':'Absent',
            'attendance_date':attendance_date}, 
            fields="*"
        )
        
        attendance_by_timesheet = 0

        for count, i in enumerate(absentees):
            try:

                doc = frappe.get_doc({
                    "doctype":"Attendance Check",
                    "employee":i.employee,
                    "roster_type":i.roster_type,
                    "date":i.attendance_date,
                    "attendance_by_timesheet": attendance_by_timesheet,
                    "attendance":i.name,
                    "attendance_comment":i.comment,
                    "shift_assignment":i.shift_assignment,
                    "attendance_marked":1,
                    "marked_attendance_status":i.status
                }).insert(ignore_permissions=1)
            except Exception as e:
                if not "Attendance Check already exist for" in str(e):
                    frappe.log_error(message=frappe.get_traceback(), title="Attendance Check Creation")
            if count%10==0:
                frappe.db.commit()    
        frappe.db.commit()

        # create for no shift but active shift based employees
        attendance_list = [i.employee for i in frappe.db.get_list("Attendance", {
            "attendance_date":attendance_date})]
        
        no_shifts = frappe.db.get_list("Employee", {
            "shift_working":1,
            "status":"Active",
            "name": ["NOT IN", attendance_list],
            "date_of_joining": ["<=", attendance_date]
            }
        )
        if no_shifts:
            for count, i in enumerate(no_shifts):
                try:
                    if not frappe.db.exists("Attendance", {
                        'attendance_date':attendance_date,
                        'employee':i.name}
                        ):
                        doc = frappe.get_doc({
                            "doctype":"Attendance Check",
                            "employee":i.name,
                            "roster_type":"Basic",
                            'is_unscheduled':1,
                            "date":attendance_date
                        }).insert(ignore_permissions=1)
                except Exception as e:
                    if not "Attendance Check already exist for" in str(e):
                        frappe.log_error(message=frappe.get_traceback(), title="Attendance Check Creation")
                if count%10==0:
                    frappe.db.commit()
            frappe.db.commit()
            

        no_timesheet = frappe.db.sql(f"""SELECT emp.employee FROM `tabEmployee` emp
                                    WHERE emp.attendance_by_timesheet = 1
                                    AND emp.status ='Active'
                                    AND emp.employee_name != 'Test Employee'
                                    AND emp.name NOT IN (SELECT employee from `tabTimesheet` WHERE start_date='{attendance_date}')
                                    AND '{attendance_date}' NOT IN (SELECT holiday_date from `tabHoliday` h WHERE h.parent = emp.holiday_list AND h.holiday_date = '{attendance_date}')""", as_dict=1)
        
        if no_timesheet:
            for count, i in enumerate(no_timesheet):
                try:
                    doc = frappe.get_doc({
                        "doctype":"Attendance Check",
                        "employee":i.employee,
                        "roster_type":'Basic',
                        "date":attendance_date,
                        "attendance_by_timesheet": 1,
                        "attendance_marked":0,
                        "comment":"No Timesheet Created."
                    }).insert(ignore_permissions=1)
                except Exception as e:
                    if not "Attendance Check already exist for" in str(e):
                        frappe.log_error(message=frappe.get_traceback(), title="Attendance Check Creation")
                if count%10==0:
                    frappe.db.commit()    

def approve_attendance_check():
    attendance_checks = frappe.get_all("Attendance Check", filters={
        "date":["<", today()], "workflow_state":"Pending Approval"}
    )
    for i in attendance_checks:
        doc = frappe.get_doc("Attendance Check", i.name)
        if not doc.justification:
            doc.justification = "Approved by Administrator"
        if not doc.attendance_status:
            doc.attendance_status = "Absent"
        doc.workflow_state = "Approved"
        try:
            doc.submit()
        except Exception as e:
            if str(e)=="To date can not greater than employee's relieving date":
                doc.db_set("Comment", f"Employee exited company on {frappe.db.get_value('Employee', doc.employee, 'relieving_date')}\n{doc.comment or ''}")


def mark_missing_attendance(attendance_checkin_found):
    for i in attendance_checkin_found:
        try:
            checkin_record = ""
            checkout_record = ""
            shift_assignment = ""
            att = ""
            working_hours = 0
            in_time = ''
            out_time = ''
            comment = ''
            day_off_ot = 0

            if i.attendance:
                att = frappe.get_doc("Attendance", i.attendance)
            if i.shift_assignment:
                shift_assignment = frappe.get_doc("Shift Assignment", i.shift_assignment)
                day_off_ot = frappe.get_value("Employee Schedule", {
                    'employee':i.employee,
                    'date':i.date,
                    'roster_type':i.roster_type
                }, 'day_off_ot')
            if i.checkin_record:
                checkin_record = frappe.get_doc("Employee Checkin", i.checkin_record)
            if i.checkout_record:
                checkout_record = frappe.get_doc("Employee Checkin", i.checkout_record)

            # calculate working hours
            if checkin_record and not checkout_record and shift_assignment:
                working_hours = (shift_assignment.end_datetime - checkin_record.time).total_seconds() / (60 * 60)
                in_time = checkin_record.time
                out_time = shift_assignment.end_datetime
                comment = "No checkout record found"
            elif checkin_record and checkout_record and shift_assignment:
                working_hours = (checkout_record.time - checkin_record.time).total_seconds() / (60 * 60)
                in_time = checkin_record.time
                out_time = checkout_record.time
            if att:
                # set values based on existing attendance
                if att.status=='Absent':
                    att.db_set({
                        'working_hours':working_hours,
                        'in_time':in_time,
                        'out_time':out_time,
                        'comment':comment,
                        'day_off_ot':day_off_ot,
                        'status':'Present'
                    })
            else:
                att = frappe.new_doc("Attendance")
                att.employee = i.employee
                att.employee_name = i.employee_name
                att.attendance_date = i.date
                att.status = 'Present'
                att.roster_type = i.roster_type
                att.shift_assignment = i.shift_assignment
                att.in_time = in_time
                att.out_time = out_time
                att.working_hours = working_hours
                att.comment = comment
                att.day_off_ot = day_off_ot
                att.insert(ignore_permissions=True)
                att.submit()
            frappe.db.set_value("Employee Checkin", i.checkin_record, "attendance", att.name)
            if checkout_record:
                frappe.db.set_value("Employee Checkin", i.checkout_record, "attendance", att.name)
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), 'Attendance Remark')

@frappe.whitelist()
def check_attendance_manager(email: str) -> bool:
    return frappe.db.get_value("Employee", {"user_id": email}) == frappe.db.get_single_value("ONEFM General Setting", "attendance_manager")


@frappe.whitelist()
def validate_day_off(form,convert=1):
    # Validates the existence of a shift request when the attendance status of the attendance
    doc = json.loads(form) if convert else form
    if doc.get('attendance_status') == "Day Off":
        #check if shift request for that day exists
        query = f"Select name from `tabShift Request` where docstatus = 1 and assign_day_off = 1 and  employee = '{doc.get('employee')}' and from_date <= '{doc.get('date')}'  and to_date >='{doc.get('date')}'"
        submited_result_set = frappe.db.sql(query,as_dict=1)
        if submited_result_set:
            return
        else:
            draft_query =  f"Select name,approver from `tabShift Request` where docstatus = 0 and assign_day_off = 1 and  employee = '{doc.get('employee')}' and from_date <= '{doc.get('date')}'  and to_date >='{doc.get('date')}'"
            drafts_result_set = frappe.db.sql(draft_query,as_dict=1)
            if drafts_result_set:


                doc_url = get_url_to_form('Shift Request',drafts_result_set[0].get('name'))
                approver_full_name = frappe.db.get_value("User",drafts_result_set[0].get('approver'),'full_name')
                error_template = frappe.render_template('one_fm/templates/emails/attendance_check_alert.html',context={'doctype':'Shift Request','current_user':frappe.session.user,'date':doc.date,'approver':approver_full_name,'page_link':doc_url,'employee_name':doc.employee_name})
                frappe.throw(error_template)
            else:
                #cancelled or shift request not created at all
                frappe.throw(f"""
                <p>Please note that a shift request has not been created for <b>{doc.employee_name}</b> on <b>{doc.date}</b>..</p>
                <hr>
                 To create a Shift Request <a class="btn btn-primary btn-sm" href="{frappe.utils.get_url('/app/shift-request/new-shift-request-1')}?doc_id={doc.name}&doctype={doc.doctype}" target="_blank" onclick=" ">Click Here</a>
                 """)


def assign_attendance_manager_after_48_hours():
    attendance_manager_user = fetch_attendance_manager_user_obj()
    if attendance_manager_user:
        date_time = datetime.strptime(now(), '%Y-%m-%d %H:%M:%S.%f') - timedelta(hours=48)
        attendance_check = attendance_check = frappe.db.sql("""
                                                                SELECT name
                                                                FROM `tabAttendance Check`
                                                                WHERE creation <= %s
                                                                AND docstatus = 0
                                                                AND TIME(creation) <= %s
                                                            """, (date_time, date_time.time()), as_list=1)

        if attendance_check:
            list_of_names = tuple(chain.from_iterable(attendance_check))
            if list_of_names:
                for obj in list_of_names:
                    add_assignment({
                        'doctype': "Attendance Check",
                        'name': obj,
                        'assign_to': [attendance_manager_user],
                    })


def check_for_missed(date,schedules,shift_assignments,attendance_requests,all_attendance,checks_to_create):
    all_leaves = frappe.db.sql(f"""SELECT name,employee
        FROM `tabLeave Application`
            Where '{date}' >= from_date AND '{date}' <= to_date
            AND workflow_state = 'Approved'
            AND docstatus = 1
    """,as_dict=True)
    all_shifts_query = f"""Select employee from `tabShift Request` where docstatus = 1 and
    from_date <= '{date}'  and to_date >='{date}'"""
    all_leave_employees = [i.employee for i in all_leaves]
    all_shifts = frappe.db.sql(all_shifts_query,as_dict = 1)
    shift_request_employees = [i.employee for i in all_shifts]
    schedule_employees = [i.employee for i in schedules]
    shift_assignments_employees = [i.employee for i in shift_assignments]
    attendance_requests_employees = [i.employee for i in attendance_requests]
    all_attendance_employees = [i.employee for i in all_attendance]
    merged = shift_request_employees+schedule_employees+shift_assignments_employees+\
            all_attendance_employees+attendance_requests_employees+checks_to_create+all_leave_employees
    merged_set  = set(merged) #Remove Duplicates
    merged_tuple = tuple(merged_set)
    if len(merged_tuple) == 1:
        single_employee = merged_tuple[0]
        employees_with_no_docs_query = f""" SELECT name from `tabEmployee` where status = 'Active' AND date_of_joining <= '{date}' AND shift_working = 1 and name = {single_employee}
                                        """

    #Employees with no shift,schedule,leaves etc
    else:
         employees_with_no_docs_query = f""" SELECT name from `tabEmployee` where status = 'Active' AND date_of_joining <= '{date}' and shift_working = 1 and name not in {merged_tuple}
                                            """
    result_set = frappe.db.sql(employees_with_no_docs_query,as_dict=1)
    return [i.name for i in result_set] if result_set else []


def schedule_attendance_check():
    frappe.enqueue(create_attendance_check, queue='long', timeout=7000)