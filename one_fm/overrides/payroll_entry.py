from datetime import datetime

import frappe
from frappe import _
from frappe.utils import (
	add_to_date,
	cint,
	getdate,
	get_link_to_form,
	flt
)
from hrms.payroll.doctype.payroll_entry.payroll_entry import ( PayrollEntry, get_employee_list, get_salary_structure, remove_payrolled_employees, 
															  set_fields_to_select, set_searchfield, set_match_conditions)



class PayrollEntryOverride(PayrollEntry):
	def get_salary_component_total(
		self,
		component_type=None,
		employee_wise_accounting_enabled=False,
	):
		salary_components = self.get_salary_components(component_type)
		if salary_components:
			component_dict = {}

			for item in salary_components:
				if not self.should_add_component_to_accrual_jv(component_type, item):
					continue
				
				department = frappe.db.get_value("Employee", item.employee, "department")
				employee_cost_centers = self.get_payroll_cost_centers_for_employee(
					item.employee, item.salary_structure
				)
				employee_advance = self.get_advance_deduction(component_type, item)

				for cost_center, percentage in employee_cost_centers.items():
					amount_against_cost_center = flt(item.amount) * percentage / 100

					if employee_advance:
						self.add_advance_deduction_entry(
							item, amount_against_cost_center, cost_center, employee_advance
						)
					else:
						key = (item.salary_component, cost_center, department)
						component_dict[key] = component_dict.get(key, 0) + amount_against_cost_center

					if employee_wise_accounting_enabled:
						self.set_employee_based_payroll_payable_entries(
							component_type, item.employee, amount_against_cost_center
						)
					
			account_details = self.get_account(component_dict=component_dict)

			return account_details

	def get_account(self, component_dict=None):
		account_dict = {}
		for key, amount in component_dict.items():
			component, cost_center, department = key
			account = self.get_salary_component_account(component, department)
			accounting_key = (account, cost_center)

			account_dict[accounting_key] = account_dict.get(accounting_key, 0) + amount

		return account_dict

	def get_salary_component_account(self, salary_component, department):
		account = frappe.db.get_value("Salary Component Account", 
			{"parent": salary_component, "company": self.company, "custom_department": department},
			"account", cache=True
		)
		if not account:
			account = frappe.db.get_value("Salary Component Account", 
				{"parent": salary_component, "company": self.company},
				"account", cache=True
			)	

		if not account:
			frappe.throw(
				_("Please set account in Salary Component {0}").format(
					get_link_to_form("Salary Component", salary_component)
				)
			)

		return account

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
			if self.payroll_type:
				error_msg += "<br>" + _("Payroll type: {0}").format(frappe.bold(self.payroll_type))
				
			frappe.throw(error_msg, title=_("No employees found"))
			

		# Custom method to fetch Bank Details and update employee list
		set_bank_details(self, employees)

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
			payroll_type=self.payroll_type,
			payroll_entry=self.name
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
		date = frappe.db.get_single_value("HR and Payroll Additional Settings", "payroll_date")
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

	set_on_hold_employees(
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

	attendance_sub_query = None
	if filters.payroll_type == "Basic":
		attendance_sub_query = Employee.employee.notin(
			frappe.qb.from_(Attendance)
			.select(Attendance.employee)
			.where(
				(Attendance.attendance_date[filters.start_date:filters.end_date])
				& (Attendance.status == "On Hold")
				& (Attendance.roster_type == filters.payroll_type)
			)
		)
	elif filters.payroll_type == "Over-Time":
		attendance_sub_query = Employee.employee.isin(
			frappe.qb.from_(Attendance)
			.select(Attendance.employee)
			.where(
				(Attendance.attendance_date[filters.start_date:filters.end_date])
				& (Attendance.status != "On Hold")
				& (Attendance.roster_type == filters.payroll_type)
			)
		)

	query = (
	frappe.qb.from_(Employee)
	.join(SalaryStructureAssignment)
	.on(Employee.name == SalaryStructureAssignment.employee)
	.where(
		(SalaryStructureAssignment.docstatus == 1)
		& (Employee.status.isin(["Active", "Vacation"]))
		& (Employee.company == filters.company)
		& ((Employee.date_of_joining <= filters.end_date) | (Employee.date_of_joining.isnull()))
		& ((Employee.relieving_date >= filters.start_date) | (Employee.relieving_date.isnull()))
		& (SalaryStructureAssignment.salary_structure.isin(sal_struct))
		& (SalaryStructureAssignment.payroll_payable_account == filters.payroll_payable_account)
		& (filters.end_date >= SalaryStructureAssignment.from_date)
		& (attendance_sub_query)
	))

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


def set_bank_details(self, employee_details):
	"""This Funtion Sets the bank Details of an employee. The data is fetched from Bank Account Doctype.

	Args:
		employee_details (dict): Employee Details Child Table.

	Returns:
		employee_details ([dict): Sets the bank account IBAN code and Bank Code.
	"""
	employee_missing_detail = []

	for employee in employee_details:
		try:
			bank_account = frappe.db.get_value("Bank Account",{"party":employee.employee},["iban","bank", "bank_account_no"])
			salary_mode = frappe.db.get_value("Employee", {"name": employee.employee}, ["salary_mode"])
			if bank_account:
				iban, bank, bank_account_no = bank_account
			else:
				iban, bank, bank_account_no = None, None, None

			if not salary_mode:
				employee_missing_detail.append(frappe._dict(
				{"employee":employee.employee, "salary_mode":"", "issue":"No salary mode"}))
			elif(salary_mode=="Bank" and bank is None):
				employee_missing_detail.append(frappe._dict(
					{"employee":employee.employee, "salary_mode":salary_mode, "issue":"No bank account"}))
			elif(salary_mode=="Bank" and bank_account_no is None):
				employee_missing_detail.append(frappe._dict(
					{"employee":employee.employee, "salary_mode":salary_mode, "issue":"No account no."}))
			employee.salary_mode = salary_mode
			employee.iban_number = iban or bank_account_no
			bank_code = frappe.db.get_value("Bank", {"name": bank}, ["bank_code"])
			employee.bank_code = bank_code
		except Exception as e:
			frappe.log_error(str(e), "Payroll Entry")
			frappe.throw(str(e))

	# check for missing details, log and report
	if len(employee_missing_detail) > 0:
		missing_detail = []
		for i in employee_missing_detail:
			missing_detail.append({
				"employee":i.employee,
				"salary_mode":i.salary_mode,
				"issue": i.issue
			})

		mpi_exists = frappe.db.exists("Missing Payroll Information",{"payroll_entry": self.name})
		
		if mpi_exists:
			mpi = frappe.get_doc("Missing Payroll Information", mpi_exists)

			# delete previous table data
			# frappe.db.sql(f"""
			# 	DELETE FROM `tabMissing Payroll Information Detail`
			# 	WHERE parent="{mpi.name}"
			# ;""")
			# mpi.reload()
			for i in missing_detail:
				mpi.append("missing_payroll_information_detail", i)
			mpi.save(ignore_permissions=True)
			frappe.db.commit()
		else:
			mpi = frappe.get_doc({
				"doctype":"Missing Payroll Information",
				"payroll_entry": self.name,
				"missing_payroll_information_detail":missing_detail
			}).insert(ignore_permissions=True)
			frappe.db.commit()

		# generate html template to show to user screen
		message = frappe.render_template(
			"one_fm/api/doc_methods/templates/payroll/bank_issue.html",
			context={"employees":employee_missing_detail, "mpi":mpi}
		)
		frappe.throw(_(message))
	return employee_details


@frappe.whitelist()
def set_on_hold_employees(
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

	attendance_sub_query = Employee.employee.isin(
		frappe.qb.from_(Attendance)
		.select(Attendance.employee)
		.where(
			(Attendance.attendance_date[filters.start_date:filters.end_date])
			& (Attendance.status == "On Hold")
			& (Attendance.roster_type == filters.payroll_type)
		)
	)

	query = (
	frappe.qb.from_(Employee)
	.join(SalaryStructureAssignment)
	.on(Employee.name == SalaryStructureAssignment.employee)
	.where(
		(SalaryStructureAssignment.docstatus == 1)
		& (Employee.status.isin(["Active", "Vacation"]))
		& (Employee.company == filters.company)
		& ((Employee.date_of_joining <= filters.end_date) | (Employee.date_of_joining.isnull()))
		& ((Employee.relieving_date >= filters.start_date) | (Employee.relieving_date.isnull()))
		& (SalaryStructureAssignment.salary_structure.isin(sal_struct))
		& (SalaryStructureAssignment.payroll_payable_account == filters.payroll_payable_account)
		& (filters.end_date >= SalaryStructureAssignment.from_date)
		& (attendance_sub_query)
	))

	query = set_fields_to_select(query, fields)
	query = set_searchfield(query, searchfield, search_string, qb_object=Employee)
	query = set_filter_conditions(query, filters, qb_object=Employee)

	if not ignore_match_conditions:
		query = set_match_conditions(query=query, qb_object=Employee)

	if limit:
		query = query.limit(limit)

	if offset:
		query = query.offset(offset)

	employees = query.run(as_dict=as_dict)

	if len(employees) > 0:
		mpi_exists = frappe.db.exists("Missing Payroll Information", { "payroll_entry": filters.payroll_entry})
		missing_payroll_info = []
		for employee in employees:
			missing_payroll_info.append({
				"employee": employee.employee,
				"salary_mode": "N/A",
				"issue": "On-Hold attendance records"
			})

		if mpi_exists:
			mpi = frappe.get_doc("Missing Payroll Information", mpi_exists)
			for info in missing_payroll_info:
				mpi.append("missing_payroll_information_detail", info)
			mpi.save(ignore_permissions=True)

		else:
			mpi = frappe.get_doc({
				"doctype":"Missing Payroll Information",
				"payroll_entry": filters.payroll_entry,
				"missing_payroll_information_detail": missing_payroll_info
			}).insert(ignore_permissions=True)
		
		frappe.db.commit()