import frappe
import itertools
from frappe.utils import cstr, flt, add_days, time_diff_in_hours
from calendar import monthrange  

def timesheet_automation(start_date=None,end_date=None,project=None):
    filters = {
		'attendance_date': ['between', (start_date, end_date)],
        'project': project,
		'status': 'Present'
	}
    logs = frappe.db.get_list('Attendance', fields="employee,working_hours,attendance_date,site,project,post_type,operations_shift", filters=filters, order_by="employee,attendance_date")   
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
            item = frappe.get_value("Post Type", attendance.post_type, 'sale_item')
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
        "activity_type": attendance.post_type,
        "from_time": start,
        "to_time": end,
        "project": attendance.project,
        "site": attendance.site,
        "operations_post": post,
        "shift": attendance.operations_shift,
        "hours": attendance.working_hours,
        "billable": billable,
        "billing_hours": billing_hours,
        "billing_rate":billing_rate
    })
    return timesheet