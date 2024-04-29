# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

from datetime import datetime
import frappe, random
from frappe.utils import (
    get_first_day, get_last_day, getdate, add_days, add_months, now
)
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
			create_record(supervisor=k, detail=v)
			# frappe.enqueue(create_record, supervisor=k, date=datetime.today().date(), detail=v)

def create_record(supervisor, detail):
	creation = now()
	owner = frappe.session.user
	date = str(getdate())
	employee_list = frappe.db.get_list("Employee", 
		fields=['name', 'employee_name', 'day_off_category', 'number_of_days_off'])
	employee_dict = {}
	for i in employee_list:
		employee_dict[i.name] = i
	supervisor = employee_dict[supervisor]
	# check if document exists
	if frappe.db.exists("Roster Day Off Checker", {'name':f"{date}-{supervisor.employee_name}"}):
		frappe.get_doc("Roster Day Off Checker", f"{date}-{supervisor.employee_name}").delete()
		frappe.db.commit()

	doc = frappe.get_doc({
		'doctype': 'Roster Day Off Checker',
		'supervisor': supervisor.name,
		'supervisor_name':supervisor.employee_name,
		'date': date,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	query = query = """
		INSERT INTO `tabRoster Day Off Detail` (`name`, `employee`, `employee_name`, `monthweek`, 
		`day_off_category`, `number_of_days_off`, `day_off_schedule`, `days_off_ot`, `day_off_difference`, 
		`owner`, `modified_by`, `creation`, `modified`, `parent`, `parenttype`, `parentfield`, `idx`)
		VALUES 
	"""
	idx = 1
	for i in detail:
		emp = employee_dict[i['employee']]
		child_name = f"{doc.name}-{emp.name}-{str(creation)}-{random.random()}"
		query += f"""
			("{child_name}", "{emp.name}", "{emp.employee_name}", "{i['monthweek']}", 
			"{emp.day_off_category}", {emp.number_of_days_off}, "{i['day_off_schedule']}", '{i['days_off_ot']}', 
			"{i['day_off_difference']}", "{owner}", "{owner}", "{creation}", "{creation}", "{doc.name}", "{doc.doctype}", 
			"detail", {idx}
			),"""
		idx += 1
	query = query[:-1]
	frappe.db.sql(query, values=[], as_dict=1)
	frappe.db.commit()

def validate_offs(emp, project_cycle, supervisor):
	"""
	Validate if the employee is has exceeded weekly or monthly off schedule.
	:return:
	"""
	datalist = []

	if emp.day_off_category == 'Monthly':
		start_date = get_first_day(getdate())
		end_date = get_last_day(getdate())
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
					day_off_diff = f"{ot_days} OT and {off_days} day(s) off scheduled, actual day off should be {emp.number_of_days_off}"

				start_date_split = str(start_date).split('-')
				end_date_split = str(end_date).split('-')
				datalist.append({
					'monthweek': f"{monthname_dict[start_date_split[1]]} {start_date_split[2]} - {monthname_dict[end_date_split[1]]} {end_date_split[2]}",
					'emp_days_off': emp.number_of_days_off,
					'day_off_schedule': off_days,
					'days_off_ot': ot_days,
					'employee': emp.name,
					'day_off_difference': day_off_diff
				})
			start_date = add_days(end_date, 1)
			end_date = get_last_day(start_date)

	elif emp.day_off_category == 'Weekly':
		start_date = get_first_day(getdate())
		end_date = add_days(start_date, 6)
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

				start_date_split = str(start_date).split('-')
				end_date_split = str(end_date).split('-')
				datalist.append({
					'monthweek': f"{monthname_dict[start_date_split[1]]} {start_date_split[2]} - {monthname_dict[end_date_split[1]]} {end_date_split[2]}",
					'emp_days_off': emp.number_of_days_off,
					'day_off_schedule': off_days,
					'days_off_ot': ot_days,
					'employee': emp.name,
					'day_off_difference': day_off_diff
				})
				
			start_date = add_days(end_date, 1)
			end_date = add_days(start_date, 6)
	return frappe._dict({'supervisor': supervisor, 'data': datalist})


@frappe.whitelist()
def generate_checker():
	frappe.enqueue(check_roster_day_off, queue='long', timeout=4000)
	return True