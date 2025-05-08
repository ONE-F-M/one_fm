# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from datetime import timedelta, datetime
from collections import OrderedDict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import  add_to_date, cstr, getdate
from frappe.permissions import get_doctype_roles

from one_fm.one_fm.page.roster.roster import get_current_user_details


class RosterEmployeeActions(Document):
	def autoname(self):
		base_name = f"{self.start_date}|{self.end_date}|{self.action_type}|{self.supervisor or self.site_supervisor or self.project_manager}"

		# Check if a document with this name already exists
		existing = frappe.db.exists("Roster Employee Actions", base_name)
		if not existing:
			self.name = base_name
		else:
			# Increment until a unique name is found
			i = 1
			while True:
				new_name = f"{base_name}|{i}"
				if not frappe.db.exists("Roster Employee Actions", new_name):
					self.name = new_name
					break
				i += 1


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

	start_date = getdate(add_to_date(cstr(getdate()), days=1)) # start date to be from tomorrow
	end_date = getdate(add_to_date(start_date, days=14)) # end date to be 14 days after start date

	employees_not_rostered = get_employees_not_rostered(start_date, end_date)
	supervisors_not_rostered_employees = get_supervisors_not_rostered_employees(employees_not_rostered, start_date)

	# for each supervisor, create a roster action
	for supervisor in supervisors_not_rostered_employees:
		try:
			site_supervisor = frappe.get_value('Operations Site', supervisor.site, 'account_supervisor')
			employees = supervisor.employees.split(",")
			project_manager = frappe.get_value('Project', supervisor.project, 'account_manager')

			roster_employee_actions = frappe.new_doc("Roster Employee Actions")
			roster_employee_actions.start_date = start_date
			roster_employee_actions.end_date = end_date
			roster_employee_actions.status = "Pending"
			roster_employee_actions.action_type = "Roster Employee"

			if supervisor.supervisor_source and supervisor.supervisor_source == "Shift":
				roster_employee_actions.supervisor = supervisor.shift_supervisor
				roster_employee_actions.site_supervisor = site_supervisor
				roster_employee_actions.project_manager = project_manager
			elif supervisor.supervisor_source and supervisor.supervisor_source == "Site":
				roster_employee_actions.site_supervisor = supervisor.shift_supervisor
				roster_employee_actions.project_manager = project_manager
			elif supervisor.supervisor_source and supervisor.supervisor_source == "Project":
				roster_employee_actions.project_manager = supervisor.shift_supervisor

			for employee in employees:
				sorted_dates = sorted(
				[datetime.strptime(date.strip(), "%Y-%m-%d") for date in employees_not_rostered.get(employee, [])]
			)
				roster_employee_actions.append('employees_not_rostered', {
					'employee': employee,
					"missing_dates": ", ".join([date.strftime("%Y-%m-%d") for date in sorted_dates])
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
		Eg: [('HR-EMP-00001', '2024IN093', 'John Doe', '2024-04-08'), ('HR-EMP-00001', '2024IN093', 'Jane Doe', '2024-04-09')]
	"""

	active_employees = frappe.db.sql("""
		select
			employee,
			relieving_date

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
		if employee.relieving_date is None or (start_date + timedelta(days=x)) < employee.relieving_date
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
			es.employee, es.date
		from
			`tabEmployee Schedule` es
		join `tabEmployee` emp
		on es.employee=emp.name
		where
			es.date >= '{start_date}'
			and
			es.date <= '{end_date}'
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
		SELECT 
			la.employee, la.from_date, la.to_date
		FROM 
			`tabLeave Application` la
		JOIN `tabEmployee` emp
		ON la.employee=emp.name
		WHERE 
			(la.from_date >= '{start_date}' AND la.to_date <= '{end_date}' AND la.status IN ('Open', 'Approved'))
			OR 
			la.name IN (
				SELECT DISTINCT leave_application 
				FROM `tabAttendance` 
				WHERE attendance_date >= '{start_date}'
				AND attendance_date <= '{end_date}' 
				AND status = 'On Leave'
			)
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
		Eg: [{'shift_supervisor': 'HR-EMP-00003', 'supervisor_source': 'Project/Shift/Site','project': 'P1', 'site': 'Site1', 'employees': 'HR-EMP-00001, HR-EMP-00002'}]
	"""
	employee_list = list(employees_not_rostered.keys())

	# To create ("HR-EMP-1", "HR-EMP-2", "HR-EMP-3")
	employee_ids = f"""({",".join([f"'{emp_id}'" for emp_id in employee_list])})"""


	query = """
		SELECT
			COALESCE(
				CASE WHEN ess.employee IS NOT NULL THEN oss.supervisor ELSE NULL END,
				CASE WHEN osi.account_supervisor IS NOT NULL AND osi.account_supervisor != '' THEN osi.account_supervisor ELSE NULL END,
				p.account_manager
			) AS shift_supervisor,

			CASE
				WHEN ess.employee IS NOT NULL THEN 'Shift'
				WHEN (osi.account_supervisor IS NOT NULL AND osi.account_supervisor != '') THEN 'Site'
				WHEN p.account_manager IS NOT NULL THEN 'Project'
				ELSE 'None'
			END AS supervisor_source,

			os.project As project,
			os.site AS site,
			GROUP_CONCAT(DISTINCT e.name) AS employees
		FROM
			`tabOperations Shift` AS os
		LEFT JOIN
			`tabOperations Site` AS osi ON osi.name = os.site
		LEFT JOIN
			`tabProject` AS p ON p.name = os.project
		LEFT JOIN
			(
				SELECT 
					parent AS shift_name,
					supervisor,
					ROW_NUMBER() OVER (PARTITION BY parent ORDER BY idx) AS rn
				FROM `tabOperations Shift Supervisor`
				WHERE parenttype = 'Operations Shift'
			) AS oss ON oss.shift_name = os.name AND oss.rn = 1
		LEFT JOIN
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
			AND (oss.supervisor IS NULL OR ess.employee IS NOT NULL)
		GROUP BY
		    shift_supervisor, os.site
	""".format(date, employee_ids)
	result = frappe.db.sql(query, as_dict=True)

	return result


## Roster Employee Actions code for Roster view below
@frappe.whitelist()
def get_employees_with_missing_schedules():
	"""
	Returns employees with missing schedules based on current user's role
	Returns: OrderedDict {employee: [missing_dates]}
	"""
	start_date = getdate(add_to_date(cstr(getdate()), days=1))  # Tomorrow
	end_date = getdate(add_to_date(start_date, days=14))        # 14 days later

	# Get current user details
	user, user_roles, user_employee = get_current_user_details()

	if not user_employee:
		frappe.throw("No employee record linked to current user")

	# Get base employee list based on role
	if "Operations Manager" in user_roles:
		employees = get_shift_working_active_employees(start_date, end_date)
	elif "Project Manager" in user_roles:
		employees = get_project_manager_employees(user_employee.name, start_date, end_date)
	elif "Site Supervisor" in user_roles:
		employees = get_site_supervisor_employees(user_employee.name, start_date, end_date)
	elif "Shift Supervisor" in user_roles:
		employees = get_shift_supervisor_employees(user_employee.name, start_date, end_date)
	else:
		return OrderedDict()


	rostered = get_rostered_employees(start_date, end_date)
	on_leave = get_employees_on_leave_in_period(start_date, end_date)
	
	missing_schedules = set(employees) - set(rostered) - set(on_leave)
	result = OrderedDict()

	
	for employee, date in missing_schedules:
		if employee not in result:
			result[employee] = {
				"dates": []
			}
		result[employee]["dates"].append(date)

	# Sort dates for each employee
	for employee in result:
		result[employee]["dates"] = sorted(result[employee]["dates"])
	html_output = render_employees_missing_schedules_html(result)
	return html_output


def render_employees_missing_schedules_html(missing_schedules):
	"""
	missing_schedules: {employee_docname: {"employee_id": ..., "employee_name": ..., "dates": [...]}}
	"""
	if len(missing_schedules) > 0:
		html = "<table class='table table-bordered'>"
		html += """<thead>
					<tr>
						<th>Employee ID</th>
						<th>Employee Name</th>
						<th>Shift Allocation</th>
						<th>Missing Dates</th>
						<th></th>
					</tr>
				</thead><tbody>"""
	
		for emp, info in missing_schedules.items():
			emp_info = frappe.db.get_value("Employee", emp, ["employee_name", "employee_id", "shift"], as_dict=1)
			formatted_dates = [
				datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y") for date in info["dates"]
			]
			dates_str = ", ".join(formatted_dates)
			html += f"""<tr>
							<td>{emp_info["employee_id"]}</td>
							<td>{emp_info["employee_name"]}</td>
							<td>{emp_info["shift"]}</td>
							<td>{dates_str}</td>
							<td><a class="btn btn-warning" target="_blank" href="/app/roster?main_view='roster'&sub_view='basic'&roster_type='basic'&shift={emp_info["shift"]}&employee_id={emp_info["employee_id"]}">Take Action</a></td>
						</tr>"""
		html += "</tbody></table>"
		return html

	html = """
		<div class="alert text-center" role="alert">
			<h5 class="mb-0">No employees with missing schedules found.</h5>
		</div>
	"""
	return html


def get_project_manager_employees(user_employee, start_date, end_date):
	"""Employees in projects managed by current user"""
	return _get_employees_with_join(
		join_clause="""
			JOIN `tabOperations Shift` os ON e.shift = os.name
			JOIN `tabOperations Site` site ON os.site = site.name 
			JOIN `tabProject` p ON site.project = p.name
		""",
		where_clause="p.account_manager = %(user_employee)s",
		user_employee=user_employee,
		start_date=start_date,
		end_date=end_date
	)

def get_site_supervisor_employees(user_employee, start_date, end_date):
	"""Employees in sites managed by current user"""
	return _get_employees_with_join(
		join_clause="""
			JOIN `tabOperations Shift` os ON e.shift = os.name
			JOIN `tabOperations Site` site ON os.site = site.name
		""",
		where_clause="site.account_supervisor = %(user_employee)s",
		user_employee=user_employee,
		start_date=start_date,
		end_date=end_date
	)

def get_shift_supervisor_employees(user_employee, start_date, end_date):
	"""Employees in shifts managed by current user"""
	return _get_employees_with_join(
		join_clause="""
			JOIN `tabOperations Shift` os ON e.shift = os.name
			JOIN `tabOperations Shift Supervisor` oss 
				ON os.name = oss.parent AND oss.parenttype = 'Operations Shift'
		""",
		where_clause="oss.supervisor = %(user_employee)s",
		user_employee=user_employee,
		start_date=start_date,
		end_date=end_date
	)

def _get_employees_with_join(join_clause, where_clause, user_employee, start_date, end_date):
	"""Generic query builder for role-based employee fetching"""
	employees = frappe.db.sql(f"""
		SELECT 
			e.name as employee,
			e.relieving_date
		FROM `tabEmployee` e
		{join_clause}
		WHERE
			e.status = 'Active'
			AND e.shift_working = 1
			AND {where_clause}
	""", {"user_employee": user_employee}, as_dict=True)

	return [
		(emp.employee, (start_date + timedelta(days=x)).strftime('%Y-%m-%d'))
		for emp in employees
		for x in range((end_date - start_date).days + 1)
		if not emp.relieving_date or (start_date + timedelta(days=x)) < emp.relieving_date
	]
