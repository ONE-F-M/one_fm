# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import *
import datetime

def execute(filters=None):
	if not filters: filters = {}

	if not (filters.month and filters.year):
		msgprint(_("Please select month and year"), raise_exception=1)

	columns, data =  get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	return [
		{
			"label": ("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{
			"label": ("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": ("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 120,
		},
		{
			"label": ("Work Permit Salary"),
			"fieldname": "work_permit_salary",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": ("Base Salary"),
			"fieldname": "base",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": ("Civil ID"),
			"fieldname": "one_fm_civil_id",
			"options": "Journal Entry",
			"width": 140,
		},
		{
			"label": ("Shoon File"),
			"fieldname": "shoon_file",
			"fieldtype": "Link",
			"options": "PAM File",
			"width": 120,
		},
		{
			"label": ("Bank Account"),
			"fieldname": "bank_ac_no",
			"fieldtype": "Link",
			"options": "Bank Account",
			"width": 120,
		},
		{
			"label": ("Start Date"),
			"fieldname": "start_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": ("End Date"),
			"fieldname": "end_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": ("No. Of Days(Current Month)"),
			"fieldname": "days_in_period",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": ("Holiday List"),
			"fieldname": "holiday_list",
			"fieldtype": "Link",
			"options": "Holiday List",
			"width": 120,
		},
		{
			"label": ("No. of Public holiday"),
			"fieldname": "number_of_public_holiday",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": ("Shift/Non-Shift Worker"),
			"fieldname": "shift_work_type",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": ("Attendance By TimeSheet"),
			"fieldname": "att_by_timesheet",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": ("Auto Attendance"),
			"fieldname": "auto_attendance",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": ("Day off Type"),
			"fieldname": "day_off_category",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": ("Days Off(Employee Docs)"),
			"fieldname": "number_of_days_off",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": ("Theoretical Days Off"),
			"fieldname": "theoretical_days_off",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": ("Theoretical Working Days"),
			"fieldname": "theoretical_working_days",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": ("Scheduled Working Days"),
			"fieldname": "working_days",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": ("Days Off (Roster)"),
			"fieldname": "do_roster",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("OT Days Off (Roster)"),
			"fieldname": "do_ot",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("Present Days (Attendance)"),
			"fieldname": "present_days",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("Days Off (Attendance)"),
			"fieldname": "do_att",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("Public Holidays(Attendance)"),
			"fieldname": "att_public_holidays",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": ("Present OT Days (Attendence)"),
			"fieldname": "present_days_ot",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("Sick Leave"),
			"fieldname": "sl",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("Annual Leave"),
			"fieldname": "al",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("Other Leave"),
			"fieldname": "ol",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("No. of Absent"),
			"fieldname": "ab",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("Payment Days(Basic)"),
			"fieldname": "pd",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("Payment Days(OT)"),
			"fieldname": "pdot",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("Total"),
			"fieldname": "total",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
	]

def get_data(filters):
	data = []
	if not filters:
		return

	report_date = str(filters["year"]) + "-" + str(filters["month"]) + "-1"

	first_day_of_month = str(get_first_day(report_date))
	last_day_of_month = str(get_last_day(report_date))
	query = frappe.db.sql(f"""
		SELECT DISTINCT e.name as employee, e.employee_name, e.project, e.work_permit_salary, e.one_fm_civil_id, e.bank_ac_no,
		e.day_off_category, e.shift_working as shift_work_type, e.attendance_by_timesheet as att_by_timesheet, e.auto_attendance, 
		e.holiday_list, e.number_of_days_off , e.pam_file_number as shoon_file, ssa.base, pe.start_date, pe.end_date
		FROM `tabEmployee` e JOIN `tabSalary Structure Assignment` ssa ON e.name=ssa.employee
			JOIN `tabPayroll Employee Detail` ped ON e.name=ped.employee
			JOIN `tabPayroll Entry` pe ON pe.name=ped.parent
			JOIN `tabAttendance` at ON at.employee=e.name
		WHERE ssa.docstatus=1 AND pe.end_date BETWEEN '{first_day_of_month}' and '{last_day_of_month}'
			AND at.attendance_date BETWEEN pe.start_date AND pe.end_date
			AND at.roster_type='Basic'
			AND pe.salary_slips_created=1
		GROUP BY e.name
		ORDER BY e.name ASC
	""", as_dict=1)

	# payroll_cycle = get_payroll_cycle(filters)
	employee_list = get_employee_list(query)

	attendance_by_employee = get_attendance(employee_list)

	for i in query:
		i.days_in_period = (i.end_date - i.start_date).days + 1
		att_project = attendance_by_employee.get(i.employee)
		if att_project:
			i.do_ot = att_project['do_ot']
			i.present_days = att_project['present_days']
			i.present_days_ot = att_project['present_days_ot']
			i.do_att = att_project['do_att']
			i.sl = att_project['sl']
			i.al = att_project['al']
			i.ol = att_project['ol']
			i.ab = att_project['ab']
			i.att_public_holidays = att_project['h']
			i.number_of_public_holiday = att_project['ph']
			if i.shift_work_type == 1:
				i.shift_work_type = "Shift Worker"
				i.do_roster = att_project['do_roster_se']
				i.working_days = att_project['working_days']
			else:
				i.shift_work_type = "Non-Shift Worker"
				i.do_roster = att_project['do_roster_nse']
				i.working_days = i.days_in_period - i.do_roster - i.att_public_holidays
			
		i.theoretical_days_off = theoretical_days_off(i.day_off_category, i.number_of_days_off, i.start_date, i.end_date)
		i.theoretical_working_days = i.days_in_period - i.theoretical_days_off
		i.pd = i.present_days + i.do_att + i.sl + i.al + i.ol + i.att_public_holidays
		i.pdot = i.present_days_ot + i.do_ot
		i.total = i.present_days + i.do_att + i.sl + i.al + i.ol + i.ab + i.att_public_holidays

	if not query:
		frappe.msgprint(("No Payroll Submitted or Salary Slip Created from the Payroll Entry this month!"), alert=True, indicator="Blue")

	return query

def get_employee_list(query):
	employee = {}
	for q in query:
		employee[q.employee] = {}
		employee[q.employee]['start_date'] = q.start_date
		employee[q.employee]['end_date'] = q.end_date
	return employee


# def get_payroll_cycle(filters):
# 	settings = frappe.get_doc("HR and Payroll Additional Settings")
# 	default_date = settings.payroll_date


# 	end_date = datetime.date(int(filters["year"]), int(filters["month"]), int(default_date))
# 	payroll_cycle = {
# 		'Other': {
# 			'start_date': add_days(add_months(datetime.date(int(filters["year"]),int(filters["month"]), int(default_date)), -1), -1),
# 			'end_date': datetime.date(int(filters["year"]), int(filters["month"]), int(default_date))

# 			}
# 		}

# 	for row in settings.project_payroll_cycle:
# 		if row.payroll_start_day == 'Month Start':
# 			row.payroll_start_day = 1
# 		payroll_cycle[row.project] = {

# 			'start_date':add_days(add_months(datetime.date(int(filters["year"]), int(filters["month"]), int(row.payroll_start_day)), -1), -1),
# 			'end_date':datetime.date(int(filters["year"]), int(filters["month"]), int(row.payroll_start_day)),
# 		}

# 	return payroll_cycle

def theoretical_days_off(day_off_category, number_of_days_off, start_date, end_date):
	if day_off_category == "Monthly":
		return number_of_days_off
	else:
		no_of_days = (end_date - start_date).days 
		weeks = no_of_days // 7
		return weeks * number_of_days_off

def get_attendance(employee_list):
	attendance_dict = {}
	for employee in employee_list:
		start_time = time.time()
		start_date = employee_list[employee]['start_date']
		end_date = employee_list[employee]['end_date']
		attendance_dict[employee]={'working_days':0, 'do_roster_se':0, 'do_ot': 0, 'do_roster_nse':0, 'present_days': 0, 'present_days_ot':0, 'sl':0, 'al':0, 'ab':0, 'ol':0, 'do_att':0, 'h':0}
		
		working_days = frappe.db.sql(f"""
			SELECT COUNT(*) as working_days FROM `tabEmployee Schedule` es
			WHERE es.employee = '{employee}'
			AND es.date BETWEEN '{start_date}' AND '{end_date}'
			AND es.employee_availability = 'Working'
			AND es.roster_type='Basic'
		""", as_dict=1)

		day_off = frappe.db.sql(f"""SELECT
										COUNT(CASE WHEN es.day_off_ot = 0 THEN 1 END) AS do,
										COUNT(CASE WHEN es.day_off_ot = 1 THEN 1 END) AS do_ot
									FROM `tabEmployee Schedule` es  
									WHERE  es.employee = '{employee}'
									AND es.employee_availability = 'Day Off'
									AND es.date BETWEEN '{start_date}' AND '{end_date}'
									AND es.roster_type='Basic'
									GROUP BY es.employee
								""", as_dict=1)
		
		do_roster_nse = frappe.db.sql(f"""Select count(*) as do from `tabHoliday` h JOIN `tabEmployee` e ON e.holiday_list=h.parent
												WHERE e.name = '{employee}'
												AND h.holiday_date BETWEEN '{start_date}' AND '{end_date}' 
	 											AND h.weekly_off = 1""", as_dict=1)
		
		ph = frappe.db.sql(f"""Select count(*) as holiday from `tabHoliday` h JOIN `tabEmployee` e ON e.holiday_list=h.parent
												WHERE e.name = '{employee}'
												AND h.holiday_date BETWEEN '{start_date}' AND '{end_date}' 
	 											AND h.weekly_off = 0""", as_dict=1)

		attendance = frappe.db.sql(f"""SELECT 
									COUNT(CASE WHEN at.status IN ("Present", "Work From Home") THEN 1 END) AS present_days,
									COUNT(CASE WHEN at.status = "Absent" THEN 1 END) AS absent,
									COUNT(CASE WHEN at.status = "Holiday" THEN 1 END) AS holiday,
									COUNT(CASE WHEN at.status = "Day Off" THEN 1 END) AS do
									FROM `tabAttendance` at 
									WHERE  at.employee = '{employee}'
									AND at.attendance_date BETWEEN '{start_date}' AND '{end_date}'
									AND at.roster_type='Basic'
									GROUP BY at.employee
								""", as_dict=1)
		present_list_ot = frappe.db.sql(f"""
			SELECT COUNT(*) as present_days_ot FROM `tabAttendance` at
			WHERE at.employee = '{employee}'
			AND at.attendance_date BETWEEN '{start_date}' AND '{end_date}'
			AND at.status IN ("Present", "Work From Home")
			AND at.roster_type='Over-Time'
			GROUP BY at.employee
		""", as_dict=1)

		attendance_leave_details = frappe.db.sql(f"""
			SELECT at.leave_type, COUNT(at.leave_type) AS leave_count FROM `tabAttendance` at
				WHERE at.employee = '{employee}'
				AND at.status = "On Leave"
				AND at.attendance_date BETWEEN '{start_date}' AND '{end_date}'
				Group by at.leave_type;
			""", as_dict=1)


		attendance_dict[employee]['working_days'] = working_days[0].working_days if working_days else 0
		attendance_dict[employee]['do_roster_se'] = day_off[0].do if day_off else 0
		attendance_dict[employee]['do_ot'] = day_off[0].do_ot if day_off else 0
		attendance_dict[employee]['do_roster_nse'] = do_roster_nse[0].do if do_roster_nse else 0
		attendance_dict[employee]['do_att'] = attendance[0].do if attendance else 0
		attendance_dict[employee]['present_days'] = attendance[0].present_days if attendance else 0
		attendance_dict[employee]['present_days_ot']  = present_list_ot[0].present_days_ot if present_list_ot else 0
		attendance_dict[employee]['ab'] = attendance[0].absent if attendance else 0
		attendance_dict[employee]['h'] = attendance[0].holiday if attendance else 0	
		attendance_dict[employee]['ph'] = ph[0].holiday if attendance else 0	
		for row in attendance_leave_details:
			if row.leave_type == 'Sick Leave':
				attendance_dict[employee]['sl'] = row.leave_count
			elif row.leave_type == 'Annual Leave':
				attendance_dict[employee]['al'] = row.leave_count
			else:
				attendance_dict[employee]['ol'] = row.leave_count
	return attendance_dict

@frappe.whitelist()
def get_attendance_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(attendance_date) from tabAttendance ORDER BY YEAR(attendance_date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)
