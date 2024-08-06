from datetime import datetime

import frappe
from frappe import _
from frappe.utils import (
	add_to_date,
	cint,
	getdate,
)
from frappe.query_builder.functions import Coalesce, Count

from hrms.payroll.doctype.payroll_entry.payroll_entry import ( PayrollEntry, get_employee_list, get_salary_structure, remove_payrolled_employees, 
															  set_fields_to_select, set_searchfield, set_match_conditions)



class PayrollEntryOverride(PayrollEntry):
	@frappe.whitelist()
	def fill_employee_details(self):
		filters = self.make_filters()
		employees = get_employee_list(filters=filters, as_dict=True, ignore_match_conditions=True)
		self.set("employees", [])

		if not employees:
			error_msg = _(
				"No employees found for the mentioned criteria:<br>Company: {0}<br> Currency: {1}<br>Payroll Payable Account: {2}"
			).format(
				frappe.bold(self.company),
				frappe.bold(self.currency),
				frappe.bold(self.payroll_payable_account),
			)
			if self.branch:
				error_msg += "<br>" + _("Branch: {0}").format(frappe.bold(self.branch))
			if self.department:
				error_msg += "<br>" + _("Department: {0}").format(frappe.bold(self.department))
			if self.designation:
				error_msg += "<br>" + _("Designation: {0}").format(frappe.bold(self.designation))
			if self.start_date:
				error_msg += "<br>" + _("Start date: {0}").format(frappe.bold(self.start_date))
			if self.end_date:
				error_msg += "<br>" + _("End date: {0}").format(frappe.bold(self.end_date))
			frappe.throw(error_msg, title=_("No employees found"))

		self.set("employees", employees)
		self.number_of_employees = len(self.employees)

		return self.get_employees_with_unmarked_attendance()


	def make_filters(self):
		project = None

		if self.custom_project_configuration == "Specific Project":
			project = (self.custom_project_filter,)
		elif self.custom_project_configuration == "All External Projects":
			project = frappe.get_all("Project", {"project_type": "External", "status": "Open"}, "name", as_list=1)

		filters = frappe._dict(
			company=self.company,
			branch=self.branch,
			department=self.department,
			designation=self.designation,
			grade=self.grade,
			currency=self.currency,
			start_date=self.start_date,
			end_date=self.end_date,
			payroll_payable_account=self.payroll_payable_account,
			salary_slip_based_on_timesheet=self.salary_slip_based_on_timesheet,
			project=project,
			custom_payroll_cycle_start_date=getdate(self.start_date).day,
			custom_payroll_cycle_end_date=getdate(self.end_date).day,
			payroll_type=self.payroll_type
		)

		if not self.salary_slip_based_on_timesheet:
			filters.update(dict(payroll_frequency=self.payroll_frequency))

		return filters

@frappe.whitelist()
def get_start_end_dates(payroll_frequency, start_date=None, company=None):
	"""Returns dict of start and end dates for given payroll frequency based on start_date"""
	start_date, end_date = None, None
	if payroll_frequency == "Monthly":
		#fetch Payroll date's day
		date = frappe.db.get_single_value('HR and Payroll Additional Settings', 'payroll_date')
		year = getdate().year - 1 if getdate().day < cint(date) and  getdate().month == 1 else getdate().year
		month = getdate().month if getdate().day >= cint(date) else getdate().month - 1

		#calculate Payroll date, start and end date.
		payroll_date = datetime(year, month, cint(date)).strftime("%Y-%m-%d")
		start_date = add_to_date(payroll_date, months=-1)
		end_date = add_to_date(payroll_date, days=-1)

	return frappe._dict({"start_date": start_date, "end_date": end_date})


def get_employee_list(
	filters: frappe._dict,
	searchfield=None,
	search_string=None,
	fields: list[str] | None = None,
	as_dict=True,
	limit=None,
	offset=None,
	ignore_match_conditions=False,
) -> list:
	sal_struct = get_salary_structure(
		filters.company,
		filters.currency,
		filters.salary_slip_based_on_timesheet,
		filters.payroll_frequency,
	)

	if not sal_struct:
		return []

	emp_list = get_filtered_employees(
		sal_struct,
		filters,
		searchfield,
		search_string,
		fields,
		as_dict=as_dict,
		limit=limit,
		offset=offset,
		ignore_match_conditions=ignore_match_conditions,
	)

	if as_dict:
		employees_to_check = {emp.employee: emp for emp in emp_list}
	else:
		employees_to_check = {emp[0]: emp for emp in emp_list}

	return remove_payrolled_employees(employees_to_check, filters.start_date, filters.end_date)



def get_filtered_employees(
	sal_struct,
	filters,
	searchfield=None,
	search_string=None,
	fields=None,
	as_dict=False,
	limit=None,
	offset=None,
	ignore_match_conditions=False,
) -> list:
	SalaryStructureAssignment = frappe.qb.DocType("Salary Structure Assignment")
	Employee = frappe.qb.DocType("Employee")
	Attendance = frappe.qb.DocType("Attendance")

	query = (
		frappe.qb.from_(Employee)
		.join(SalaryStructureAssignment)
		.on(Employee.name == SalaryStructureAssignment.employee)
		.where(
			(SalaryStructureAssignment.docstatus == 1)
			& (Employee.status != "Inactive")
			& (Employee.company == filters.company)
			& ((Employee.date_of_joining <= filters.end_date) | (Employee.date_of_joining.isnull()))
			& ((Employee.relieving_date >= filters.start_date) | (Employee.relieving_date.isnull()))
			& (SalaryStructureAssignment.salary_structure.isin(sal_struct))
			& (SalaryStructureAssignment.payroll_payable_account == filters.payroll_payable_account)
			& (filters.end_date >= SalaryStructureAssignment.from_date)
			& (Employee.employee.notin(
				frappe.qb.from_(Attendance)
				.select(Attendance.employee)
				.where(
					(Attendance.attendance_date[filters.start_date:filters.end_date])
				    & (Attendance.status == "On Hold")
					& (Attendance.roster_type == filters.payroll_type)
		   		)
			))
		)
	)

	query = set_fields_to_select(query, fields)
	query = set_searchfield(query, searchfield, search_string, qb_object=Employee)
	query = set_filter_conditions(query, filters, qb_object=Employee)

	if not ignore_match_conditions:
		query = set_match_conditions(query=query, qb_object=Employee)

	if limit:
		query = query.limit(limit)

	if offset:
		query = query.offset(offset)

	return query.run(as_dict=as_dict)



def set_filter_conditions(query, filters, qb_object):
	"""Append optional filters to employee query"""
	if filters.get("employees"):
		query = query.where(qb_object.name.notin(filters.get("employees")))

	if filters.get("project"):
		query = query.where(qb_object.project.isin(filters.get("project")))
	

	for fltr_key in ["branch", "department", "designation", "grade", "custom_payroll_cycle_start_date", "custom_payroll_cycle_end_date"]:
		if filters.get(fltr_key):
			query = query.where(qb_object[fltr_key] == filters[fltr_key])
	return query