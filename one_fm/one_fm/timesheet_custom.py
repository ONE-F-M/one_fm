import frappe
import itertools
from frappe.utils import cstr

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
            #Get start time from first employee checkin of that day of log type IN
            start = frappe.get_list("Employee Checkin", {"employee": key, "time": ['between', (date, date)], "log_type": "IN"}, "time", order_by="time asc")[0].time
            #Get end time from last employee checkin of that day of log type OUT
            end = frappe.get_list("Employee Checkin", {"employee": key, "time": ['between', (date, date)], "log_type": "OUT"}, "time", order_by="time desc")[0].time
            #Get the sale item of post type
            item = frappe.get_value("Post Type", attendance.post_type,'sale_item')
            #Get billing hours and unit rate from contracts
            contract_item_detail = frappe.db.sql("""select ci.shift_hours,ci.unit_rate 
            from `tabContract Item` ci,`tabContracts` c 
            where c.name = ci.parent and ci.parenttype = 'Contracts' 
            and c.project = %s and ci.item_code = %s""",(attendance.project,item),as_dict = 1)
            billing_hours = 0
            billing_rate = 0
            billable = 0
            if contract_item_detail:
                billable = 1
                billing_hours = contract_item_detail[0].shift_hours
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