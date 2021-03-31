import frappe
from frappe.utils import cint
from erpnext.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log
import itertools

def process_auto_attendance(self):
    print(cint(self.enable_auto_attendance), self.process_attendance_after, self.last_sync_of_checkin)
    print(not cint(self.enable_auto_attendance), not self.process_attendance_after, not self.last_sync_of_checkin)
    if not cint(self.enable_auto_attendance) or not self.process_attendance_after or not self.last_sync_of_checkin:
        return
    filters = {
        'skip_auto_attendance':'0',
        'attendance':('is', 'not set'),
        'time':('>=', self.process_attendance_after),
        'shift_actual_end': ('<', self.last_sync_of_checkin),
        'shift': self.name
    }
    logs = frappe.db.get_list('Employee Checkin', fields="*", filters=filters, order_by="employee,time")
    print(filters, logs)
    for key, group in itertools.groupby(logs, key=lambda x: (x['employee'], x['shift_actual_start'])):
        single_shift_logs = list(group)
        attendance_status, working_hours, late_entry, early_exit = self.get_attendance(single_shift_logs)
        mark_attendance_and_link_log(single_shift_logs, attendance_status, key[1].date(), working_hours, late_entry, early_exit, self.name)
    for employee in self.get_assigned_employee(self.process_attendance_after, False):
        self.mark_absent_for_dates_with_no_attendance(employee)