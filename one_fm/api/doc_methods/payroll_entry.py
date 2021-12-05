import frappe, erpnext
from erpnext.payroll.doctype.payroll_entry.payroll_entry import get_existing_salary_slips
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, cstr, flt, nowdate, add_days, getdate, fmt_money, add_to_date, DATE_FORMAT, date_diff
from frappe import _
import openpyxl as xl
import time
from copy import copy
from pathlib import Path

def validate_employee_attendance(self):
	employees_to_mark_attendance = []
	days_in_payroll, days_holiday, days_attendance_marked = 0, 0, 0

	for employee_detail in self.employees:
		days_holiday = self.get_count_holidays_of_employee(employee_detail.employee)
		days_attendance_marked, days_scheduled = self.get_count_employee_attendance(employee_detail.employee)

		days_in_payroll = date_diff(self.end_date, self.start_date) + 1
		if days_in_payroll != (days_holiday + days_attendance_marked) != (days_holiday + days_scheduled) :
			employees_to_mark_attendance.append({
				"employee": employee_detail.employee,
				"employee_name": employee_detail.employee_name
				})
	return employees_to_mark_attendance

def get_count_holidays_of_employee(self, employee):
	holidays = 0
	days = frappe.db.sql("""select count(*) from `tabEmployee Schedule` where
		employee=%s and date between %s and %s and employee_availability in ("Day Off", "Sick Leave", "Annual Leave", "Emergency Leave") """, (employee,
		self.start_date, self.end_date))
	if days and days[0][0]:
		holidays = days[0][0]
	return holidays

@frappe.whitelist()
def fill_employee_details(self):
	"""
	This Function fetches the employee details and updates the 'Employee Details' child table.

	Returns:
		list of active employees based on selected criteria
		and for which salary structure exists.
	"""	
	self.set('employees', [])
	employees = self.get_emp_list()
	
	#Fetch Bank Details and update employee list 
	set_bank_details(employees)
	
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
def set_bank_details(employee_details):
	"""This Funtion Sets the bank Details of an employee. The data is fetched from Bank Account Doctype.

	Args:
		employee_details (dict): Employee Details Child Table.

	Returns:
		employee_details ([dict): Sets the bank account IBAN code and Bank Code.
	"""
	for employee in employee_details:
		iban, bank, bank_account_no = frappe.db.get_value("Bank Account",{"party":employee.employee},["iban","bank", "bank_account_no"])
		if not bank:
			frappe.throw(_("Bank Details for {0} does not exists").format(employee.employee))
		else:
			employee.iban_number = iban or bank_account_no
			bank_code = frappe.db.get_value("Bank", {'name': bank}, ["bank_code"])
			employee.bank_code = bank_code
	return employee_details

def get_count_employee_attendance(self, employee):
	scheduled_days = 0
	marked_days = 0 
	roster = frappe.db.sql("""select count(*) from `tabEmployee Schedule` where 
		employee=%s and date between %s and %s and employee_availability="Working" """, 
		(employee, self.start_date, self.end_date))
	if roster and roster[0][0]:
		scheduled_days = roster[0][0]
	attendances = frappe.db.sql("""select count(*) from tabAttendance where
		employee=%s and docstatus=1 and attendance_date between %s and %s""",
		(employee, self.start_date, self.end_date))
	if attendances and attendances[0][0]:
		marked_days = attendances[0][0]
	return marked_days, scheduled_days

def create_payroll_entry(start_date, end_date):
	"""Create Payroll Entry doc from the given period.

	Args:
		start_date (date): Start date of the payroll
		end_date (date): End Date of the payroll

	Returns:
		[doc]: newly created Payroll Entry Doc
	"""
	try:
		#selected_dept = department
		payroll_entry = frappe.new_doc("Payroll Entry")
		payroll_entry.posting_date = getdate()
		#payroll_entry.department = department
		payroll_entry.payroll_frequency = "Monthly"
		payroll_entry.exchange_rate = 0
		payroll_entry.payroll_payable_account = frappe.get_value("Company", erpnext.get_default_company(), "default_payroll_payable_account")
		payroll_entry.company = erpnext.get_default_company()
		payroll_entry.start_date = start_date
		payroll_entry.end_date = end_date
		payroll_entry.cost_center = frappe.get_value("Company", erpnext.get_default_company(), "cost_center")
		payroll_entry.save()
		payroll_entry.fill_employee_details()
		payroll_entry.save()
		payroll_entry.submit()
		frappe.db.commit()
		return payroll_entry
	except Exception:
		frappe.log_error(frappe.get_traceback(), cstr(start_date)+' | '+cstr(end_date))

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
def set_payroll_export_file_path(doc, method):
	""" This method fetches the company bank details and makes a call to the export function based on the provided bank.

	Args:
		payroll_entry (document object): The payroll entry document object to set the export file field for.
	"""
	# Get default bank used to pay salaries
	default_bank = frappe.db.get_single_value("HR and Payroll Additional Settings", 'default_bank')

	# Fetch template and bank code for default bank
	template_path, bank_code = frappe.db.get_value("Bank", {'name': default_bank}, ["payroll_export_template", "bank_code"])
	
	if "NBK" in bank_code:
		# Enqueue method for longer list of employees
		if len(doc.employees) > 30:
			frappe.enqueue(export_nbk, doc=doc, template_path=template_path)
		else:
			export_nbk(doc, template_path)

def export_nbk(doc, template_path):
	"""This method fetches the bank template from the provided directory, copies the template style and data into a new workbook, writes payroll entry data 
		into the new workbook and saves it in the private files directory of the current site.

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
		Path("/home/frappe/frappe-bench/sites/{0}/private/files/payroll-entry/".format(frappe.local.site)).mkdir(parents=True, exist_ok=True)
		destination_file = cstr(frappe.local.site) + "/private/files/payroll-entry/{payroll_entry}.xlsx".format(payroll_entry=doc.name)
		
		# Save updated template in same source directory
		destination_wb.save(filename=destination_file)

		end = time.time()

		print("Total Execution Time: ", end-start)

	except Exception as e:
		frappe.throw(e)

@frappe.whitelist(allow_guest=True)
def download_excel_payroll_export_file(payroll_entry):
	return get_excel_payroll_export_file(payroll_entry)

def get_excel_payroll_export_file(payroll_entry):
	app_url = frappe.local.conf.app_url
	filename = payroll_entry + ".xlsx"
	path = "/private/files/payroll-entry/"

	result = {}
	result.update({'filename': filename})
	result.update({'app_url': app_url})
	result.update({'path': path})
  
	return result