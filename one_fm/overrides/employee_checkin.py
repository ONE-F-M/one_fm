import frappe

from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, get_link_to_form

from hrms.hr.doctype.attendance.attendance import (
	get_duplicate_attendance_record,
	get_overlapping_shift_attendance,
)
from hrms.hr.doctype.shift_assignment.shift_assignment import (
	get_actual_start_end_datetime_of_shift,
)
from hrms.hr.utils import validate_active_employee


class EmployeeCheckinOverride(EmployeeCheckin):


	def fetch_shift(self):
		pass

