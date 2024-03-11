import frappe, erpnext
from frappe.utils import (
	cint, cstr, getdate, add_to_date, get_first_day
)
from frappe import _
import datetime
import calendar
from datetime import datetime
from one_fm.one_fm.doctype.hr_and_payroll_additional_settings.hr_and_payroll_additional_settings import (
	get_projects_not_configured_in_payroll_cycle_but_linked_in_employee,
	get_projects_configured_in_payroll_cycle
)

# imports all methods from payroll_entry
from hrms.payroll.doctype.payroll_entry.payroll_entry import *

class PayrollEntryOverride(PayrollEntry):
    @frappe.whitelist()
    def fill_employee_details(self):
        """
    	Method Override fill_employee_details in Payroll Entry
    	This Function fetches the employee details and updates the 'Employee Details' child table.

    	Returns:
    		list of active employees based on selected criteria
    		and for which salary structure exists.
    	"""
        self.set('employees', [])

        project_list = self.get_project_list_query()

        filters = self.make_filters()

        employees = get_employee_list(filters=filters, project_list=project_list, as_dict=True, ignore_match_conditions=True)

        # Custom method to fetch Bank Details and update employee list
        set_bank_details(self, employees)

        if not employees:
            error_msg = _("No employees found for the mentioned criteria:<br>Company: {0}<br> Currency: {1}<br>Payroll Payable Account: {2}").format(
                frappe.bold(self.company), frappe.bold(self.currency), frappe.bold(self.payroll_payable_account))
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

        for d in employees:
            self.append('employees', d)
        self.number_of_employees = len(self.employees)

    def get_project_list_query(self):
        project_list = False

        # Find payroll cycle start day
        payroll_start_day = str(get_start_date(self.start_date))

        # Find projects comes under the default payroll cycle
        if payroll_start_day == str(frappe.db.get_single_value('HR and Payroll Additional Settings', 'default_payroll_start_day')):
            # Find all projects linked to payroll cycles
            query = '''
                select
                    project
                from
                    `tabProject Payroll Cycle`
            '''
            projects = frappe.db.sql(query, as_dict=True)
            if not projects:
                projects = [{'project': ''}]

            # Get projects not configured in payroll cycle but linked in employee
            default_projects = get_projects_not_configured_in_payroll_cycle_but_linked_in_employee(', '.join(['"{}"'.format(project['project']) for project in projects]))
            if default_projects:
                project_list = [project.project for project in default_projects]

            # Find projects configured in default payroll cycle
            configured_projects = get_projects_configured_in_payroll_cycle(payroll_start_day)
            if configured_projects:
                if project_list:
                    project_list += ', '+configured_projects
                else:
                    project_list = configured_projects
        else:
            # Find projects configured in payroll start day
            project_list = get_projects_configured_in_payroll_cycle(payroll_start_day)

        return project_list

def auto_create_payroll_entry(payroll_date=None):
	"""
		Create Payroll Entry record with payroll cycle configured in HR and Payroll Additional Settings.
	"""

	if not payroll_date:
		payroll_date_day = frappe.db.get_single_value('HR and Payroll Additional Settings', 'payroll_date')
		# Calculate payroll date
		payroll_date = (datetime(getdate().year, getdate().month, cint(payroll_date_day))).strftime("%Y-%m-%d")

	# Find default from date and end date for payroll
	default_payroll_start_day = frappe.db.get_single_value('HR and Payroll Additional Settings', 'default_payroll_start_day')

	# Get Payroll cycle list from HR and Payroll Settings and itrate for payroll cycle
	query = '''
		select
			distinct payroll_start_day
		from
			`tabProject Payroll Cycle`
	'''
	data = frappe.db.sql(query, as_dict=True)

	payroll_start_day_list = [d['payroll_start_day'] for d in data]

	for payroll_start_day in payroll_start_day_list:
		# Find from date and end date for payroll
		start_date, end_date = get_payroll_start_end_date_by_start_day(payroll_date, payroll_start_day)

		# Create Payroll Entry
		create_monthly_payroll_entry(payroll_date, start_date, end_date)

	if default_payroll_start_day and default_payroll_start_day not in payroll_start_day_list:
		default_start_date, default_end_date = get_payroll_start_end_date_by_start_day(payroll_date, default_payroll_start_day)

		create_monthly_payroll_entry(payroll_date, default_start_date, default_end_date)

def get_payroll_start_end_date_by_start_day(payroll_date, start_day):
	if start_day == 'Month Start':
		start_day = 1
	if start_day == 'Month End':
		start_day = getdate(get_first_day(getdate(payroll_date))).day
	year = getdate(payroll_date).year - 1 if getdate(payroll_date).day < cint(start_day) and  getdate(payroll_date).month == 1 else getdate(payroll_date).year
	month = getdate(payroll_date).month if getdate(payroll_date).day >= cint(start_day) else getdate(payroll_date).month - 1
	date = datetime(year, month, cint(start_day)).strftime("%Y-%m-%d")
	if getdate(payroll_date) <= getdate(date):
		start_date = add_to_date(date, months=-1)
		end_date = add_to_date(date, days=-1)
	else:
		start_date = getdate(date)
		end_date = add_to_date(date, days=-1, months=1)
	return start_date, end_date

def create_monthly_payroll_entry(payroll_date, start_date, end_date):
	try:
		# payroll_type = ["Basic", "Over-Time"]
		payroll_type = ["Basic"]
		for types in payroll_type:
			payroll_entry = frappe.new_doc("Payroll Entry")
			payroll_entry.posting_date = getdate(payroll_date)
			payroll_entry.payroll_frequency = "Monthly"
			payroll_entry.exchange_rate = 0
			payroll_entry.payroll_payable_account = frappe.get_value("Company", erpnext.get_default_company(), "default_payroll_payable_account")
			payroll_entry.company = erpnext.get_default_company()
			payroll_entry.start_date = start_date
			payroll_entry.end_date = end_date
			payroll_entry.payroll_type = types
			payroll_entry.cost_center = frappe.get_value("Company", erpnext.get_default_company(), "cost_center")
			payroll_entry.save()
			# Fetch employees with the project filter
			payroll_entry.fill_employee_details()
			payroll_entry.save()
			payroll_entry.submit()
			frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), cstr(start_date)+' | '+cstr(end_date))

def get_start_date(date):
	if isinstance(date, str):
		date = datetime.strptime(date, '%Y-%m-%d')

	last_date_of_month = calendar.monthrange(date.year, date.month)[1]
	if date.day == 1:
		return 'Month Start'
	elif date.day == last_date_of_month:
		return 'Month End'
	else:
		return date.day

def get_employee_list(
    filters: frappe._dict,
    project_list=None,
    searchfield=None,
    search_string=None,
    fields: list[str] = None,
    as_dict=True,
    limit=None,
    offset=None,
    ignore_match_conditions=False
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
        project_list,
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
    project_list=None,
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

    print(sal_struct)
    print(project_list)

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
            & (Employee.project.isin(project_list))
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

@frappe.whitelist()
def set_bank_details(self, employee_details):
	"""This Funtion Sets the bank Details of an employee. The data is fetched from Bank Account Doctype.

	Args:
		employee_details (dict): Employee Details Child Table.

	Returns:
		employee_details ([dict): Sets the bank account IBAN code and Bank Code.
	"""
	employee_missing_detail = []
	missing_ssa = []
	employee_list = ', '.join(['"{}"'.format(employee.employee) for employee in employee_details])
	if employee_list:
		missing_ssa = frappe.db.sql("""
			SELECT employee from `tabEmployee` E
			WHERE E.status = 'Active'
			AND E.employment_type != 'Subcontractor'
			AND E.name NOT IN (
				SELECT employee from `tabSalary Structure Assignment` SE
			)
			""".format(employee_list), as_dict=True)

	for employee in employee_details:
		try:
			bank_account = frappe.db.get_value("Bank Account",{"party":employee.employee},["iban","bank", "bank_account_no"])
			salary_mode = frappe.db.get_value("Employee", {'name': employee.employee}, ["salary_mode"])
			if bank_account:
				iban, bank, bank_account_no = bank_account
			else:
				iban, bank, bank_account_no = None, None, None

			if not salary_mode:
				employee_missing_detail.append(frappe._dict(
				{'employee':employee.employee, 'salary_mode':'', 'issue':'No salary mode'}))
			elif(salary_mode=='Bank' and bank is None):
				employee_missing_detail.append(frappe._dict(
					{'employee':employee.employee, 'salary_mode':salary_mode, 'issue':'No bank account'}))
			elif(salary_mode=="Bank" and bank_account_no is None):
				employee_missing_detail.append(frappe._dict(
					{'employee':employee.employee, 'salary_mode':salary_mode, 'issue':'No account no.'}))
			employee.salary_mode = salary_mode
			employee.iban_number = iban or bank_account_no
			bank_code = frappe.db.get_value("Bank", {'name': bank}, ["bank_code"])
			employee.bank_code = bank_code
		except Exception as e:
			frappe.log_error(str(e), 'Payroll Entry')
			frappe.throw(str(e))

	if len(missing_ssa) > 0:
		for e in missing_ssa:
			employee_missing_detail.append(frappe._dict(
				{'employee':e.employee, 'salary_mode':'', 'issue':'No Salary Structure Assignment'}))

	# check for missing details, log and report
	if(len(employee_missing_detail)):
		missing_detail = []
		for i in employee_missing_detail:
			missing_detail.append({
				'employee':i.employee,
				'salary_mode':i.salary_mode,
				'issue': i.issue
			})

		if frappe.db.exists("Missing Payroll Information",{'payroll_entry': self.name}):
			fetch_mpi = frappe.db.sql(f"""
				SELECT name FROM `tabMissing Payroll Information`
				WHERE payroll_entry="{self.name}"
				ORDER BY modified DESC
				LIMIT 1
			;""", as_dict=1)
			mpi = frappe.get_doc('Missing Payroll Information', fetch_mpi[0].name)
			# delete previous table data
			frappe.db.sql(f"""
				DELETE FROM `tabMissing Payroll Information Detail`
				WHERE parent="{mpi.name}"
			;""")
			mpi.reload()
			for i in missing_detail:
				mpi.append('missing_payroll_information_detail', i)
			mpi.save(ignore_permissions=True)
			frappe.db.commit()
		else:
			mpi = frappe.get_doc({
				'doctype':"Missing Payroll Information",
				'payroll_entry': self.name,
				'missing_payroll_information_detail':missing_detail
			}).insert(ignore_permissions=True)
			frappe.db.commit()

		# generate html template to show to user screen
		message = frappe.render_template(
			'one_fm/api/doc_methods/templates/payroll/bank_issue.html',
			context={'employees':employee_missing_detail, 'mpi':mpi}
		)
		frappe.throw(_(message))
	return employee_details
