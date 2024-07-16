# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

from itertools import groupby
from frappe.utils import (
    get_first_day, get_last_day, getdate, add_days, now, get_first_day_of_week, get_last_day_of_week
)
from frappe.model.document import Document
from frappe.query_builder.functions import Count
from one_fm.operations.doctype.operations_shift.operations_shift import get_shift_supervisor

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
	# Get all active employees
	# Validate their offs for next 2 months
	# If discrepency, get shift supervisor grouped by and site supervisor.
	# Create record with this info
	Employee = frappe.qb.DocType('Employee')
	employees = frappe.db.sql( frappe.qb.from_(Employee).select("*").where((Employee.status=="Active") & (Employee.shift_working == 1)), as_dict=1)


	roster_day_off_data = []

	for employee in employees:
		data = validate_offs(employee)
		if len(data) > 0: roster_day_off_data = roster_day_off_data + data
	
	roster_day_off_data.sort(key=lambda x: (x["shift_supervisor"] is not None, x["shift_supervisor"]), reverse=True)

	for key, data in groupby(roster_day_off_data, key=lambda k: (k["shift_supervisor"], k["site_supervisor"])):
		# create record
		shift_supervisor = key[0]
		site_supervisor = key[1]
		roster_data = list(data)

		supervisor_name = frappe.db.get_value("Employee", shift_supervisor, "employee_name")
		site_supervisor_name = frappe.db.get_value("Employee", site_supervisor, "employee_name")
		today = getdate()
		docname = f"{today}-{supervisor_name}-{site_supervisor_name}"
		if frappe.db.exists("Roster Day Off Checker", {'name': docname}):
			delete_checker(docname)

		checker_doc = frappe.new_doc("Roster Day Off Checker")
		checker_doc.date = today
		checker_doc.supervisor = shift_supervisor
		checker_doc.supervisor_name = supervisor_name
		checker_doc.site_supervisor = site_supervisor
		checker_doc.site_supervisor_name = site_supervisor_name
		checker_doc.insert(ignore_permissions=1)

		create_checker(checker_doc.name, roster_data)

def delete_checker(docname):
	frappe.db.sql("""
		DELETE FROM `tabRoster Day Off Checker` where name=%s	
	""", (docname))

	frappe.db.sql("""
		DELETE FROM `tabRoster Day Off Detail` where parent=%s 
	""", (docname))
	frappe.db.commit() 


def validate_offs(employee):
	start_date = None
	end_date = None
	today = getdate()
	if employee.day_off_category == "Monthly":
		start_date = get_first_day(today)
		end_date = get_last_day(today)
	elif employee.day_off_category == "Weekly":
		start_date = get_first_day_of_week(today)
		end_date = get_last_day_of_week(today)
		
	EmployeeSchedule = frappe.qb.DocType("Employee Schedule")
	OperationsShift = frappe.qb.DocType("Operations Shift")

	datalist = [] # contains row wise child table data
	for i in range(2):
		supervisors_to_notify = []

		# QB conditions
		employee_name = (EmployeeSchedule.employee == employee.name) 
		employee_day_off_ot = (EmployeeSchedule.day_off_ot == 0)
		employee_schedule_date = (EmployeeSchedule.date[start_date:end_date])
		employee_availability = (EmployeeSchedule.employee_availability == "Day Off")
		join_condition = (EmployeeSchedule.shift == OperationsShift.name)
		
		# Calculate no of off days
		od = frappe.db.sql(frappe.qb.from_(EmployeeSchedule)        
			.select(Count("name").as_("off_days"))
			.where(employee_schedule_date & employee_name & employee_day_off_ot & employee_availability)
			.groupby(EmployeeSchedule.shift), 
		as_dict=1) 
		off_days = od[0].off_days if len(od) > 0 else 0 

		# Calculate no of ot days
		ot = frappe.db.sql( frappe.qb.from_(EmployeeSchedule)
			.select(Count("name").as_("ot_days"))
			.where( employee_name & employee_schedule_date & (EmployeeSchedule.day_off_ot == 1))
			.groupby(EmployeeSchedule.shift), as_dict=1) 
		ot_days = ot[0].ot_days if len(ot) > 0 else 0 



		if employee.number_of_days_off != (off_days+ot_days):
			day_off_diff = ''
			if off_days > employee.number_of_days_off and not ot_days:
				day_off_diff = f"{off_days-employee.number_of_days_off} day(s) off scheduled more, please reduce by {off_days-employee.number_of_days_off}"
			elif off_days < employee.number_of_days_off and not ot_days:
				day_off_diff = f"{employee.number_of_days_off-off_days} day(s) off scheduled less, please schedule {employee.number_of_days_off-off_days} more day off"
			elif ot_days < employee.number_of_days_off and not off_days:
				day_off_diff = f"{employee.number_of_days_off-ot_days} day(s) off scheduled less, please schedule {employee.number_of_days_off-ot_days} more day off"
			elif ot_days > employee.number_of_days_off and not off_days:
				day_off_diff = f"{ot_days-employee.number_of_days_off} day(s) off OT scheduled more, please schedule {ot_days-employee.number_of_days_off} day off OT less"
			elif (ot_days and off_days):
				day_off_diff = f"{ot_days} OT and {off_days} day(s) off scheduled, actual day off should be {employee.number_of_days_off}"

			start_date_split = str(start_date).split('-')
			end_date_split = str(end_date).split('-')
			datalist.append({
				"monthweek": f"{monthname_dict[start_date_split[1]]} {start_date_split[2]} - {monthname_dict[end_date_split[1]]} {end_date_split[2]}",
				"emp_days_off": employee.number_of_days_off,
				"day_off_schedule": off_days,
				"days_off_ot": ot_days,
				"employee": employee.name,
				"day_off_difference": day_off_diff,
				"employee_id": employee.employee_id,
				"employee_name": employee.employee_name,
				"day_off_category": employee.day_off_category,
				"number_of_days_off": employee.number_of_days_off
			})


		# If off_days > 0, get the shift and site supervisor based on their shift(s) in the start and end dates.  
		if len(datalist) > 0 and off_days > 0:
			site_shift_data = frappe.db.sql( frappe.qb.from_(EmployeeSchedule)
				.select(EmployeeSchedule.shift, OperationsShift.site)
				.left_join(OperationsShift)
		        .on(join_condition)
				.where((EmployeeSchedule.shift != "") & employee_name & employee_schedule_date & employee_day_off_ot)
				.groupby(EmployeeSchedule.shift),
			as_dict=1)

			for shift in site_shift_data:
				site_supervisor = frappe.db.get_value("Operations Site", shift.site, "account_supervisor")
				shift_supervisor = get_shift_supervisor(shift.shift)

				if len(supervisors_to_notify) == 0:
					supervisors_to_notify.append({"shift_supervisor" :shift_supervisor, "site_supervisor": site_supervisor})
				else:
					for supervisor in supervisors_to_notify:
						if supervisor["shift_supervisor"] != shift_supervisor:
							supervisors_to_notify.append({"shift_supervisor" :shift_supervisor, "site_supervisor": site_supervisor})


		# If ot_days > 0, get the shift and site supervisor based on their shift(s) in the start and end dates.  
		if len(datalist) > 0 and ot_days > 0:
			site_shift_data = frappe.db.sql( frappe.qb.from_(EmployeeSchedule)
				.select(EmployeeSchedule.shift, OperationsShift.site)
				.left_join(OperationsShift)
		        .on(join_condition)
				.where(employee_name & employee_schedule_date & (EmployeeSchedule.shift != "") & (EmployeeSchedule.day_off_ot == 1))
				.groupby(EmployeeSchedule.shift),
			as_dict=1)
			for shift in site_shift_data:
				site_supervisor = frappe.db.get_value("Operations Site", shift.site, "account_supervisor")
				shift_supervisor = get_shift_supervisor(shift.shift)

				if len(supervisors_to_notify) == 0:
					supervisors_to_notify.append({"shift_supervisor" :shift_supervisor, "site_supervisor": site_supervisor})
				else:
					for supervisor in supervisors_to_notify:
						if supervisor["shift_supervisor"] != shift_supervisor:
							supervisors_to_notify.append({"shift_supervisor" :shift_supervisor, "site_supervisor": site_supervisor})
	
		start_date = add_days(end_date, 1)
		if employee.day_off_category == "Monthly":
			end_date = get_last_day(start_date)
		elif employee.day_off_category == "Weekly":
			end_date = get_last_day_of_week(start_date)

	for supervisor in supervisors_to_notify:
		supervisor["data"] = datalist

	return supervisors_to_notify

def create_checker(parent, roster_data):
	for info in roster_data:
		creation = now()
		count = 0
		for data in info["data"]:		
			child_name = f"{parent}-{str(creation)}-{frappe.generate_hash(length=8)}"
			values = {
				"name": child_name,
				"employee": data["employee"],
				"employee_id": data["employee_id"],
				"employee_name": data["employee_name"],
				"monthweek": data["monthweek"],
				"day_off_category": data["day_off_category"],
				"number_of_days_off": data["number_of_days_off"],
				"day_off_schedule": data["day_off_schedule"],
				"days_off_ot": data["days_off_ot"],
				"day_off_difference": data["day_off_difference"],
				"owner": frappe.session.user,
				"modified_by": frappe.session.user,
				"creation": creation,
				"modified": creation,
				"parent": parent,
				"parenttype": "Roster Day Off Checker",
				"parentfield": "detail",
				"idx": count
			}
			count = count + 1


			frappe.db.sql("""
				INSERT INTO `tabRoster Day Off Detail`
				 (name, employee, employee_id, employee_name, monthweek, day_off_category, number_of_days_off, day_off_schedule, days_off_ot, 
				 day_off_difference, owner, modified_by, creation, modified, parent, parenttype, parentfield, idx)
				 VALUES 
				 (%(name)s, %(employee)s, %(employee_id)s, %(employee_name)s, %(monthweek)s, %(day_off_category)s, %(number_of_days_off)s, %(day_off_schedule)s, %(days_off_ot)s, 
				 %(day_off_difference)s, %(owner)s, %(modified_by)s, %(creation)s, %(modified)s, %(parent)s, %(parenttype)s, %(parentfield)s, %(idx)s)
			""", values=values)

		frappe.db.commit()

@frappe.whitelist()
def generate_checker():
	frappe.enqueue(check_roster_day_off, queue='long', timeout=4000)