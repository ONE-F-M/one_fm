# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

from collections import OrderedDict
import frappe
from frappe.utils import (
    get_first_day, get_last_day, getdate, add_days, add_months
)
from frappe.model.document import Document
from frappe.query_builder.functions import Count
from one_fm.one_fm.page.roster.roster import get_current_user_details
from one_fm.operations.doctype.operations_shift.operations_shift import get_shift_supervisor

monthname_dict = {
	"01": "Jan",
	"02": "Feb",
	"03": "Mar",
	"04": "Apr",
	"05": "May",
	"06": "Jun",
	"07": "Jul",
	"08": "Aug",
	"09": "Sep",
	"10": "Oct",
	"11": "Nov",
	"12": "Dec",
}


class RosterDayOffChecker(Document):
	pass

def get_day_off_comparison_dates(day_off_category):
    today = getdate()
    comparison_periods = []

    if day_off_category == "Monthly":
        # Current month
        current_month_start = get_first_day(today)
        current_month_end = get_last_day(today)
        comparison_periods.append({
            "start_date": current_month_start,
            "end_date": current_month_end
        })

        # Next month
        next_month_date = add_months(today, 1)
        next_month_start = get_first_day(next_month_date)
        next_month_end = get_last_day(next_month_date)
        comparison_periods.append({
            "start_date": next_month_start,
            "end_date": next_month_end
        })

    elif day_off_category == "Weekly":
        # First 7-day period starting from tomorrow
        week1_start = add_days(today, 1)
        week1_end = add_days(week1_start, 6)
        comparison_periods.append({
            "start_date": week1_start,
            "end_date": week1_end
        })

        # Next 7-day period
        week2_start = add_days(week1_end, 1)
        week2_end = add_days(week2_start, 6)
        comparison_periods.append({
            "start_date": week2_start,
            "end_date": week2_end
        })

    return comparison_periods

def check_roster_day_off():
	# Get all active employees
	# Validate their offs for next 2 months/weeks based on their Day Off Category
	# If discrepency, create record with each employee info
	try:
		Employee = frappe.qb.DocType("Employee")
		employees = frappe.db.sql(frappe.qb.from_(Employee).select("*").where((Employee.status=="Active") & (Employee.shift_working == 1)), as_dict=1)

		today = getdate()

		for employee in employees:
			comparison_dates = get_day_off_comparison_dates(employee.day_off_category)

			site_supervisor = frappe.db.get_value("Operations Site", employee.site, "account_supervisor")
			shift_supervisor = get_shift_supervisor(employee.shift)
			project_manager = frappe.db.get_value("Project", employee.project, "account_manager")

			for period in comparison_dates:	# Always 2 iterations only because we have just two period for comparison	
				day_off_data = get_employee_day_off_comparison(employee, period["start_date"], period["end_date"])

				if day_off_data["day_off_difference"]:
					duration = day_off_data["monthweek"]
		
					# Delete exising for target duration against employee
					frappe.delete_doc_if_exists("Roster Day Off Checker", f"OPR-RDOC-{employee.name}-{duration}")

					day_off_checker = frappe.new_doc("Roster Day Off Checker")
					day_off_checker.date = today
					day_off_checker.monthweek = duration
					day_off_checker.employee = employee.name
					day_off_checker.shift_supervisor = shift_supervisor
					day_off_checker.site_supervisor = site_supervisor
					day_off_checker.project_manager = project_manager
					day_off_checker.day_off_difference = day_off_data["day_off_difference"]
					day_off_checker.insert(ignore_permissions=1)

	except Exception:
		frappe.log_error(frappe.get_traceback())

def get_employee_day_off_comparison(employee, start_date, end_date):		
	EmployeeSchedule = frappe.qb.DocType("Employee Schedule")

	# QB conditions
	employee_name = (EmployeeSchedule.employee == employee.name) 
	employee_schedule_date = (EmployeeSchedule.date[start_date:end_date])
		
	# Calculate no of off days
	od = frappe.db.sql(frappe.qb.from_(EmployeeSchedule)        
		.select(Count("name").as_("off_days"))
		.where(employee_schedule_date & employee_name & (EmployeeSchedule.employee_availability == "Day Off") & (EmployeeSchedule.day_off_ot == 0))
		.groupby(EmployeeSchedule.employee), 
	as_dict=1) 
	off_days = od[0].off_days if len(od) > 0 else 0 

	# Calculate no of ot days
	ot = frappe.db.sql( frappe.qb.from_(EmployeeSchedule)
		.select(Count("name").as_("ot_days"))
		.where(employee_schedule_date & employee_name & (EmployeeSchedule.day_off_ot == 1))
		.groupby(EmployeeSchedule.employee), as_dict=1) 
	ot_days = ot[0].ot_days if len(ot) > 0 else 0 

	day_off_diff = ""
	employee_number_of_days_off = employee.number_of_days_off

	if employee_number_of_days_off != (off_days + ot_days): # If has any discrepency
		if off_days > employee_number_of_days_off and not ot_days:
			day_off_diff = f"{off_days - employee_number_of_days_off} day(s) off scheduled more, please reduce by {off_days - employee_number_of_days_off}"
		elif off_days < employee_number_of_days_off and not ot_days:
			day_off_diff = f"{employee_number_of_days_off - off_days} day(s) off scheduled less, please schedule {employee_number_of_days_off - off_days} more day off"
		elif ot_days < employee_number_of_days_off and not off_days:
			day_off_diff = f"{employee_number_of_days_off - ot_days} day(s) off OT scheduled less, please schedule {employee_number_of_days_off - ot_days} more day off"
		elif ot_days > employee_number_of_days_off and not off_days:
			day_off_diff = f"{ot_days - employee_number_of_days_off} day(s) off OT scheduled more, please schedule {ot_days - employee_number_of_days_off} day off OT less"
		elif (ot_days and off_days):
			day_off_diff = f"{ot_days} day(s) OT and {off_days} day(s) off scheduled, actual day off should be {employee_number_of_days_off}"

	start_date_split = str(start_date).split("-")
	end_date_split = str(end_date).split("-")

	return {
		"monthweek": f"{monthname_dict[start_date_split[1]]} {start_date_split[2]} - {monthname_dict[end_date_split[1]]} {end_date_split[2]}",
		"month": start_date_split[1],
		"year": start_date_split[0],
		"off_days": off_days,
		"ot_days": ot_days,
		"day_off_difference": day_off_diff
	}

@frappe.whitelist()
def generate_checker():
	frappe.enqueue(check_roster_day_off, queue="long", timeout=4000)

@frappe.whitelist()
def get_day_off_issue_of_employees():
	"""
		Returns employees with missing day offs based on the current user's role.
		- Operations Manager: All employees
		- Project Manager: Employees under the project manager
		- Site Supervisor: Employees under the site supervisor
		- Shift Supervisor: Employees under the shift supervisor
	"""
	# Get current user details
	user, user_roles, user_employee = get_current_user_details()

	if not user_employee or not any(role in user_roles for role in ["Operations Manager", "Project Manager", "Site Supervisor", "Shift Supervisor"]):
		frappe.throw("No employee record linked to current user")
	else:
		#Get base employee list based on role
		if "Operations Manager" in user_roles:
			Employee = frappe.qb.DocType("Employee")
			employees = frappe.db.sql( frappe.qb.from_(Employee).select("*").where((Employee.status=="Active") & (Employee.shift_working == 1)), as_dict=1)
		elif "Project Manager" in user_roles:
			employees = get_project_manager_employees(user_employee.name)
		elif "Site Supervisor" in user_roles:
			employees = get_site_supervisor_employees(user_employee.name)
		elif "Shift Supervisor" in user_roles:
			employees = get_shift_supervisor_employees(user_employee.name)
		else:	
			return OrderedDict()
			
		roster_day_off_data = get_day_off_details_of_employees(employees)

		html_output = render_day_off_issues_html(roster_day_off_data)
		return html_output

def get_day_off_details_of_employees(employees):
	# Get all active employees
	# Validate their offs for next 2 months
	try:
		roster_day_off_data = []

		for employee in employees:
			comparison_dates = get_day_off_comparison_dates(employee.day_off_category)

			for period in comparison_dates:	# Always 2 iterations only because we have just two period for comparison	
				day_off_data = get_employee_day_off_comparison(employee, period["start_date"], period["end_date"])

				if day_off_data["day_off_difference"]:
					roster_day_off_data.append({
						"employee_id": employee.employee_id,
						"employee_name": employee.employee_name,
						"department": employee.department,
						"day_off_category": employee.day_off_category,
						"monthweek": day_off_data["monthweek"],
						"day_off_difference": day_off_data["day_off_difference"],
						"year": day_off_data["year"],
						"month": day_off_data["month"],
					})

		return roster_day_off_data
		
	except Exception:
		frappe.log_error(frappe.get_traceback())

def render_day_off_issues_html(roster_day_off_data):
	"""
	Day off issues : {employee_docname: {"employee_id": ..., "employee_name": ..., "monthweek": [...],"day_off_category": ...}}
	"""
	if len(roster_day_off_data) > 0:
		html = "<table class='table table-bordered'>"
		html += """<thead>
					<tr>
						<th>Employee ID</th>
						<th>Employee Name</th>
						<th>Month/Week</th>
						<th>Day off Category</th>
						<th>Day Off Difference</th>
						<th></th>
					</tr>
				</thead><tbody>"""
		
	
		for info in roster_day_off_data:
			html += f"""<tr>
							<td>{info["employee_id"]}</td>
							<td>{info["employee_name"]}</td>
							<td>{info["monthweek"]}</td>
							<td>{info["day_off_category"]}</td>
							<td>{info["day_off_difference"]}</td>
							<td><a class="btn btn-warning" target="_blank" href="/app/roster?main_view='roster'&sub_view='basic'&roster_type='basic'&department={info["department"]}&employee_id={info["employee_id"]}&month={info["month"]}&year={info["year"]}">Take Action</a></td>
						</tr>"""
		html += "</tbody></table>"
		return html

	html = """
		<div class="alert text-center" role="alert">
			<h5 class="mb-0">No Day Off Issues.Employees have correct number of days off. Great Job</h5>
		</div>
	"""
	return html

def get_project_manager_employees(user_employee):
	"""Employees in projects managed by current user"""
	return _get_employees_with_join(
		join_clause="""
			JOIN `tabOperations Shift` os ON e.shift = os.name
			JOIN `tabOperations Site` site ON os.site = site.name 
			JOIN `tabProject` p ON site.project = p.name
		""",
		where_clause="p.account_manager = %(user_employee)s",
		user_employee=user_employee
	)

def get_site_supervisor_employees(user_employee):
	"""Employees in sites managed by current user"""
	return _get_employees_with_join(
		join_clause="""
			JOIN `tabOperations Shift` os ON e.shift = os.name
			JOIN `tabOperations Site` site ON os.site = site.name
		""",
		where_clause="site.account_supervisor = %(user_employee)s",
		user_employee=user_employee
	)

def get_shift_supervisor_employees(user_employee):
	"""Employees in shifts managed by current user"""
	return _get_employees_with_join(
		join_clause="""
			JOIN `tabOperations Shift` os ON e.shift = os.name
			JOIN `tabOperations Shift Supervisor` oss 
				ON os.name = oss.parent AND oss.parenttype = 'Operations Shift'
		""",
		where_clause="oss.supervisor = %(user_employee)s",
		user_employee=user_employee
	)

def _get_employees_with_join(join_clause, where_clause, user_employee):
	"""Generic query builder for role-based employee fetching (returns employee records only)"""
	return frappe.db.sql(f"""
		SELECT 
			e.name,
			e.employee_name,
			e.day_off_category,
			e.number_of_days_off,
			e.employee_id,
			e.shift
		FROM `tabEmployee` e
		{join_clause}
		WHERE
			e.status = 'Active'
			AND e.shift_working = 1
			AND {where_clause}
	""", {"user_employee": user_employee}, as_dict=True)

