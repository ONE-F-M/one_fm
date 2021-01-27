import frappe, erpnext
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, flt, nowdate, add_days, getdate, fmt_money, add_to_date, DATE_FORMAT, date_diff
from frappe import _
from erpnext.hr.doctype.payroll_entry.payroll_entry import get_end_date


def validate_employee_attendance(self):
    employees_to_mark_attendance = []
    days_in_payroll, days_holiday, days_attendance_marked = 0, 0, 0

    for employee_detail in self.employees:
        days_holiday = self.get_count_holidays_of_employee(employee_detail.employee)
        days_attendance_marked, days_scheduled = self.get_count_employee_attendance(employee_detail.employee)
        print("days_holiday", days_holiday)
        print(days_attendance_marked)

        days_in_payroll = date_diff(self.end_date, self.start_date) + 1
        print(days_in_payroll ,(days_holiday + days_attendance_marked),(days_holiday + days_scheduled))
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



def create_payroll_entry():
    try:
        departments = frappe.get_all("Department")
        start_date = add_to_date(nowdate(), months=-1)
        end_date = get_end_date(start_date, 'monthly')['end_date']
        start_date = '2020-11-24'
        end_date = '2020-12-23'
        selected_dept = ''
        for department in departments:
            selected_dept = department.name
            payroll_entry = frappe.new_doc("Payroll Entry")
            payroll_entry.posting_date = getdate()
            payroll_entry.department = department.name
            payroll_entry.payroll_frequency = "Monthly"
            payroll_entry.company = erpnext.get_default_company()
            payroll_entry.start_date = start_date
            payroll_entry.end_date = end_date
            payroll_entry.cost_center = frappe.get_value("Company", erpnext.get_default_company(), "cost_center")
            payroll_entry.save()
            payroll_entry.fill_employee_details()
            payroll_entry.save()
            payroll_entry.submit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), selected_dept+' | '+start_date+' | '+end_date)
