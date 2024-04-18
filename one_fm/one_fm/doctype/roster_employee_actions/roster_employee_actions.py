# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate, get_link_to_form
from one_fm.processor import sendemail
from frappe.permissions import get_doctype_roles
import datetime
from datetime import timedelta
from collections import OrderedDict

class RosterEmployeeActions(Document):
	def autoname(self):
		self.name = str(self.start_date) + "|" + str(self.end_date) + "|" + self.action_type  + "|" + self.supervisor

	def after_insert(self):
		# send notification to supervisor
		user_id = frappe.db.get_value("Employee", self.supervisor, ["user_id"])
		if user_id:
			link = get_link_to_form(self.doctype, self.name)
			subject = _("New Action to {action_type}.".format(action_type=self.action_type))
			message = _("""
				You have been issued a Roster Employee Action.<br>
				Please review the employees assigned to you, take necessary actions and update the status.<br>
				Link: {link}""".format(link=link))
			sendemail([user_id], subject=subject, message=message, reference_doctype=self.doctype, reference_name=self.name)

@frappe.whitelist()
def get_permission_query_conditions(user):
	"""
		Method used to set the permission to get the list of docs (Example: list view query)
		Called from the permission_query_conditions of hooks for the DocType Roster Employee Actions
		args:
			user: name of User object or current user
		return conditions query
	"""
	if not user: user = frappe.session.user

	if user == "Administrator":
		return ""

	# Fetch all the roles associated with the current user
	user_roles = frappe.get_roles(user)

	if "System Manager" in user_roles:
		return ""
	if "Operation Admin" in user_roles:
		return ""

	# Get roles allowed to Roster Employee Actions doctype
	doctype_roles = get_doctype_roles('Roster Employee Actions')
	# If doctype roles is in user roles, then user permitted
	role_exist = [role in doctype_roles for role in user_roles]

	if role_exist and len(role_exist) > 0 and True in role_exist:
		employee = frappe.get_value("Employee", {"user_id": user}, ["name"])
		if "Shift Supervisor" in user_roles or "Site Supervisor" in user_roles:
			return '(`tabRoster Employee Actions`.`supervisor`="{employee}" or `tabRoster Employee Actions`.`site_supervisor`="{employee}")'.format(employee = employee)

	return ""


def create():
	frappe.enqueue(create_roster_employee_actions, is_async=True, queue='long')


def create_roster_employee_actions():
	"""
		This function creates a Roster Employee Actions document and issues notifications to relevant supervisors
		directing them to schedule employees that are unscheduled and assigned to them.
		It computes employees not scheduled for the span of two weeks, starting from tomorrow.
	"""

	start_date = getdate(add_to_date(cstr(getdate()), days=-2)) # start date to be from tomorrow
	end_date = getdate(add_to_date(start_date, days=4)) # end date to be 14 days after start date

	employees_not_rostered = get_employees_not_rostered(start_date, end_date)
	supervisors_not_rostered_employees = get_supervisors_not_rostered_employees(employees_not_rostered, start_date)
	print(supervisors_not_rostered_employees)

	# for each supervisor, create a roster action
	for supervisor in supervisors_not_rostered_employees:
		try:
			site_supervisor = frappe.get_value('Operations Site', supervisor.site, 'account_supervisor')
			employees = supervisor.employees.split(",")

			roster_employee_actions = frappe.new_doc("Roster Employee Actions")
			roster_employee_actions.start_date = start_date
			roster_employee_actions.end_date = end_date
			roster_employee_actions.status = "Pending"
			roster_employee_actions.action_type = "Roster Employee"
			roster_employee_actions.supervisor = supervisor.shift_supervisor
			roster_employee_actions.site_supervisor = site_supervisor
			for employee in employees:
				roster_employee_actions.append('employees_not_rostered', {
					'employee': employee,
					"missing_dates": ", ".join(employees_not_rostered.get(employee))
				})
			roster_employee_actions.save()
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Error while generating Roster employee actions")
			continue
		frappe.db.commit()

def get_employees_not_rostered(start_date, end_date):
	"""
		Method to find the shift working employees not rostered in the given date range
		args:
			start_date: Date obj, Sart of the date range
			end_date: Date obj, End of the date range
		Return: Dictionary of employees with the dates(in which they are not rostered)
		Eg: {'HR-EMP-00001': ['2024-04-10', '2024-04-09'], 'HR-EMP-00002': ['2024-04-10']}
	"""
	# fetch employees that are active and don't have a schedule in the specified date range
	shift_working_active_employees = get_shift_working_active_employees(start_date, end_date)
	employees_rostered = get_rostered_employees(start_date, end_date)
	employees_not_rostered = set(shift_working_active_employees) - set(employees_rostered)
	# Eg: {('HR-EMP-00001', '2024-04-09'), ('HR-EMP-00001', '2024-04-10'), ('HR-EMP-00002', '2024-04-08'), ('HR-EMP-00002', '2024-04-10')}

	employees_on_leave_in_period = get_employees_on_leave_in_period(start_date, end_date)
	if employees_on_leave_in_period and len(employees_on_leave_in_period) > 0:
		# Employee on leave not need to be rostered, so removing the employee on the date from the list
		employees_not_rostered = employees_not_rostered - set(employees_on_leave_in_period)
		# Eg: {('HR-EMP-00001', '2024-04-09'), ('HR-EMP-00001', '2024-04-10'), ('HR-EMP-00002', '2024-04-10')}

	employees_not_rostered_dict = False
	try:
		employees_not_rostered_dict = OrderedDict()
		for obj in employees_not_rostered:
			employees_not_rostered_dict.setdefault(obj[0], []).append(obj[1])
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Error while generating missing dates(Roster Employee Actions)")

	return employees_not_rostered_dict

def get_shift_working_active_employees(start_date, end_date):
	"""
		A method to get list of combination of active shift working empoyees with a date range
		This code generates all possible combinations of those employees with dates
		between the start and end date (inclusive).

		args:
			start_date: Date Object
			end_date: Date Object

		Return: List of tuples.
		Eg: [('HR-EMP-00001', '2024-04-08'), ('HR-EMP-00001', '2024-04-09'), ('HR-EMP-00001', '2024-04-10'),
		('HR-EMP-00002', '2024-04-08'), ('HR-EMP-00002', '2024-04-09'), ('HR-EMP-00002', '2024-04-10')]
	"""

	active_employees = frappe.db.sql("""
		select
			employee
		from
			`tabEmployee`
		where
			status = 'Active'
			and
			shift_working = 1
	""", as_dict=1)

	return [
		(employee.employee, (start_date + timedelta(days=x)).strftime('%Y-%m-%d'))
		for employee in active_employees
		for x in range((end_date - start_date).days + 1)
	]

def get_rostered_employees(start_date, end_date):
	"""
		A method to get list of combination of rostered empoyees with a date range
		This code iterates through a list of employee rosters
		For each roster entry, it extracts the employee information and formats the date into a consistent YYYY-MM-DD format.

		args:
			start_date: Date Object
			end_date: Date Object

		Return: List of tuples.
		Eg: [('HR-EMP-00001', '2024-04-08'), ('HR-EMP-00002', '2024-04-09')]
	"""

	employees_rostered = frappe.db.sql(f"""
		select
			employee, date
        from
			`tabEmployee Schedule`
        where
			date >= '{start_date}'
			and
			date <= '{end_date}'
    """, as_dict=True)

	return [
		(roster.employee, (roster.date).strftime('%Y-%m-%d'))
		for roster in employees_rostered
	]

def get_employees_on_leave_in_period(start_date, end_date):
	"""
		Method to return leave employee between the date range
		args:
			start_date: Date obj, Sart of the date range
			end_date: Date obj, End of the date range
		return: list of employee ID
		Eg: [('HR-EMP-00002', '2024-04-08')] Considerring HR-EMP-00002 is leave on '2024-04-08'
	"""

	leaves = frappe.db.sql(f"""
		select
			employee, from_date, to_date
        from
			`tabLeave Application`
        where
			from_date >= '{start_date}'
			and
			to_date <= '{end_date}'
			and
			status = 'Open'
    """, as_dict=True)

	return [
		(leave.employee, (leave.from_date + timedelta(days=x)).strftime('%Y-%m-%d'))
		for leave in leaves
		for x in range((leave.to_date - leave.from_date).days + 1)
	]

def get_supervisors_not_rostered_employees(employees_not_rostered, date):
	"""
		Method to fetch supervisors along with employees who are not rostered (scheduled) for a given date
		args:
			employees_not_rostered: Dictionary of employees with the dates(in which they are not rostered)
			date: date object

		return: List of dict of supervisor and non rostered employees of the supervisor
		Eg: [{'shift_supervisor': 'HR-EMP-00003', 'site': 'Site1', 'employees': 'HR-EMP-00001, HR-EMP-00002'}]
	"""
	employee_ids = tuple(employees_not_rostered.keys())
	query = """
		SELECT
			oss.supervisor AS shift_supervisor,
			os.site AS site,
			GROUP_CONCAT(e.name) AS employees
		FROM
			`tabOperations Shift` AS os
		JOIN
			`tabOperations Shift Supervisor` AS oss
			ON oss.parent = os.name AND oss.parenttype = 'Operations Shift'
		JOIN
			(
				SELECT
					es.employee
				FROM
					`tabEmployee Schedule` AS es
				WHERE
					es.date = '{0}'
					AND
					es.employee_availability = 'Working'
			) AS ess
			ON ess.employee = oss.supervisor
		JOIN
			`tabEmployee` AS e
			ON e.shift = os.name
		WHERE
			os.status = 'Active'
			AND
			e.name IN {1}
		GROUP BY
			oss.supervisor, os.site
	""".format(date, employee_ids)
	return frappe.db.sql(query, as_dict=True)
