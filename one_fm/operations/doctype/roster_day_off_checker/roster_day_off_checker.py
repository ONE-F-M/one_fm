# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

from collections import OrderedDict
import frappe
from datetime import date, timedelta, datetime
from frappe.utils import (
    get_first_day, get_last_day, getdate, add_days, add_months, nowdate, date_diff
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

def get_leave_dates_by_employee():
    today = getdate(nowdate())
    
    # First of current month
    current_month_start = get_first_day(today)

    # last day of next month
    next_month_end = get_last_day(add_months(today, 1))

    results = frappe.db.sql("""
        SELECT employee, from_date, to_date
        FROM `tabLeave Application`
        WHERE leave_type IN ('Annual Leave', 'Leave Without Pay')
		AND status = 'Approved'
        AND (
            (from_date BETWEEN %(start_date)s AND %(end_date)s)
            OR
            (to_date BETWEEN %(start_date)s AND %(end_date)s)
        )
    """, { "start_date": current_month_start, "end_date": next_month_end }, as_dict=True)

    leave_days_by_employee = {}

    for row in results:
        employee = row.employee
        from_date = getdate(row.from_date)
        to_date = getdate(row.to_date)
        
        days_count = date_diff(to_date, from_date) + 1  # inclusive
        leave_days = [(add_days(from_date, i)) for i in range(days_count)]

        if employee not in leave_days_by_employee:
            leave_days_by_employee[employee] = set()

        leave_days_by_employee[employee].update(leave_days)

    # Convert sets to sorted lists
    for emp in leave_days_by_employee:
        leave_days_by_employee[emp] = sorted(list(leave_days_by_employee[emp]))

    return leave_days_by_employee

def get_day_off_comparison_dates(employee, total_leave_dates):
    today = getdate()
    comparison_periods = []
    total_leave_dates = [] if total_leave_dates is None else total_leave_dates

    # Fallbacks for null dates
    joining_date = employee.date_of_joining or date.min
    relieving_date = employee.relieving_date or date.max

    def add_period(start, end, total_days):
        # Clamp dates within employee tenure
        start_date = max(start, joining_date)
        end_date = min(end, relieving_date)

        if start_date > end_date:
            return

        working_dates = []
        leave_dates_in_period = []
		
        current = start_date
        while current <= end_date:
            if current in total_leave_dates:
                leave_dates_in_period.append(current)
            else:
                working_dates.append(current)
            current += timedelta(days=1)

        # Calculate proportional days off
        calculated_days_off = (len(working_dates) / total_days) * employee.number_of_days_off

        comparison_periods.append({
            "start_date": start_date,
            "end_date": end_date,
            "calculated_number_of_days_off": round(calculated_days_off),
            "leave_dates": leave_dates_in_period,
            "working_dates": working_dates
        })

    if employee.day_off_category == "Monthly":
        # Current month
        add_period(get_first_day(today), get_last_day(today), 30)

        # Next month
        next_month = add_months(today, 1)
        add_period(get_first_day(next_month), get_last_day(next_month), 30)

    elif employee.day_off_category == "Weekly":
        # First week (starting from tomorrow)
        week1_start = add_days(today, 1)
        week1_end = add_days(week1_start, 6)
        add_period(week1_start, week1_end, 7)

        # Second week
        week2_start = add_days(week1_end, 1)
        week2_end = add_days(week2_start, 6)
        add_period(week2_start, week2_end, 7)

    return comparison_periods

def split_date_range_for_past_and_future(start_date, end_date):
    """
    Splits the input date range into 'past' and 'future' based on today's date.
    
    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).

    Returns:
        dict: {
            "past": {"start_date": ..., "end_date": ...} or None,
            "future": {"start_date": ..., "end_date": ...} or None
        }
    """
    start = getdate(start_date)
    end = getdate(end_date)
    today = getdate(nowdate())

    result = {
        "past": None,
        "future": None
    }

    if start < today:
        past_end = min(end, add_days(today, -1))
        if past_end >= start:
            result["past"] = {
                "start_date": start,
                "end_date": past_end
            }

    if end >= today:
        future_start = max(start, today)
        result["future"] = {
            "start_date": future_start,
            "end_date": end
        }

    return result

def check_roster_day_off():
	# Get all active employees
	# Validate their offs for next 2 months/weeks based on their Day Off Category
	# If discrepency, create record with each employee info
	try:
		today = getdate()

		Employee = frappe.qb.DocType("Employee")
		employees = frappe.db.sql(frappe.qb.from_(Employee).select("*").where((Employee.status=="Active") & (Employee.shift_working == 1) & ((Employee.relieving_date.isnull()) | (Employee.relieving_date > today))), as_dict=1)

		leave_dates_by_employee = get_leave_dates_by_employee()

		for employee in employees:
			employee_leave_dates = leave_dates_by_employee.get(employee.name)
			comparison_dates = get_day_off_comparison_dates(employee, employee_leave_dates)

			site_supervisor = frappe.db.get_value("Operations Site", employee.site, "account_supervisor")
			shift_supervisor = get_shift_supervisor(employee.shift)
			project_manager = frappe.db.get_value("Project", employee.project, "account_manager")

			for period in comparison_dates:	# Always 2 iterations only because we have just two period for comparison
				day_off_data = get_employee_day_off_comparison(employee, period["start_date"], period["end_date"], period["calculated_number_of_days_off"], period["working_dates"])

				if day_off_data["day_off_difference"]:
					duration = day_off_data["monthweek"]

					yesterday_repeat_count = frappe.db.get_value(
						"Roster Day Off Checker",
						{
							"employee": employee.name,
							"monthweek": duration,
							"date": add_days(today, -1),
							"creation": ["between", [add_days(nowdate(), -1), nowdate()]],
						},
						["repeat_count"]
					)

					# Delete exising for target duration against employee
					frappe.delete_doc_if_exists("Roster Day Off Checker", f"OPR-RDOC-{employee.name}-{duration}")

					day_off_checker = frappe.new_doc("Roster Day Off Checker")
					day_off_checker.date = today
					day_off_checker.monthweek = duration
					day_off_checker.repeat_count = (yesterday_repeat_count or 0) + 1
					day_off_checker.employee = employee.name
					day_off_checker.shift_supervisor = shift_supervisor
					day_off_checker.site_supervisor = site_supervisor
					day_off_checker.project_manager = project_manager
					day_off_checker.required_number_of_days_off = period["calculated_number_of_days_off"] if period["calculated_number_of_days_off"] != employee.number_of_days_off else ''
					day_off_checker.rostered_days_off = day_off_data["rostered_off_days"]
					day_off_checker.rostered_day_off_ot = day_off_data["rostered_ot_days"]
					day_off_checker.day_off_taken = day_off_data["availed_off_days"]
					day_off_checker.worked_day_off_ot = day_off_data["availed_ot_days"]
					day_off_checker.day_off_difference = day_off_data["day_off_difference"]
					day_off_checker.insert(ignore_permissions=1)

		frappe.db.commit()


	except Exception:
		frappe.log_error(frappe.get_traceback())

def get_employee_day_off_comparison(employee, start_date, end_date, calculated_day_offs = 0, working_dates = []):
	date_ranges = split_date_range_for_past_and_future(start_date, end_date)

	off_days = 0
	ot_days = 0

	rostered_off_days = 0
	rostered_ot_days = 0

	availed_off_days = 0
	availed_ot_days = 0

	if date_ranges["past"]:
		"""
		Calculate day offs and day off ot using employee's attendance within the date range
		"""
		Attendance = frappe.qb.DocType("Attendance")

		attendance_start_date = date_ranges["past"]["start_date"]
		attendance_end_date = date_ranges["past"]["end_date"]

		# QB conditions
		conditions = (
			(Attendance.employee == employee.name) &
			(Attendance.attendance_date.between(attendance_start_date, attendance_end_date))
		)

		if working_dates:
			conditions &= Attendance.attendance_date.isin(working_dates)

		# Calculate no of off days
		od = frappe.db.sql(frappe.qb.from_(Attendance)
			.select(Count("name").as_("off_days"))
			.where(conditions & (Attendance.status == "Day Off") & (Attendance.day_off_ot == 0) & (Attendance.docstatus == 1))
			.groupby(Attendance.employee),
		as_dict=1)
		attendance_off_days = (od[0].off_days if len(od) > 0 else 0)
		off_days = off_days + attendance_off_days
		availed_off_days = attendance_off_days

		# Calculate no of ot days
		ot = frappe.db.sql( frappe.qb.from_(Attendance)
			.select(Count("name").as_("ot_days"))
			.where(conditions & (Attendance.day_off_ot == 1))
			.groupby(Attendance.employee), as_dict=1)
		attendance_ot_days = (ot[0].ot_days if len(ot) > 0 else 0)
		ot_days = ot_days + attendance_ot_days
		availed_ot_days = attendance_ot_days

	if date_ranges["future"]:
		"""
		Calculate day offs and day off ot using employee schedules within the date range including today
		"""
		EmployeeSchedule = frappe.qb.DocType("Employee Schedule")

		schedule_start_date = date_ranges["future"]["start_date"]
		schedule_end_date = date_ranges["future"]["end_date"]

		# QB conditions
		conditions = (
			(EmployeeSchedule.employee == employee.name) &
			(EmployeeSchedule.date[schedule_start_date:schedule_end_date])
		)

		if working_dates:
			conditions &= EmployeeSchedule.date.isin(working_dates)

		# Calculate no of off days
		od = frappe.db.sql(frappe.qb.from_(EmployeeSchedule)
			.select(Count("name").as_("off_days"))
			.where(conditions & (EmployeeSchedule.employee_availability == "Day Off") & (EmployeeSchedule.day_off_ot == 0))
			.groupby(EmployeeSchedule.employee),
		as_dict=1)
		schedule_off_days = (od[0].off_days if len(od) > 0 else 0)
		off_days = off_days + schedule_off_days
		rostered_off_days = schedule_off_days

		# Calculate no of ot days
		ot = frappe.db.sql( frappe.qb.from_(EmployeeSchedule)
			.select(Count("name").as_("ot_days"))
			.where(conditions & (EmployeeSchedule.day_off_ot == 1))
			.groupby(EmployeeSchedule.employee), as_dict=1)
		schedule_ot_days = (ot[0].ot_days if len(ot) > 0 else 0)
		ot_days = ot_days + schedule_ot_days
		rostered_ot_days = schedule_ot_days

	day_off_diff = ""
	employee_number_of_days_off = calculated_day_offs

	if employee_number_of_days_off != (off_days + ot_days): # If has any discrepency
		if off_days > employee_number_of_days_off and not ot_days:
			day_off_diff = f"{off_days - employee_number_of_days_off} day(s) off scheduled more, please reduce by {off_days - employee_number_of_days_off} day(s) off"
		elif off_days < employee_number_of_days_off and not ot_days:
			day_off_diff = f"{employee_number_of_days_off - off_days} day(s) off scheduled less, please schedule {employee_number_of_days_off - off_days} more day(s) off"
		elif ot_days < employee_number_of_days_off and not off_days:
			day_off_diff = f"{employee_number_of_days_off - ot_days} day(s) off OT scheduled less, please schedule {employee_number_of_days_off - ot_days} more day(s) off OT"
		elif ot_days > employee_number_of_days_off and not off_days:
			day_off_diff = f"{ot_days - employee_number_of_days_off} day(s) off OT scheduled more, please reduce by {ot_days - employee_number_of_days_off} day(s) off OT"
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
		"rostered_off_days": rostered_off_days,
		"rostered_ot_days": rostered_ot_days,
		"availed_off_days": availed_off_days,
		"availed_ot_days": availed_ot_days,
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
		leave_dates_by_employee = get_leave_dates_by_employee()
		roster_day_off_data = []

		for employee in employees:
			employee_leave_dates = leave_dates_by_employee.get(employee.name)
			comparison_dates = get_day_off_comparison_dates(employee, employee_leave_dates)

			for period in comparison_dates:	# Always 2 iterations only because we have just two period for comparison
				day_off_data = get_employee_day_off_comparison(employee, period["start_date"], period["end_date"], period["calculated_number_of_days_off"], period["working_dates"])

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
						"role":employee.custom_operations_role_allocation,
						"shift":employee.shift
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
							<td><a class="btn btn-warning" target="_blank" href="/app/roster?main_view='roster'&sub_view='basic'&roster_type='basic'&department={info["department"]}&employee_id={info["employee_id"]}&operations_role={info["role"]}&month={info["month"]}&year={info["year"]}">Take Action</a></td>
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
			e.shift,
		    e.custom_operations_role_allocation
		FROM `tabEmployee` e
		{join_clause}
		WHERE
			e.status = 'Active'
			AND e.shift_working = 1
			AND {where_clause}
	""", {"user_employee": user_employee}, as_dict=True)
