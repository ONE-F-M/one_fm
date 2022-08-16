import frappe
from frappe import _
from one_fm.api.doc_methods.payroll_entry import get_basic_salary
from one_fm.api.notification import create_notification_log
from frappe.utils import cint, flt, date_diff, cstr, today, getdate

def get_scheduled_day_off(employee, start_date, end_date):
	schedule_list = frappe.db.sql_list("""
	select distinct date from `tabEmployee Schedule`
	where
		employee=%s and
		date between %s and %s
		and employee_availability in ("Day Off", "Sick Leave", "Annual Leave", "Emergency Leave") """,
	(employee, start_date, end_date))

	schedules = [cstr(schedule) for schedule in schedule_list]

	return schedules

def get_leave_details(self, joining_date=None, relieving_date=None, lwp=None, for_preview=0):
	if not joining_date:
		joining_date, relieving_date = frappe.get_cached_value("Employee", self.employee,
			["date_of_joining", "relieving_date"])

	working_days = date_diff(self.end_date, self.start_date) + 1
	if for_preview:
		self.total_working_days = working_days
		self.payment_days = working_days
		return

	holidays = self.get_holidays_for_employee(self.start_date, self.end_date)
	actual_lwp = self.calculate_lwp(holidays, working_days)
	if not cint(frappe.db.get_value("HR Settings", None, "include_holidays_in_total_working_days")):
		working_days -= len(holidays)
		if working_days < 0:
			frappe.throw(_("There are more holidays than working days this month."))

	if not lwp:
		lwp = actual_lwp
	elif lwp != actual_lwp:
		frappe.msgprint(_("Leave Without Pay does not match with approved Leave Application records"))

	self.total_working_days = working_days
	self.leave_without_pay = lwp

	absent_days = frappe.db.sql("""select count(name) as absent from `tabAttendance` where employee=%s and status="Absent" and attendance_date between %s and %s """,
	(self.employee, self.start_date, self.end_date), as_dict=1)

	payment_days = flt(self.get_payment_days(joining_date, relieving_date)) - flt(lwp) - flt(absent_days[0].absent if len(absent_days) > 0 else 0)
	self.payment_days = payment_days > 0 and payment_days or 0


def get_working_days_details(
	self, joining_date=None, relieving_date=None, lwp=None, for_preview=0
):
	payroll_based_on = frappe.db.get_value("Payroll Settings", None, "payroll_based_on")
	include_holidays_in_total_working_days = frappe.db.get_single_value(
		"Payroll Settings", "include_holidays_in_total_working_days"
	)

	include_day_off_in_total_working_days = frappe.db.get_single_value(
		"HR and Payroll Additional Settings", "include_day_off_in_total_working_days"
	)

	working_days = date_diff(self.end_date, self.start_date) + 1
	if for_preview:
		self.total_working_days = working_days
		self.payment_days = working_days
		return

	holidays = self.get_holidays_for_employee(self.start_date, self.end_date)

	if not cint(include_holidays_in_total_working_days):
		working_days -= len(holidays)
		if working_days < 0:
			frappe.throw(_("There are more holidays than working days this month."))

	day_off_dates = get_scheduled_day_off(self.employee, self.start_date, self.end_date)

	if not cint(include_day_off_in_total_working_days):
		working_days -= len(day_off_dates)
		if working_days < 0:
			frappe.throw(_("There are more day off/holidays than working days this month."))

	if not payroll_based_on:
		frappe.throw(_("Please set Payroll based on in Payroll settings"))

	if payroll_based_on == "Attendance":
		actual_lwp, absent = self.calculate_lwp_ppl_and_absent_days_based_on_attendance(holidays)
		self.absent_days = absent
	else:
		actual_lwp = self.calculate_lwp_or_ppl_based_on_leave_application(holidays, working_days)

	if not lwp:
		lwp = actual_lwp
	elif lwp != actual_lwp:
		frappe.msgprint(
			_("Leave Without Pay does not match with approved {} records").format(payroll_based_on)
		)

	self.leave_without_pay = lwp
	self.total_working_days = working_days

	# Set Payment days by considerring include_holidays_in_total_working_days
	payment_days = self.get_payment_days(
		joining_date, relieving_date, include_holidays_in_total_working_days
	)

	# Payment days by considerring include_day_off_in_total_working_days
	if not cint(include_day_off_in_total_working_days):
		payment_days -= len(day_off_dates)

	if flt(payment_days) > flt(lwp):
		self.payment_days = flt(payment_days) - flt(lwp)

		if payroll_based_on == "Attendance":
			self.payment_days -= flt(absent)

		consider_unmarked_attendance_as = (
			frappe.db.get_value("Payroll Settings", None, "consider_unmarked_attendance_as") or "Present"
		)

		if payroll_based_on == "Attendance" and consider_unmarked_attendance_as == "Absent":
			unmarked_days = self.get_unmarked_days(include_holidays_in_total_working_days)
			self.absent_days += unmarked_days  # will be treated as absent
			self.payment_days -= unmarked_days
	else:
		self.payment_days = 0

def get_unmarked_days_based_on_doj_or_relieving(
		self, unmarked_days, include_holidays_in_total_working_days, start_date, end_date
	):
	"""
	Exclude days before DOJ or after
	Relieving Date from unmarked days
	"""
	from erpnext.hr.doctype.employee.employee import is_holiday
	include_day_off_in_total_working_days = frappe.db.get_single_value(
		"HR and Payroll Additional Settings", "include_day_off_in_total_working_days"
	)
	if include_holidays_in_total_working_days and include_day_off_in_total_working_days:
		unmarked_days -= date_diff(end_date, start_date) + 1
	elif include_holidays_in_total_working_days:
		unmarked_days -= date_diff(end_date, start_date) + 1
		for days in range(date_diff(end_date, start_date) + 1):
			date = add_days(end_date, -days)
			# include if not day off
			if not include_day_off_in_total_working_days and not is_day_off(self.employee, date):
				unmarked_days += 1
	else:
		for days in range(date_diff(end_date, start_date) + 1):
			date = add_days(end_date, -days)
			# exclude if not holidays
			if not is_holiday(self.employee, date):
				unmarked_days -= 1
			# exclude if not day off
			if not include_day_off_in_total_working_days and not is_day_off(self.employee, date):
				unmarked_days -= 1
	return unmarked_days

def is_day_off(employee, date=None):
	"""
	Returns True if given Employee has an holiday on the given date
        :param employee: Employee `name`
        :param date: Date to check. Will check for today if None
	"""

	if not date:
		date = today()

	day_off_dates = get_scheduled_day_off(employee, date, date)

	return len(day_off_dates) > 0

def salary_slip_before_submit(doc, method):
	basic_salary = get_basic_salary(doc.employee)

	# As per Kuwaiti law, 90% of WP salary has to be paid to an employee after factoring in deductions
	minimum_payable_salary = 0.9 * basic_salary

	if doc.net_pay < minimum_payable_salary:
		notify_payroll(doc)
		frappe.throw(_("Total deduction amount exceeds the permissible limit in Salary Slip for {}".format(doc.employee+":"+doc.employee_name)))


def notify_payroll(doc):
	email = frappe.get_value("HR Settings", "HR Settings", "payroll_notifications_email")
	subject = _("Urgent Attention Needed: Issues with maximum deduction in Payroll")
	message = _("Total deduction amount exceeds the permissible limit in Salary Slip for {}".format(doc.employee+":"+doc.employee_name))
	create_notification_log(subject,message,[email], doc)
