import frappe
from erpnext.hr.doctype.attendance_request.attendance_request import AttendanceRequest


class AttendanceRequestOverride(AttendanceRequest):
    def create_attendance(self):
        pass