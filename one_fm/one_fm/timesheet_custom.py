import frappe,calendar
import itertools
from datetime import date,timedelta,datetime
from frappe.utils import cstr
from calendar import monthrange  

def timesheet_automation(start_date=None,end_date=None,project=None):
    filters = {
		'attendance_date': ['between', (start_date, end_date)],
        'project': project,
		'status': 'Present'
	}
    logs = frappe.db.get_list('Attendance', fields="employee,working_hours,attendance_date,site,project,post_type", filters=filters, order_by="employee,attendance_date")
    for key, group in itertools.groupby(logs, key=lambda x: (x['employee'])):
        attendances = list(group)
        timesheet = frappe.new_doc("Timesheet")
        timesheet.employee = key
        for attendance in attendances:
            date = cstr(attendance.attendance_date)
            #Select the holiday list for the employee
            holiday_list = frappe.db.get_value("Employee",key,'holiday_list')
            days_of_week = ['Sunday', 'Monday', 'Tuesday','Wednesday','Thursday','Friday','Saturday']
            public_holiday = frappe.db.get_value('Holiday', {'parent':holiday_list,'holiday_date':date,'description':['not in',days_of_week]},['description'])
            #Select public holiday rate from contracts
            public_holiday_rate = 0
            if public_holiday:
                public_holiday_rate = frappe.db.get_value('Contracts',{'project':attendance.project},'public_holiday_rate')
            #Get start time from first employee checkin of that day of log type IN
            start = frappe.get_list("Employee Checkin", {"employee": key, "time": ['between', (date, date)], "log_type": "IN"}, "time", order_by="time asc")[0].time
            #Get end time from last employee checkin of that day of log type OUT
            end = frappe.get_list("Employee Checkin", {"employee": key, "time": ['between', (date, date)], "log_type": "OUT"}, "time", order_by="time desc")[0].time
            #Get the sale item of post type
            item = frappe.get_value("Post Type", attendance.post_type,'sale_item')
            #Get billing hours and unit rate from contracts and also check(it is monthly_rate or hourly_rate)
            #Note:- Add select field in contracts items [type-(hourly_rate or monthly_rate)]
            contract_item_detail = frappe.db.sql("""select ci.shift_hours,ci.type,ci.unit_rate,ci.monthly_rate
            from `tabContract Item` ci,`tabContracts` c 
            where c.name = ci.parent and ci.parenttype = 'Contracts' 
            and c.project = %s and ci.item_code = %s""",(attendance.project,item),as_dict = 1)
            billing_hours = 0
            billing_rate = 0
            billable = 0
            if contract_item_detail:
                billable = 1
                billing_hours = contract_item_detail[0].shift_hours
                if contract_item_detail[0].type == 'Monthly':
                    billing_rate = calculate_hourly_rate_of_monthly_working_days(attendance.project,item,contract_item_detail[0].monthly_rate,contract_item_detail[0].shift_hours,start_date)
                    if public_holiday_rate > 0:
                        billing_rate = public_holiday_rate * billing_rate
                if contract_item_detail[0].type == 'Hourly':
                    if public_holiday_rate > 0:
                        billing_rate = public_holiday_rate * contract_item_detail[0].unit_rate
                    else:
                        billing_rate = contract_item_detail[0].unit_rate
            timesheet.append("time_logs", {
                "activity_type": attendance.post_type,
                "from_time": start,
                "to_time": end,
                "project": attendance.project,
                "hours": attendance.working_hours,
                "billable": billable,
				"billing_hours": billing_hours,
				"billing_rate":billing_rate
            })
        timesheet.save()
        timesheet.submit()
    frappe.db.commit()	
            
    return

def calculate_hourly_rate_of_monthly_working_days(project = None,item_code = None,monthly_rate = None,shift_hour = None,first_day =None):
    if first_day != None:
        last_day = first_day.replace(day = monthrange(first_day.year,first_day.month)[1])
    days_off_week = frappe.db.sql("""select ci.sunday,ci.monday,ci.tuesday,
            ci.wednesday,ci.thursday,ci.friday,ci.saturday 
            from `tabContract Item` ci,`tabContracts` c 
            where c.name = ci.parent and ci.parenttype = 'Contracts' 
            and c.project = %s and ci.item_code = %s""",(project,item_code),as_dict = 1)[0]
    day_off_list = []
    if days_off_week["sunday"] == 1:
        day_off_list.append('Sunday')
    if days_off_week["monday"] == 1:
        day_off_list.append('Monday')
    if days_off_week["tuesday"] == 1:
        day_off_list.append('Tuesday')
    if days_off_week["wednesday"] == 1:
        day_off_list.append('Wednesday')
    if days_off_week["thursday"] == 1:
        day_off_list.append('Thursday')
    if days_off_week["friday"] == 1:
        day_off_list.append('Friday')
    if days_off_week["saturday"] == 1:
        day_off_list.append('Saturday')

    #get list of date between one month and remove offdays from list
    total_days = days_of_month(first_day,last_day)
    working_day_list = []
    for d in range(len(total_days)):
        day_of_week = calendar.day_name[total_days[d].weekday()]
        if day_of_week not in day_off_list:
            working_day_list.append(total_days[d])       
    #numbers of items in list = working days of month
    total_working_day = len(working_day_list)
    rate_per_day = monthly_rate / float(total_working_day)
    hourly_rate = float(rate_per_day / shift_hour)
    
    return hourly_rate

def days_of_month(start_date, end_date):
    date_list = []
    delta = end_date - start_date
    for i in range(delta.days + 1):
        day = start_date + timedelta(days=i)
        date_list.append(day)
    return date_list
