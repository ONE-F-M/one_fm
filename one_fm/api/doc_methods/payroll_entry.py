import frappe, erpnext
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, cstr, flt, nowdate, add_days, getdate, fmt_money, add_to_date, DATE_FORMAT, date_diff
from frappe import _
from erpnext.payroll.doctype.payroll_entry.payroll_entry import get_end_date, get_filter_condition, get_joining_relieving_condition, get_emp_list, get_sal_struct, remove_payrolled_employees


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

frappe.whitelist()
def get_emp_lists(self):
		"""
			Returns list of active employees based on selected criteria
			and for which salary structure exists
		"""
		self.check_mandatory()
		filters = self.make_filters()
		cond = get_filter_condition(filters)
		cond += get_joining_relieving_condition(self.start_date, self.end_date)

		condition = ''
		if self.payroll_frequency:
			condition = """and payroll_frequency = '%(payroll_frequency)s'"""% {"payroll_frequency": self.payroll_frequency}

		sal_struct = get_sal_struct(self.company, self.currency, self.salary_slip_based_on_timesheet, condition)
		if sal_struct:
			cond += "and t2.salary_structure IN %(sal_struct)s "
			cond += "and t2.payroll_payable_account = %(payroll_payable_account)s "
			cond += "and %(from_date)s >= t2.from_date"
			emp_list = get_emp_list(sal_struct, cond, self.end_date, self.payroll_payable_account)
			get_bank_details(emp_list)
			emp_list = remove_payrolled_employees(emp_list, self.start_date, self.end_date)
			return emp_list

@frappe.whitelist()
def get_bank_details(employee_details):
	for employee in employee_details:
		iban_no, bank_code = frappe.db.get_value("Bank Account",{"party":employee.employee},["iban","bank"])
		employee.iban_number = iban_no
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
