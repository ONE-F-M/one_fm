import frappe, erpnext, json
from dateutil.relativedelta import relativedelta
from frappe.utils import (
	cint, cstr, flt, nowdate, add_days, getdate, fmt_money, add_to_date, DATE_FORMAT, date_diff,
	get_first_day, get_last_day, get_link_to_form
)
from frappe import _
from frappe.utils.pdf import get_pdf
import openpyxl as xl
import time
import datetime
import calendar
from datetime import datetime, timedelta
from copy import copy
from pathlib import Path
from hrms.payroll.doctype.payroll_entry.payroll_entry import (
	get_filter_condition, get_joining_relieving_condition, remove_payrolled_employees, get_sal_struct
)
from one_fm.one_fm.doctype.hr_and_payroll_additional_settings.hr_and_payroll_additional_settings import get_projects_not_configured_in_payroll_cycle_but_linked_in_employee
from itertools import groupby
from operator import itemgetter
from one_fm.processor import sendemail
from one_fm.overrides.leave_application import close_leaves
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from one_fm.utils import production_domain

def validate_employee_attendance(self):
	employees_to_mark_attendance = []
	days_in_payroll, days_holiday, days_attendance_marked = 0, 0, 0

	for employee_detail in self.employees:
		employee_joining_date = frappe.db.get_value(
			"Employee", employee_detail.employee, "date_of_joining"
		)
		start_date = self.start_date
		if employee_joining_date > getdate(self.start_date):
			start_date = employee_joining_date

		days_holiday = self.get_count_holidays_of_employee(employee_detail.employee, start_date)
		days_attendance_marked, days_scheduled = self.get_count_employee_attendance(employee_detail.employee, start_date)

		days_in_payroll = date_diff(self.end_date, self.start_date) + 1
		if days_in_payroll != (days_holiday + days_attendance_marked) != (days_holiday + days_scheduled) :
			employees_to_mark_attendance.append({
				"employee": employee_detail.employee,
				"employee_name": employee_detail.employee_name
				})
	return employees_to_mark_attendance

def get_count_holidays_of_employee(self, employee, start_date):
	holiday_list = get_holiday_list_for_employee(employee)
	holidays = 0
	if holiday_list:
		days = frappe.db.sql("""select count(*) from `tabEmployee Schedule` where
			employee=%s and date between %s and %s and employee_availability in ("Day Off", "Sick Leave", "Annual Leave", "Emergency Leave") """, (employee,
			start_date, self.end_date))
		if days and days[0][0]:
			holidays = days[0][0]
	return holidays

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
	# Find projects comes under the same payroll cycle
	if str(get_start_date(self.start_date)) == str(frappe.db.get_single_value('HR and Payroll Additional Settings', 'default_payroll_start_day')):
		query = '''
			select
				project
			from
				`tabProject Payroll Cycle`
		'''
		projects = frappe.db.sql(query, as_dict=True)
		default_projects = get_projects_not_configured_in_payroll_cycle_but_linked_in_employee(', '.join(['"{}"'.format(project.project) for project in projects]))
		project_list = ', '.join(['"{}"'.format(project.project) for project in default_projects])
	else:
		query = '''
			select
				project
			from
				`tabProject Payroll Cycle`
			where
				payroll_start_day = '{0}'
		'''
		start_day = get_start_date(self.start_date)
		projects = frappe.db.sql(query.format(start_day), as_dict=True)
		project_list = ', '.join(['"{}"'.format(project.project) for project in projects])

	employees = get_emp_list(self, project_list)

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
	if self.validate_attendance:
		return self.validate_employee_attendance()

@frappe.whitelist()
def get_emp_list(self, project_list=False):
	"""
		Returns list of active employees based on selected criteria
		and for which salary structure exists
	"""
	self.check_mandatory()
	filters = self.make_filters()
	cond = get_filter_condition(filters)
	cond += get_joining_relieving_condition(self.start_date, self.end_date)

	condition = ""
	if self.payroll_frequency:
		condition = """and payroll_frequency = '%(payroll_frequency)s'""" % {
			"payroll_frequency": self.payroll_frequency
		}

	sal_struct = get_sal_struct(
		self.company, self.currency, self.salary_slip_based_on_timesheet, condition
	)
	if sal_struct:
		cond += "and t2.salary_structure IN %(sal_struct)s "
		cond += "and t2.payroll_payable_account = %(payroll_payable_account)s "
		cond += "and %(from_date)s >= t2.from_date "
		if project_list:
			cond += "and t1.project IN ({0})".format(project_list)
		employee_list = get_employee_list(sal_struct, cond, self.end_date, self.payroll_payable_account)
		employee_list = remove_payrolled_employees(employee_list, self.start_date, self.end_date)
		return employee_list

@frappe.whitelist()
def get_employee_list(sal_struct, cond, end_date, payroll_payable_account):
	return frappe.db.sql(
		"""
			select
				distinct t1.name as employee, t1.employee_name, t1.department, t1.designation
			from
				`tabEmployee` t1, `tabSalary Structure Assignment` t2
			where
				t1.name = t2.employee
				and t2.docstatus = 1
				and t1.status = 'Active'
		%s order by t2.from_date desc
		"""
		% cond,
		{
			"sal_struct": tuple(sal_struct),
			"from_date": end_date,
			"payroll_payable_account": payroll_payable_account
		},
		 as_dict=True,
	)

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

def get_count_employee_attendance(self, employee, start_date):
	scheduled_days = 0
	marked_days = 0
	roster = frappe.db.sql("""select count(*) from `tabEmployee Schedule` where
		employee=%s and date between %s and %s and employee_availability="Working" """,
		(employee, start_date, self.end_date))
	if roster and roster[0][0]:
		scheduled_days = roster[0][0]
	attendances = frappe.db.sql("""select count(*) from tabAttendance where
		employee=%s and docstatus=1 and attendance_date between %s and %s""",
		(employee, start_date, self.end_date))
	if attendances and attendances[0][0]:
		marked_days = attendances[0][0]
	return marked_days, scheduled_days

def auto_create_payroll_entry(payroll_date=None):
	"""
		Create Payroll Entry record with payroll cycle configured in HR and Payroll Additional Settings.
	"""

	if not payroll_date:
		payroll_date_day = frappe.db.get_single_value('HR and Payroll Additional Settings', 'payroll_date')
		# Calculate payroll date
		payroll_date = (datetime(getdate().year, getdate().month, cint(payroll_date_day))).strftime("%Y-%m-%d")


	# Get Payroll cycle list from HR and Payroll Settings and itrate for payroll cycle
	query = '''
		select
			distinct payroll_start_day
		from
			`tabProject Payroll Cycle`
	'''
	payroll_start_day_list = frappe.db.sql(query, as_dict=True)


	for payroll_start_day in payroll_start_day_list:
		# Find from date and end date for payroll
		start_date, end_date = get_payroll_start_end_date_by_start_day(payroll_date, payroll_start_day.payroll_start_day)

		# Create Payroll Entry
		create_monthly_payroll_entry(payroll_date, start_date, end_date)

	# # Find default from date and end date for payroll
	default_payroll_start_day = frappe.db.get_single_value('HR and Payroll Additional Settings', 'default_payroll_start_day')
	default_start_date, default_end_date = get_payroll_start_end_date_by_start_day(payroll_date, default_payroll_start_day)

	create_monthly_payroll_entry(payroll_date, default_start_date, default_end_date)

def create_monthly_payroll_entry(payroll_date, start_date, end_date):
	try:
		payroll_entry = frappe.new_doc("Payroll Entry")
		payroll_entry.posting_date = getdate(payroll_date)
		payroll_entry.payroll_frequency = "Monthly"
		payroll_entry.exchange_rate = 0
		payroll_entry.payroll_payable_account = frappe.get_value("Company", erpnext.get_default_company(), "default_payroll_payable_account")
		payroll_entry.company = erpnext.get_default_company()
		payroll_entry.start_date = start_date
		payroll_entry.end_date = end_date
		payroll_entry.cost_center = frappe.get_value("Company", erpnext.get_default_company(), "cost_center")
		payroll_entry.save()
		# Fetch employees with the project filter
		payroll_entry.fill_employee_details()
		payroll_entry.save()
		payroll_entry.submit()
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), cstr(start_date)+' | '+cstr(end_date))

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

def get_basic_salary(employee):
	filters = {
		'docstatus': 1,
		'employee': employee
	}
	salary_structure = frappe.get_value("Salary Structure Assignment", filters, "salary_structure", order_by="from_date desc")
	if salary_structure:
		basic_salary = frappe.db.sql("""
			SELECT amount FROM `tabSalary Detail`
			WHERE parenttype="Salary Structure"
			AND parent=%s
			AND salary_component="Basic"
		""",(salary_structure), as_dict=1)

		return basic_salary[0].amount if len(basic_salary) > 0 else 0.00
	else:
		frappe.throw(_("No Assigned Salary Structure found for the selected employee."))

@frappe.whitelist()
def export_payroll(doc, method):
	""" This method fetches the company bank details and makes a call to the export function based on the provided bank.

	Args:
		payroll_entry (document object): The payroll entry document object to set the export file field for.
	"""
	# Check if Export is enabled.
	if frappe.db.get_single_value("HR and Payroll Additional Settings", 'enable_export'):
		# Get default bank used to pay salaries
		default_bank = frappe.db.get_single_value("HR and Payroll Additional Settings", 'default_bank')

		# Fetch template and bank code for default bank
		template_path, bank_code = frappe.db.get_value("Bank", {'name': default_bank}, ["payroll_export_template", "bank_code"])

		cash_salary_employees = []

		for employee in doc.employees:
			if employee.salary_mode == "Cash":
				cash_salary_employees.append(employee)
			elif employee.salary_mode == "Bank":
				if not employee.iban_number:
					frappe.throw(_("No Iban/Bank account set for employee: {employee}".format(employee=employee.employee)))
			elif not employee.salary_mode:
				frappe.throw(_("No salary mode set for employee: {employee}".format(employee=employee.employee)))

		if "NBK" in bank_code:
			# Enqueue method for longer list of employees
			if len(doc.employees) > 30:
				frappe.enqueue(export_nbk, doc=doc, template_path=template_path)
			else:
				export_nbk(doc, template_path)

		if len(cash_salary_employees) > 0:
			if len(cash_salary_employees) > 30:
				frappe.enqueue(export_cash_payroll, cash_salary_employees=cash_salary_employees, doc_name=doc.name)
			else:
				export_cash_payroll(cash_salary_employees, doc.name)
		else:
			frappe.msgprint(_("No employees with salary mode as Cash."))


def export_nbk(doc, template_path):
	"""This method fetches the bank template from the provided directory, copies the template style and data into a new workbook, writes payroll entry data
		into the new workbook and saves it in the public files directory of the current site.

	Args:
		payroll_entry (document object): The payroll entry document object to be used for exporting the payroll data into the provided bank template and set the export file field.
		template_path (str): Path to the bank template file
	"""

	start = time.time()

	employees = doc.employees

	if len(employees) == 0:
		frappe.throw(_("No employees added to payroll entry."))

	if not doc.bank_account:
		frappe.throw(_("No bank account set in payroll entry."))

	iban, bank_account_no = frappe.db.get_value("Bank Account", {'name': doc.bank_account}, ["iban", "bank_account_no"])

	if not iban and not bank_account_no:
		frappe.throw(_("No IBAN or bank account number set for Bank Account: {bank_account}".format(bank_account=doc.bank_account)))

	try:
		# Load template file
		template_filename = cstr(frappe.local.site) + template_path
		template_wb = xl.load_workbook(filename=template_filename)
		template_ws = template_wb.worksheets[0]

		#-------------------- Copy template data to destination worksheet --------------------#
		# Setup new file
		destination_wb = xl.Workbook()
		destination_ws = destination_wb.active

		# Max row number with template data as per NBK template
		mr = 12
		# Max column number with template data as per NBK template
		mc = 7

		# copying the cell values from source excel file to destination excel file
		for i in range (1, mr + 1):
			for j in range (1, mc + 1):
				# reading cell value from source excel file
				c = template_ws.cell(row = i, column = j)

				d = destination_ws.cell(row = i, column = j)
				# writing the read value to destination excel file
				d.value = c.value
				# Copy cell style
				if c.has_style:
					d.font = copy(c.font)
					d.border = copy(c.border)
					d.fill = copy(c.fill)
					d.number_format = copy(c.number_format)
					d.protection = copy(c.protection)
					d.alignment = copy(c.alignment)
		#---------------------- End copy template data to destination worksheet ------------------#

		# Currency map as per NBK bank template
		currency_map = {
			'KWD': 'KWD - Kuwaiti Dinar',
			'USD': 'USD - US Dollar',
			'GBP': 'GBP - British Pound',
			'EUR': 'EUR - EURO',
			'CAD': 'CAD - Canadian Dollar',
			'AUD': 'AUD - Australian Dollar'
		}

  		# Set column numbers based on NBK bank template
		source_ws_emp_column_map = {
			'Employee Number': 1,
			'Employee Name': 2,
			'Employee IBAN Number': 3,
			'Payment Amount': 4,
			'Bank Code': 5,
			'Employee Civil ID': 6,
			'MOSAL ID': 7
		}

		# TODO: Fetch firm number
		currency = currency_map[doc.currency]
		posting_date = cstr(doc.posting_date).split("-") # => [yyyy, mm, dd]
		payment_month = posting_date[1] + "-" + posting_date[0] # => mm-yyyy

		# Set basic payroll details in row and columns based on NBK bank template
		destination_ws.cell(row=3, column=3).value = doc.company
		destination_ws.cell(row=4, column=3).value = bank_account_no or iban[-10:0]
		destination_ws.cell(row=5, column=3).value = doc.payment_purpose
		destination_ws.cell(row=6, column=3).value = payment_month
		destination_ws.cell(row=7, column=3).value = currency

		# Row number to start entering employee payroll data
		source_ws_employee_row_number = 13

		# Employee count for employee number column
		employee_number_column_count = 1

		total_hash = 0
		total_amount = 0

		# Set employee payroll details
		for employee in employees:
			if employee.salary_mode == "Bank":
				destination_ws.cell(row=source_ws_employee_row_number, column=source_ws_emp_column_map["Employee Number"]).value = employee_number_column_count
				destination_ws.cell(row=source_ws_employee_row_number, column=source_ws_emp_column_map["Employee Name"]).value = employee.employee_name
				destination_ws.cell(row=source_ws_employee_row_number, column=source_ws_emp_column_map["Employee IBAN Number"]).value = employee.iban_number
				destination_ws.cell(row=source_ws_employee_row_number, column=source_ws_emp_column_map["Payment Amount"]).value = employee.payment_amount
				destination_ws.cell(row=source_ws_employee_row_number, column=source_ws_emp_column_map["Bank Code"]).value = employee.bank_code
				destination_ws.cell(row=source_ws_employee_row_number, column=source_ws_emp_column_map["Employee Civil ID"]).value = employee.civil_id_number
				destination_ws.cell(row=source_ws_employee_row_number, column=source_ws_emp_column_map["MOSAL ID"]).value = employee.mosal_id

				iban_multipier = int(employee.iban_number[-10:])
				total_hash += round(iban_multipier * employee.payment_amount, 3)
				total_amount += round(employee.payment_amount, 3)

				employee_number_column_count += 1
				source_ws_employee_row_number += 1

		destination_ws.cell(row=8, column=3).value = len(employees)
		destination_ws.cell(row=9, column=3).value = total_amount
		destination_ws.cell(row=10, column=3).value = total_hash

		# Setup destination file directory with payroll entry name as filename
		Path("/home/frappe/frappe-bench/sites/{0}/public/files/payroll-entry/".format(frappe.local.site)).mkdir(parents=True, exist_ok=True)
		destination_file = cstr(frappe.local.site) + "/public/files/payroll-entry/{payroll_entry}.xlsx".format(payroll_entry=doc.name)

		# Save updated template in same source directory
		destination_wb.save(filename=destination_file)

		end = time.time()

		# print("Total Execution Time: ", end-start)

	except Exception as e:
		frappe.throw(e)


frappe.whitelist()
def export_cash_payroll(cash_salary_employees, doc_name):
	"""This method takes the list of employees who have salary mode set as Cash and exports the payroll employee details into an excel sheet.

	Args:
		cash_salary_employees (List[dict]): payroll empployee details
		doc_name (str): Name of the payroll entry document.
	"""
	try:
        # Setup destination file directory with payroll entry name as filename
		Path("/home/frappe/frappe-bench/sites/{0}/public/files/payroll-entry/".format(frappe.local.site)).mkdir(parents=True, exist_ok=True)
		destination_file = cstr(frappe.local.site) + "/public/files/payroll-entry/Cash-{payroll_entry}.xlsx".format(payroll_entry=doc_name)
		destination_wb = xl.Workbook()
		destination_ws = destination_wb.active

		# Fill color in first row
		color_fill = xl.styles.PatternFill(start_color='FFFF00',
                   end_color='FFFF00',
                   fill_type='solid')
		i = 1
		while(i < 5):
			destination_ws.cell(row=1, column=i).fill = color_fill
			i += 1

		# Set column names
		destination_ws.cell(row=1, column=1).value = "Employee Name"
		destination_ws.cell(row=1, column=2).value = "Payment Amount"
		destination_ws.cell(row=1, column=3).value = "Civil ID"
		destination_ws.cell(row=1, column=4).value = "Mosal ID"

		row_number = 2

		# Fill employees in rows
		for employee in cash_salary_employees:
			destination_ws.cell(row=row_number, column=1).value = employee.employee_name
			destination_ws.cell(row=row_number, column=2).value = employee.payment_amount
			destination_ws.cell(row=row_number, column=3).value = employee.civil_id_number
			destination_ws.cell(row=row_number, column=4).value = employee.mosal_id

			row_number += 1

		destination_wb.save(filename=destination_file)

	except Exception as e:
		frappe.log_error(e)

@frappe.whitelist()
def email_missing_payment_information(recipients):
	"""
		Send missing salary payment information
		as an email.
	"""
	# print(frappe.session.data)
	# print(recipients, '\n\n\n')

@frappe.whitelist()
def create_salary_slips(doc):
	"""
	Creates salary slip for selected employees if already not created
	"""
	doc.check_permission("write")
	employees = [emp.employee for emp in doc.employees]
	if employees:
		if len(employees) > 30 or frappe.flags.enqueue_payroll_entry:
			doc.db_set("status", "Queued")
			frappe.enqueue(
				create_salary_slips_for_employees,
				employees=employees,
				payroll_entry=doc,
				publish_progress=False,
				timeout=6000,
				queue='long'
			)
			frappe.msgprint(
				_("Salary Slip creation is queued. It may take a few minutes"),
				alert=True,
				indicator="blue",
			)
		else:
			create_salary_slips_for_employees(employees, payroll_entry = doc, publish_progress=False)
			# since this method is called via frm.call this doc needs to be updated manually
			doc.reload()

def log_payroll_failure(process, payroll_entry, error):
	error_log = frappe.log_error(
		title=_("Salary Slip {0} failed for Payroll Entry {1}").format(process, payroll_entry.name)
	)
	message_log = frappe.message_log.pop() if frappe.message_log else str(error)

	try:
		error_message = json.loads(message_log).get("message")
	except Exception:
		error_message = message_log

	error_message += "\n" + _("Check Error Log {0} for more details.").format(
		get_link_to_form("Error Log", error_log.name)
	)

	payroll_entry.db_set({"error_message": error_message, "status": "Failed"})

def create_salary_slips_for_employees(employees, payroll_entry, publish_progress=True ):
	try:
		payroll_entry = frappe.get_doc("Payroll Entry", payroll_entry.name)
		args = frappe._dict(
			{
				"salary_slip_based_on_timesheet": payroll_entry.salary_slip_based_on_timesheet,
				"payroll_frequency": payroll_entry.payroll_frequency,
				"company": payroll_entry.company,
				"posting_date": payroll_entry.posting_date,
				"deduct_tax_for_unclaimed_employee_benefits": payroll_entry.deduct_tax_for_unclaimed_employee_benefits,
				"deduct_tax_for_unsubmitted_tax_exemption_proof": payroll_entry.deduct_tax_for_unsubmitted_tax_exemption_proof,
				"exchange_rate": payroll_entry.exchange_rate,
				"currency": payroll_entry.currency,
				"payroll_entry": payroll_entry.name
			}
		)
		salary_slips_exist_for = get_existing_salary_slips(employees, args)
		count = 0
		start_date = payroll_entry.start_date
		end_date = payroll_entry.end_date
		salary_slip_chunk = []
		chunk_counter = 0

		employees_list = seperate_salary_slip(employees, start_date, end_date)
		if len(employees_list) < 30:
			for emp in employees_list:
				if emp['employee'] not in salary_slips_exist_for:
					args.update({"doctype": "Salary Slip"})
					args.update(emp)
					frappe.get_doc(args).insert()
					count += 1
					if publish_progress:
						frappe.publish_progress(
							count * 100 / len(set(employees) - set(salary_slips_exist_for)),
							title=_("Creating Salary Slips..."),
						)

		else:
			for emp in employees_list:
				if emp['employee'] not in salary_slips_exist_for:
					args.update({"doctype": "Salary Slip"})
					args.update(emp)

					# salary_slip_list.append(frappe.get_doc(args))
					salary_slip_chunk.append(frappe.get_doc(args))
					chunk_counter += 1
					if len(salary_slip_chunk) >= 30:
						frappe.enqueue(create_salary_slip_chunk,slips=salary_slip_chunk.copy(), queue="long")
						salary_slip_chunk = []
						chunk_counter=0

					# frappe.get_doc(args).insert()

			if salary_slip_chunk:
				frappe.enqueue(create_salary_slip_chunk,slips=salary_slip_chunk, queue="long")
		payroll_entry.db_set("status", "Submitted")
		
		if salary_slips_exist_for:
			frappe.msgprint(
				_(
					"Salary Slips already exist for employees {}, and will not be processed by this payroll."
				).format(frappe.bold(", ".join(emp for emp in salary_slips_exist_for))),
				title=_("Message"),
				indicator="orange",
			)

	except Exception as e:
		frappe.db.rollback()
		log_payroll_failure("creation", payroll_entry, e)

	finally:
		frappe.db.commit()  # nosemgrep
		frappe.publish_realtime("completed_salary_slip_creation")

def create_salary_slip_chunk(slips):
	for slip in slips:
		slip.insert()
		slip.save()

@frappe.whitelist()
def check_salary_slip_count(doc):
	payroll_entry = frappe.get_doc("Payroll Entry", doc)
	if payroll_entry.salary_slips_created == 1:
		salary_count = frappe.db.sql_list(
			f"""
			select Count(distinct employee) as salary_count from `tabSalary Slip`
			where docstatus!= 2 
				and company = '{payroll_entry.company}'
				and start_date = '{payroll_entry.start_date}'
				and end_date = '{payroll_entry.end_date}'
			""", as_dict=1)
		print(salary_count[0])
		if salary_count[0] != payroll_entry.number_of_employees:
			
			payroll_entry.db_set({"status": "Pending Salary Slip", "error_message": ""})
		else:
			payroll_entry.db_set({"status": "Submitted", "error_message": ""})
		frappe.db.commit()
	else:
		payroll_entry.db_set({"status": "Draft", "error_message": ""})
	return True

@frappe.whitelist()
def create_pending_sal_slip(doc):
	payroll_entry = frappe.get_doc("Payroll Entry", doc)
	pe_employees = [emp.employee for emp in payroll_entry.employees]
	ss_employees = frappe.db.sql_list(
		f"""
		select distinct employee from `tabSalary Slip`
		where docstatus!= 2 
			and company = '{payroll_entry.company}'
			and start_date >= '{payroll_entry.start_date}'
			and end_date <='{payroll_entry.end_date}'
		""", as_dict=True)
	employees = [e for e in pe_employees if e not in ss_employees]

	if len(employees) != 0:
		if len(employees) > 30 or frappe.flags.enqueue_payroll_entry:
			payroll_entry.db_set("status", "Queued")
			frappe.enqueue(
				create_salary_slips_for_employees,
				employees=employees,
				payroll_entry=payroll_entry,
				publish_progress=False,
				timeout=6000,
				queue='long'
			)
			frappe.msgprint(
				_("Salary Slip creation is queued. It may take a few minutes"),
				alert=True,
				indicator="blue",
			)
		else:
			create_salary_slips_for_employees(employees, payroll_entry=payroll_entry, publish_progress=False)
			# since this method is called via frm.call this doc needs to be updated manually
			payroll_entry.reload()
	return True


def get_existing_salary_slips(employees, args):
	return frappe.db.sql_list(
		"""
		select distinct employee from `tabSalary Slip`
		where docstatus!= 2 and company = %s and payroll_entry = %s
			and start_date >= %s and end_date <= %s
			and employee in (%s)
	"""
		% ("%s", "%s", "%s", "%s", ", ".join(["%s"] * len(employees))),
		[args.company, args.payroll_entry, args.start_date, args.end_date] + employees,
	)

def seperate_salary_slip(employees, start_date, end_date):
	parm = []
	for emp in employees:
		salary_structure_assignment = frappe.get_all("Salary Structure Assignment", {"employee":emp, "from_date":["between",(start_date, end_date)]},["*"])

		if len(salary_structure_assignment) > 1:
			mid_date = ""
			for ssa in salary_structure_assignment:
				start_date = frappe.utils.get_datetime(start_date).date()
				end_date = frappe.utils.get_datetime(end_date).date()

				if ssa.from_date > start_date and ssa.from_date < end_date:
					mid_date = ssa.from_date
			if mid_date:
				parm.append({"employee": emp, "start_date":start_date, "end_date":mid_date - timedelta(days=1)})
				parm.append({"employee": emp, "start_date":mid_date , "end_date":end_date})
		else:
			parm.append({"employee": emp, "start_date":start_date , "end_date":end_date})

	return parm

def notify_for_open_leave_application():
	try:
		if not frappe.db.get_single_value('HR and Payroll Additional Settings', 'remind_open_leave_application') and not production_domain():
			return

		open_leave_application = {}
		leave_list = frappe.get_all("Leave Application", {"workflow_state":"Open"}, ['*'])
		# sort INFO data by 'leave_approver' key.
		leave_list = sorted(leave_list, key=itemgetter('leave_approver'))

		#group leave application by leave approver
		for key, value in groupby(leave_list, itemgetter('leave_approver')):
			open_leave_application[key] = []
			for k in value:
				open_leave_application[key].append(k.name)
		for ola in open_leave_application:
			recipient = [ola]
			message = "<p>The Following Leave Application needs to be approved. Kindly, take action before midnight. </p><ul>"
			for leave_id in open_leave_application[ola]:
				doc_url = frappe.utils.get_link_to_form("Leave Application", leave_id)
				message += "<li>"+doc_url+"</li>"
			message += "</ul>"

			sendemail(recipients= recipient , subject="Leave Application need approval", message=message)
	except Exception as error:
		frappe.log_error(str(error), 'Open Leave Application reminder failed')

def close_all_leave_application():
	leave_list = frappe.get_list("Leave Application", {"workflow_state":"Open"}, ['*'])
	leave_ids = [leave.name for leave in leave_list]
	if len(leave_ids) <= 5:
		close_leaves(leave_ids)
	else:
		frappe.enqueue(method=close_leaves, leave_ids=leave_ids, queue='long', timeout=1200, job_name='Closing Leaves')
