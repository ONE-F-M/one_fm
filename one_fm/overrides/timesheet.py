import frappe
import itertools
from frappe.utils import cstr, flt, add_days, time_diff_in_hours, getdate
from calendar import monthrange
from one_fm.api.utils import get_reports_to_employee_name
from hrms.overrides.employee_timesheet import *
from frappe import _
from one_fm.processor import sendemail
from one_fm.utils import send_workflow_action_email


class TimesheetOveride(Timesheet):
    def validate(self):
        self.set_status()
        self.validate_dates()
        self.validate_time_logs()
        self.update_cost()
        self.calculate_total_amounts()
        self.calculate_percentage_billed()
        self.set_dates()
        self.set_approver()
        self.validate_start_date()

    def validate_start_date(self):
        if getdate(self.start_date) > getdate():
            frappe.throw("Please note that timesheets cannot be created for a date in the future")
            
    def set_approver(self):
        if self.attendance_by_timesheet:
            self.approver = fetch_approver(self.employee)

    def before_submit(self):
        current_date = getdate()
        allowed_role = "HR Manager"
        if allowed_role not in frappe.get_roles(frappe.session.user):
            if self.start_date != current_date or self.end_date != current_date:
                frappe.throw("Not allowed to submit doc for previous date")

    def on_update(self):
        if self.workflow_state == 'Open':
            send_workflow_action_email(self, [self.approver])
            message = "The timesheet {0} of {1}, Open for your Approval".format(self.name, self.employee_name)
            create_notification_log("Pending - Workflow Action on Timesheet", message, [self.approver], self)

    def on_submit(self):
        self.validate_mandatory_fields()
        self.update_task_and_project()
        if self.workflow_state == "Approved":
            self.check_approver()
            self.create_attendance()
        elif self.workflow_state == "Rejected":
            self.check_approver()
            self.notify_the_employee()

    def notify_the_employee(self):
        timesheet_url = '<a href="{0}">{1}</a>'.format(frappe.utils.get_link_to_form("Timesheet", self.name), self.name)
        message = "The Timesheet {0}, is {1} by {2}".format(timesheet_url, self.workflow_state, frappe.get_value('User', frappe.session.user, 'full_name'))
        user = frappe.get_value('Employee', self.employee, 'user_id')
        if user:
            subject = 'Timesheet {0} - {1}'.format(timesheet_url, self.workflow_state)
            sendemail(
                recipients=[user],
                subject=subject,
                message=message,
                reference_doctype='self.doctype',
                reference_name=self.name
            )
            create_notification_log(subject, message, [user], self)

    def on_cancel(self):
        self.cancel_the_attendance()

    def cancel_the_attendance(self):
        attendance = frappe.db.exists('Attendance', {'timesheet': self.name, 'docstatus': ['<', 2]})
        if attendance:
            frappe.get_doc("Attendance", attendance).cancel()

    def create_attendance(self):
        attendance_by_timesheet = frappe.db.get_value('Employee', self.employee, 'attendance_by_timesheet')
        if not attendance_by_timesheet:
            return
        attendance_exists = frappe.db.exists('Attendance',
            {'attendance_date': self.start_date, 'employee': self.employee, 'docstatus': ['<', 2]})
        if attendance_exists:
            att = frappe.get_doc("Attendance", attendance_exists)
            if att.status == 'Absent':
                att.db_set("status", "Present")
                att.db_set("timesheet", self.name)
                att.db_set("working_hours", self.total_hours, notify=True)
                att.db_set("reference_doctype", "Timesheet")
                att.db_set("reference_docname", self.name)
        else:
            att = frappe.new_doc("Attendance")
            att.employee = self.employee
            att.employee_name = self.employee_name
            att.attendance_date = self.start_date
            att.company = self.company
            att.status = "Present"
            att.working_hours = self.total_hours
            att.reference_doctype = "Timesheet"
            att.reference_docname = self.name
            att.insert(ignore_permissions=True)
            att.submit()
    
    def check_approver(self):
        if frappe.session.user != self.approver:
            frappe.throw(_("Only Approver can Approve/Reject the timesheet"))

def timesheet_automation(start_date=None,end_date=None,project=None):
    filters = {
		'attendance_date': ['between', (start_date, end_date)],
        'project': project,
		'status': 'Present'
	}
    logs = frappe.db.get_list('Attendance', fields="employee,working_hours,attendance_date,site,project,operations_role,operations_shift", filters=filters, order_by="employee,attendance_date")
    for key, group in itertools.groupby(logs, key=lambda x: (x['employee'])):
        attendances = list(group)
        timesheet = frappe.new_doc("Timesheet")
        timesheet.employee = key
        for attendance in attendances:
            billing_hours, billing_rate, billable, public_holiday_rate_multiplier = 0, 0, 0, 0
            date = cstr(attendance.attendance_date)
            holiday_list = frappe.db.get_value('Contracts', {'project': attendance.project}, 'holiday_list')
            post = get_post(key, attendance.operations_shift, date)
            public_holiday = frappe.db.get_value('Holiday', {'parent': holiday_list, 'holiday_date': date}, ['description'])
            if public_holiday:
                public_holiday_rate_multiplier = frappe.db.get_value('Contracts', {'project': attendance.project}, 'public_holiday_rate')
            #Get start time from first employee checkin of that day of log type IN
            start = frappe.get_list("Employee Checkin", {"employee": key, "time": ['between', (date, date)], "log_type": "IN"}, "time", order_by="time asc")[0].time
            #Get end time from last employee checkin of that day of log type OUT
            end = frappe.get_list("Employee Checkin", {"employee": key, "time": ['between', (date, date)], "log_type": "OUT"}, "time", order_by="time desc")[0].time
            #Get the sale item of post type
            item = frappe.get_value("Operations Role", attendance.operations_role, 'sale_item')
            gender = frappe.get_value("Operations Post", post, 'gender')
            shift_hours = frappe.get_value("Operations Shift", attendance.operations_shift, ['duration'])
            #pass gender, shift hour, dayoffs, uom
            contract_item_detail = get_contrat_item_detail(attendance.project, item, gender, shift_hours)
            if contract_item_detail:
                billable = 1
                #biiling hours should be set based on billing type in contracts
                billing_hours = set_billing_hours(attendance.project, start, end, shift_hours)
                if contract_item_detail[0].uom == 'Month':
                    billing_rate = calculate_hourly_rate(attendance.project, item, contract_item_detail[0].rate, shift_hours, start_date)
                    if public_holiday_rate_multiplier > 0:
                        billing_rate = public_holiday_rate_multiplier * billing_rate
                if contract_item_detail[0].uom == 'Hours':
                    billing_rate = contract_item_detail[0].rate
                    if public_holiday_rate_multiplier > 0:
                        billing_rate = public_holiday_rate_multiplier * contract_item_detail[0].rate
            timesheet = add_time_log(timesheet, attendance, start, end, post, billable, billing_hours, billing_rate)
        timesheet.save()
        timesheet.submit()
    frappe.db.commit()

def days_of_month(start_date, end_date):
    date_list = []
    delta = end_date - start_date
    for i in range(delta.days + 1):
        day = add_days(start_date, i)
        date_list.append(day)
    return date_list

def calculate_hourly_rate(project = None,item_code = None,monthly_rate = None,shift_hour = None,first_day =None):
    if first_day != None:
        last_day = first_day.replace(day = monthrange(first_day.year, first_day.month)[1])
    #pass shift hours, gender, uom, days_off
    days_off_week = frappe.db.sql("""
            SELECT
                days_off
            FROM `tabContract Item` ci, `tabContracts` c
            WHERE c.name = ci.parent and ci.parenttype = 'Contracts'
                and c.project = %s and ci.item_code = %s
    """, (project, item_code), as_dict=0)[0][0]
    total_days = days_of_month(first_day, last_day)
    days_off_month = flt(days_off_week) * 4
    total_working_day = len(total_days) - days_off_month
    rate_per_day = monthly_rate / flt(total_working_day)
    hourly_rate = flt(rate_per_day / shift_hour)
    return hourly_rate

def get_post(employee, operations_shift, date):
    return frappe.db.sql("""
            SELECT
                e.post
            FROM `tabPost Allocation Plan` p,`tabPost Allocation Employee Assignment` e
            WHERE p.name = e.parent and e.parenttype = 'Post Allocation Plan'
                and e.employee = %s and p.operations_shift = %s
                and p.date = %s
            """, (employee, operations_shift, date), as_dict=1)[0].post

#pass shift_hours, gender, uom, day_offs if needed
def get_contrat_item_detail(project, item, gender, shift_hours):
    return frappe.db.sql("""
            SELECT
                ci.name, ci.item_code, ci.head_count as qty,
                ci.shift_hours, ci.uom, ci.rate,
                ci.gender, ci.unit_rate, ci.type,
                ci.monthly_rate
            FROM `tabContract Item` ci, `tabContracts` c
            WHERE c.name = ci.parent and ci.parenttype = 'Contracts'
                and c.project = %s and ci.item_code = %s
                and ci.gender = %s and ci.shift_hours = %s
            """, (project, item, gender, shift_hours), as_dict = 1)

def set_billing_hours(project, from_time, to_time, shift_hour):
    billing_type = frappe.get_value('Contracts',{'project': project}, 'billing_type')
    if billing_type == 'Actual Hours':
        billing_hours = time_diff_in_hours(to_time, from_time)
    else:
        billing_hours = shift_hour
    return billing_hours

def add_time_log(timesheet, attendance, start, end, post, billable, billing_hours, billing_rate):
    timesheet.append("time_logs", {
        "activity_type": attendance.operations_role,
        "from_time": start,
        "to_time": end,
        "project": attendance.project,
        "site": attendance.site,
        "operations_role": post,
        "shift": attendance.operations_shift,
        "hours": attendance.working_hours,
        "billable": billable,
        "billing_hours": billing_hours,
        "billing_rate":billing_rate
    })
    return timesheet

@frappe.whitelist()
def fetch_approver(employee):
    if employee:
        approver = get_reports_to_employee_name(employee)
        if approver:
            return frappe.get_value("Employee", approver, ["user_id"])
        else:
            frappe.throw("No approver found for {employee}".format(employee=employee))

def validate_timesheet_count(doc, event):
    if doc.workflow_state == "Approved":
        employee_shift = frappe.get_value("Employee", doc.employee,["default_shift"])
        expected_working_duration = frappe.get_value("Shift Type", employee_shift,["duration"])

        if expected_working_duration < doc.total_hours:
            frappe.msgprint("Kindly, note that {employee} has timed over".format(employee=employee))

def validate_date(doc, method):
    current_date = getdate()
    allowed_role = "HR Manager"
    if allowed_role not in frappe.get_roles(frappe.session.user):
        if doc.start_date != current_date or doc.end_date != current_date:
            frappe.throw("Not allowed to submit doc for previous date")

def create_notification_log(subject, message, for_users, reference_doc):
	for user in for_users:
		doc = frappe.new_doc('Notification Log')
		doc.subject = subject
		doc.email_content = message
		doc.for_user = user
		doc.document_type = reference_doc.doctype
		doc.document_name = reference_doc.name
		doc.from_user = reference_doc.modified_by
		# If notification log type is Alert then it will not send email for the log
		doc.type = 'Alert'
		doc.insert(ignore_permissions=True)
