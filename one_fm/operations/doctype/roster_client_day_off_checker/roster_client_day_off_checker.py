# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_first_day, get_last_day, getdate, add_months, nowdate, add_days
from datetime import date
from one_fm.operations.doctype.operations_shift.operations_shift import get_shift_supervisor


monthname_dict = {
	"01": "January",
	"02": "February",
	"03": "March",
	"04": "April",
	"05": "May",
	"06": "June",
	"07": "July",
	"08": "August",
	"09": "September",
	"10": "October",
	"11": "November",
	"12": "December",
}


class RosterClientDayOffChecker(Document):
	def autoname(self):
		# Standard name format
		self.name = f"OPR-RCDOC-{self.employee}-{self.monthweek}"
		
		# Check if name already exists
		if frappe.db.exists("Roster Client Day Off Checker", self.name):
			# Append suffix -1, -2, etc. until unique
			count = 1
			while True:
				new_name = f"{self.name}-{count}"
				if not frappe.db.exists("Roster Client Day Off Checker", new_name):
					self.name = new_name
					break
				count += 1


def get_employee_cdo_count(employee, start_date, end_date):
	"""
	Count the number of Client Day Off schedules for an employee within a date range.
	
	Args:
		employee (str): Employee ID
		start_date (date): Start date of the period
		end_date (date): End date of the period
	
	Returns:
		int: Count of Client Day Off schedules
	"""
	cdo_count = frappe.db.count("Employee Schedule", {
		"employee": employee,
		"date": ["between", [start_date, end_date]],
		"employee_availability": "Client Day Off"
	})
	
	return cdo_count


def format_reporting_month(month_date):
	"""
	Format a date as '[Month Name] [YYYY]' for reporting month field.
	
	Args:
		month_date (date): Any date within the month
	
	Returns:
		str: Formatted month string (e.g., "February 2026")
	"""
	month_str = month_date.strftime("%m")
	year_str = month_date.strftime("%Y")
	return f"{monthname_dict[month_str]} {year_str}"


def create_or_update_cdo_checker(employee, month_start, month_end, cdo_count, today):
	"""
	Create or update a Client Day Off Checker record for an employee.
	
	Logic:
	- If no record exists: Create new with repeat_count = 1
	- If record exists with status = "Pending":
		- If CDO still > 3: Delete old record and create new with incremented repeat_count
		- If CDO <= 3: Skip (issue resolved but not marked Complete)
	- If record exists with status = "Completed":
		- If CDO > 3 again: Create new record with repeat_count = 1 (new issue)
	
	Args:
		employee (frappe.Document): Employee document
		month_start (date): First day of the month
		month_end (date): Last day of the month
		cdo_count (int): Current CDO count for the month
		today (date): Current date
	"""
	reporting_month = format_reporting_month(month_start)
	
	# Check for existing record
	existing_records = frappe.get_all(
		"Roster Client Day Off Checker",
		filters={
			"employee": employee.name,
			"monthweek": reporting_month  # Field name is 'monthweek' in DocType
		},
		fields=["name", "status", "repeat_count"],
		order_by="creation desc",
		limit=1
	)
	
	
	# Get supervisors
	shift_supervisor = get_shift_supervisor(employee.shift, today) if employee.shift else None
	site_supervisor = frappe.db.get_value("Operations Site", employee.site, "site_supervisor") if employee.site else None
	project_manager = frappe.db.get_value("Project", employee.project, "project_manager") if employee.project else None
	
	if not existing_records:
		# No existing record - create new one
		_create_new_cdo_checker(
			employee=employee,
			reporting_month=reporting_month,
			cdo_count=cdo_count,
			repeat_count=1,
			shift_supervisor=shift_supervisor,
			site_supervisor=site_supervisor,
			project_manager=project_manager,
			today=today
		)
	else:
		existing_record = existing_records[0]
		
		if existing_record["status"] == "Pending":
			# Check if issue is still present
			if cdo_count > 3:
				# Issue still exists - increment repeat count
				yesterday_repeat_count = frappe.db.get_value(
					"Roster Client Day Off Checker",
					{
						"employee": employee.name,
						"monthweek": reporting_month,  # Field name is 'monthweek'
						"date": add_days(today, -1)
					},
					"repeat_count"
				)
				
				# Delete existing record for today if it exists
				frappe.delete_doc_if_exists("Roster Client Day Off Checker", existing_record["name"])
				
				# Create new record with incremented repeat count
				new_repeat_count = (yesterday_repeat_count or existing_record["repeat_count"]) + 1
				_create_new_cdo_checker(
					employee=employee,
					reporting_month=reporting_month,
					cdo_count=cdo_count,
					repeat_count=new_repeat_count,
					shift_supervisor=shift_supervisor,
					site_supervisor=site_supervisor,
					project_manager=project_manager,
					today=today
				)
			# else: CDO <= 3, issue resolved but not marked Complete - skip
		
		elif existing_record["status"] == "Completed":
			# Issue was previously resolved but has recurred
			if cdo_count > 3:
				# Create new record with repeat_count = 1 (new issue)
				# Autoname format now supports multiple records per month
				_create_new_cdo_checker(
					employee=employee,
					reporting_month=reporting_month,
					cdo_count=cdo_count,
					repeat_count=1,
					shift_supervisor=shift_supervisor,
					site_supervisor=site_supervisor,
					project_manager=project_manager,
					today=today
				)


def _create_new_cdo_checker(employee, reporting_month, cdo_count, repeat_count, shift_supervisor, site_supervisor, project_manager, today):
	"""
	Internal function to create a new Roster Client Day Off Checker record.
	
	Args:
		employee (frappe.Document): Employee document
		reporting_month (str): Formatted reporting month
		cdo_count (int): CDO count
		repeat_count (int): Repeat count
		shift_supervisor (str): Shift supervisor employee ID
		site_supervisor (str): Site supervisor employee ID
		project_manager (str): Project manager employee ID
		today (date): Current date
	"""
	cdo_checker = frappe.new_doc("Roster Client Day Off Checker")
	cdo_checker.date = today
	cdo_checker.monthweek = reporting_month  # Field name is 'monthweek' in DocType
	cdo_checker.status = "Pending"
	cdo_checker.repeat_count = repeat_count
	cdo_checker.employee = employee.name
	cdo_checker.assigned_client_day_off_count = cdo_count  # Field name is 'assigned_client_day_off_count'
	cdo_checker.client_day_off_explanation = "The employee has been scheduled for more than 3 Client Day Off in a month."
	cdo_checker.shift_supervisor = shift_supervisor
	cdo_checker.site_supervisor = site_supervisor
	cdo_checker.project_manager = project_manager
	cdo_checker.insert(ignore_permissions=True)
	frappe.db.commit()



def check_roster_client_day_off():
	"""
	Main scheduled function to check for excessive Client Day Off assignments.
	
	Runs daily at 4:30 AM to:
	1. Query all active employees
	2. Check current month and next month for each employee
	3. Create/update checker records for employees with > 3 CDOs per month
	"""
	try:
		today = getdate(nowdate())
		
		# Get all active employees
		Employee = frappe.qb.DocType("Employee")
		employees = frappe.db.sql(
			frappe.qb.from_(Employee)
			.select("*")
			.where(
				(Employee.status.isin(["Active", "Vacation"])) &
				(Employee.shift_working == 1) &
				((Employee.relieving_date.isnull()) | (Employee.relieving_date > today))
			),
			as_dict=1
		)
		
		for employee in employees:
			# Check current month
			current_month_start = get_first_day(today)
			current_month_end = get_last_day(today)
			current_cdo_count = get_employee_cdo_count(employee.name, current_month_start, current_month_end)
			
			if current_cdo_count > 3:
				create_or_update_cdo_checker(employee, current_month_start, current_month_end, current_cdo_count, today)
			
			# Check next month
			next_month = add_months(today, 1)
			next_month_start = get_first_day(next_month)
			next_month_end = get_last_day(next_month)
			next_cdo_count = get_employee_cdo_count(employee.name, next_month_start, next_month_end)
			
			if next_cdo_count > 3:
				create_or_update_cdo_checker(employee, next_month_start, next_month_end, next_cdo_count, today)
		
		frappe.db.commit()
	
	except Exception:
		frappe.log_error(
			title="Error creating Client Day Off checkers",
			message=frappe.get_traceback()
		)


@frappe.whitelist()
def generate_client_day_off_checker():
	"""
	Whitelisted function to manually trigger Client Day Off checker generation.
	Only accessible by Operations Admin, Operations Manager, Projects Manager, and System Manager.
	Enqueues the check_roster_client_day_off function to run in the background.
	"""
	allowed_roles = ["Operation Admin", "Operations Manager", "Projects Manager", "System Manager"]
	if not any(frappe.db.exists("Has Role", {"parent": frappe.session.user, "role": role}) for role in allowed_roles):
		frappe.throw(
			msg=_("You do not have permission to run the Client Day Off Checker. Required role: Operation Admin, Operations Manager, or Projects Manager."),
			title=_("Not Permitted"),
			exc=frappe.PermissionError,
		)
	frappe.enqueue(check_roster_client_day_off, queue="long", timeout=4000)

