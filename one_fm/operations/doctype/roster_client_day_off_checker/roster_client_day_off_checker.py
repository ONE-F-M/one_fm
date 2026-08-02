# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, add_days
from datetime import timedelta
from one_fm.operations.doctype.operations_shift.operations_shift import get_shift_supervisor





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


def get_week_start(ref_date):
	"""
	Return the Sunday that starts the week containing ref_date.

	Weeks run Sunday (0) to Saturday (6).

	Args:
		ref_date (date): Reference date

	Returns:
		date: The Sunday at or before ref_date
	"""
	ref_date = getdate(ref_date)
	# isoweekday(): Monday=1 … Sunday=7
	days_since_sunday = ref_date.isoweekday() % 7  # Sunday→0, Mon→1 … Sat→6
	return ref_date - timedelta(days=days_since_sunday)


def get_week_end(ref_date):
	"""
	Return the Saturday that ends the week containing ref_date.

	Args:
		ref_date (date): Reference date

	Returns:
		date: The Saturday at or after ref_date
	"""
	return get_week_start(ref_date) + timedelta(days=6)


def format_reporting_week(period_start, period_end):
	"""
	Format the two-week evaluation window as 'Week <current>-<next> <YYYY>'.

	Uses the ISO week of the window start date and adds 1 for the next week,
	since the window always spans exactly two consecutive weeks.

	Args:
		period_start (date): Start of the window (current week Sunday)
		period_end (date): End of the window (next week Saturday)

	Returns:
		str: Formatted week string (e.g., "Week 24-25 2026")
	"""
	period_start = getdate(period_start)
	period_end = getdate(period_end)
	# Shift to Monday (+1 day) since ISO weeks run Mon–Sun, and our window starts on Sunday.
	current_monday = period_start + timedelta(days=1)
	# period_end is the next week's Saturday, so Monday of that week is 5 days earlier.
	next_monday = period_end - timedelta(days=5)
	current_year, current_week, _ = current_monday.isocalendar()
	next_year, next_week, _ = next_monday.isocalendar()
	if current_year == next_year:
		return f"Week {current_week}-{next_week} {current_year}"
	return f"Week {current_week}-{next_week} {current_year}/{next_year}"


def create_or_update_cdo_checker(employee, period_start, period_end, cdo_count, today):
	"""
	Create or update a Client Day Off Checker record for an employee.

	Logic:
	- If no record exists: Create new with repeat_count = 1
	- If record exists with status = "Pending":
		- If CDO still > 1: Delete old record and create new with incremented repeat_count
		- If CDO <= 1: Skip (issue resolved but not marked Complete)
	- If record exists with status = "Completed":
		- If CDO > 1 again: Create new record with repeat_count = 1 (new issue)

	Args:
		employee (frappe.Document): Employee document
		period_start (date): Start of the evaluation window (current week Sunday)
		period_end (date): End of the evaluation window (next week Saturday)
		cdo_count (int): Current CDO count within the two-week window
		today (date): Current date
	"""
	reporting_week = format_reporting_week(period_start, period_end)
	
	# Check for existing record
	existing_records = frappe.get_all(
		"Roster Client Day Off Checker",
		filters={
			"employee": employee.name,
			"monthweek": reporting_week
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
			reporting_week=reporting_week,
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
			if cdo_count > 1:
				# Issue still exists - increment repeat count
				yesterday_repeat_count = frappe.db.get_value(
					"Roster Client Day Off Checker",
					{
						"employee": employee.name,
						"monthweek": reporting_week,
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
					reporting_week=reporting_week,
					cdo_count=cdo_count,
					repeat_count=new_repeat_count,
					shift_supervisor=shift_supervisor,
					site_supervisor=site_supervisor,
					project_manager=project_manager,
					today=today
				)
			# else: CDO <= 1, issue resolved but not marked Complete - skip
		
		elif existing_record["status"] == "Completed":
			# Issue was previously resolved but has recurred
			if cdo_count > 1:
				# Create new record with repeat_count = 1 (new issue)
				# Autoname format now supports multiple records per month
				_create_new_cdo_checker(
					employee=employee,
					reporting_week=reporting_week,
					cdo_count=cdo_count,
					repeat_count=1,
					shift_supervisor=shift_supervisor,
					site_supervisor=site_supervisor,
					project_manager=project_manager,
					today=today
				)


def _create_new_cdo_checker(employee, reporting_week, cdo_count, repeat_count, shift_supervisor, site_supervisor, project_manager, today):
	"""
	Internal function to create a new Roster Client Day Off Checker record.

	Args:
		employee (frappe.Document): Employee document
		reporting_week (str): Formatted reporting week label (e.g., "Week 25 2026")
		cdo_count (int): CDO count
		repeat_count (int): Repeat count
		shift_supervisor (str): Shift supervisor employee ID
		site_supervisor (str): Site supervisor employee ID
		project_manager (str): Project manager employee ID
		today (date): Current date
	"""
	cdo_checker = frappe.new_doc("Roster Client Day Off Checker")
	cdo_checker.date = today
	cdo_checker.monthweek = reporting_week
	cdo_checker.status = "Pending"
	cdo_checker.repeat_count = repeat_count
	cdo_checker.employee = employee.name
	cdo_checker.assigned_client_day_off_count = cdo_count
	cdo_checker.client_day_off_explanation = (
		"The employee has been scheduled for more than 1 Client Day Off "
		"within the current and next week window."
	)
	cdo_checker.shift_supervisor = shift_supervisor
	cdo_checker.site_supervisor = site_supervisor
	cdo_checker.project_manager = project_manager
	cdo_checker.insert(ignore_permissions=True)
	frappe.db.commit()



def check_roster_client_day_off():
	"""
	Main scheduled function to check for excessive Client Day Off assignments.

	Runs daily at 4:30 AM to:
	1. Query all active, shift-working employees
	2. Count CDO records in a combined two-week window (current week + next week,
	   Sunday-Saturday)
	3. Create/update checker records for employees with > 1 CDOs in the window
	"""
	try:
		today = getdate(nowdate())

		# Compute the two-week window: current week (Sun–Sat) + next week (Sun–Sat)
		current_week_start = get_week_start(today)
		next_week_end = get_week_end(current_week_start + timedelta(days=7))

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
			# Count CDOs across the full two-week window
			cdo_count = get_employee_cdo_count(
				employee.name, current_week_start, next_week_end
			)

			if cdo_count > 1:
				# Use current week start as the reference for the reporting label
				create_or_update_cdo_checker(
					employee, current_week_start, next_week_end,
					cdo_count, today
				)

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



@frappe.whitelist()
def get_take_action_data(checker: str) -> dict:
	"""
	Redirect path and roster filters for the Take Action button (WI-001690).

	Returns the same {path, params} shape as the Contract Compliance Checker's
	equivalent, so the client handling is identical.

	The checker stores the employee's allocations as plain text (project_allocation,
	site_allocation, shift_allocation) and carries no operations role, so anything
	missing is resolved from the Employee record - which is also where the role lives.
	"""
	doc = frappe.get_doc("Roster Client Day Off Checker", checker)
	doc.check_permission("read")

	employee = (
		frappe.db.get_value(
			"Employee",
			doc.employee,
			["project", "site", "shift", "custom_operations_role_allocation", "employee_id", "employee_name"],
			as_dict=True,
		)
		or frappe._dict()
	)

	# The roster reads these off the query string in setup_staff_filters(); year and
	# month drive which month the calendar opens on.
	date = getdate(doc.date) if doc.date else getdate(nowdate())

	return {
		"path": "/app/roster",
		"params": {
			"main_view": "roster",
			"sub_view": "roster",
			"employee_id": doc.employee_id or employee.employee_id,
			"employee_name": doc.employee_name or employee.employee_name,
			"project": doc.project_allocation or employee.project,
			"site": doc.site_allocation or employee.site,
			"shift": doc.shift_allocation or employee.shift,
			"operations_role": employee.custom_operations_role_allocation,
			"year": str(date.year),
			"month": str(date.month),
		},
	}
