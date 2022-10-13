# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

from datetime import datetime
import frappe
from frappe.utils import getdate, add_days, add_months
from frappe.model.document import Document
from one_fm.utils import get_payroll_cycle


monthname_dict = {
	'01': 'Jan',
	'02': 'Feb',
	'03': 'Mar',
	'04': 'Apr',
	'05': 'May',
	'06': 'Jun',
	'07': 'Jul',
	'08': 'Aug',
	'09': 'Sep',
	'10': 'Oct',
	'11': 'Nov',
	'12': 'Dec',
}


class RosterDayOffChecker(Document):
	pass


def check_roster_day_off():
	payroll_cycle = get_payroll_cycle()
	employees = frappe.db.sql("""
		SELECT * FROM `tabEmployee` 
			WHERE
		status='Active' AND shift_working=1 
	""", as_dict=True)

	# get project supervisors
	project_supervisors = frappe.db.sql("""
		SELECT supervisor, project FROM `tabOperations Shift` 
		GROUP BY project
	""", as_dict=1)

	project_supervisor_dict = {}
	for ps in project_supervisors:
		if not project_supervisor_dict.get(ps.supervisor):
			project_supervisor_dict[ps.project] = ps.supervisor

	# start running
	supervisor_dict = {}
	for emp in employees:
		if emp.project:
			res = validate_offs(emp, payroll_cycle.get(emp.project), project_supervisor_dict.get(emp.project))
			if supervisor_dict.get(res.supervisor):
				supervisor_dict[res.supervisor] += res.data
			else:
				supervisor_dict[res.supervisor] = res.data

	# create data
	for k, v in supervisor_dict.items():
		if k and v:
			frappe.get_doc({
				'doctype': 'Roster Day Off Checker',
				'supervisor': k,
				'date': datetime.today().date(),
				'detail': v
			}).insert(ignore_permissions=True)

def validate_offs(emp, project_cycle, supervisor):
	"""
	Validate if the employee is has exceeded weekly or monthly off schedule.
	:return:
	"""
	datalist = []

	if emp.day_off_category == 'Monthly':
		start_date = project_cycle['start_date']
		end_date = project_cycle['end_date']
		for i in range(2):
			off_days = frappe.db.sql("""
				SELECT COUNT(name) as cnt FROM `tabEmployee Schedule`
					WHERE
				employee='{emp.name}' AND employee_availability='Day Off' AND day_off_ot=0
				AND date BETWEEN '{start_date}' AND '{end_date}'
			""".format(emp=emp, start_date=start_date, end_date=end_date), as_dict=True)[0].cnt
			ot_days = frappe.db.sql("""
				SELECT COUNT(name) as cnt FROM `tabEmployee Schedule`
					WHERE
				employee='{emp.name}' AND day_off_ot=1
				AND date BETWEEN '{start_date}' AND '{end_date}'
			""".format(emp=emp, start_date=start_date, end_date=end_date), as_dict=True)[0].cnt
			if emp.number_of_days_off != (off_days+ot_days):
				day_off_diff = ''
				if off_days > emp.number_of_days_off and not ot_days:
					day_off_diff = f"{off_days-emp.number_of_days_off} day(s) off scheduled more, please reduce by {off_days-emp.number_of_days_off}"
				elif off_days < emp.number_of_days_off and not ot_days:
					day_off_diff = f"{emp.number_of_days_off-off_days} day(s) off scheduled less, please schedule {emp.number_of_days_off-off_days} more day off"
				elif ot_days < emp.number_of_days_off and not off_days:
					day_off_diff = f"{emp.number_of_days_off-ot_days} day(s) off scheduled less, please schedule {emp.number_of_days_off-ot_days} more day off"
				elif ot_days > emp.number_of_days_off and not off_days:
					day_off_diff = f"{ot_days-emp.number_of_days_off} day(s) off OT scheduled more, please schedule {ot_days-emp.number_of_days_off} day off OT less"
				elif (ot_days and off_days):
					day_off_diff = f"{ot_days} OT and {emp.number_of_days_off} day(s) off scheduled, actual day off should be {emp.number_of_days_off}"

				start_date_split = start_date.split('-')
				end_date_split = end_date.split('-')
				datalist.append({
					'monthweek': f"{monthname_dict[start_date_split[1]]} {start_date_split[2]} - {monthname_dict[end_date_split[1]]} {end_date_split[2]}",
					'emp_days_off': emp.number_of_days_off,
					'day_off_schedule': off_days,
					'days_off_ot': ot_days,
					'employee': emp.name,
					'day_off_difference': day_off_diff
				})
			start_date = add_days(end_date, 1)
			end_date = add_months(start_date, 1)

	elif emp.day_off_category == 'Weekly':
		start_date = project_cycle['start_date']
		end_date = add_days(start_date, 7)
		for i in range(7):
			off_days = frappe.db.sql("""
				SELECT COUNT(name) as cnt FROM `tabEmployee Schedule`
					WHERE
				employee='{emp.name}' AND employee_availability='Day Off' AND day_off_ot=0
				AND date BETWEEN '{start_date}' AND '{end_date}'
			""".format(emp=emp, start_date=start_date, end_date=end_date), as_dict=True)[0].cnt
			ot_days = frappe.db.sql("""
				SELECT COUNT(name) as cnt FROM `tabEmployee Schedule`
					WHERE
				employee='{emp.name}' AND day_off_ot=1
				AND date BETWEEN '{start_date}' AND '{end_date}'
			""".format(emp=emp, start_date=start_date, end_date=end_date), as_dict=True)[0].cnt
			if emp.number_of_days_off != (off_days+ot_days):
				day_off_diff = ''
				if off_days > emp.number_of_days_off and not ot_days:
					day_off_diff = f"{off_days-emp.number_of_days_off} day(s) off scheduled more, please reduce by {off_days-emp.number_of_days_off}"
				elif off_days < emp.number_of_days_off and not ot_days:
					day_off_diff = f"{emp.number_of_days_off-off_days} day(s) off scheduled less, please schedule {emp.number_of_days_off-off_days} more day off"
				elif ot_days < emp.number_of_days_off and not off_days:
					day_off_diff = f"{emp.number_of_days_off-ot_days} day(s) off scheduled less, please schedule {emp.number_of_days_off-ot_days} more day off"
				elif ot_days > emp.number_of_days_off and not off_days:
					day_off_diff = f"{ot_days-emp.number_of_days_off} day(s) off OT scheduled more, please schedule {ot_days-emp.number_of_days_off} day off OT less"
				elif (ot_days and off_days):
					day_off_diff = f"{ot_days} OT and {emp.number_of_days_off} day(s) off scheduled, actual day off should be {emp.number_of_days_off}"

				start_date_split = start_date.split('-')
				end_date_split = end_date.split('-')
				datalist.append({
					'monthweek': f"{monthname_dict[start_date_split[1]]} {start_date_split[2]} - {monthname_dict[end_date_split[1]]} {end_date_split[2]}",
					'emp_days_off': emp.number_of_days_off,
					'day_off_schedule': off_days,
					'days_off_ot': ot_days,
					'employee': emp.name,
					'day_off_difference': day_off_diff
				})

			start_date = add_days(end_date, 1)
			end_date = add_days(start_date, 7)
	return frappe._dict({'supervisor': supervisor, 'data': datalist})


