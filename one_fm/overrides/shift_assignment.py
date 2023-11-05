import frappe
from frappe.utils import add_days, now, today
from datetime import datetime
from hrms.hr.doctype.shift_assignment.shift_assignment import *


class ShiftAssignmentOverride(ShiftAssignment):
        
    def validate(self):
        self.set_datetime()
        super(ShiftAssignmentOverride, self).validate()

    def validate_overlapping_shifts(self):
        overlapping_dates = self.get_overlapping_dates()
        if len(overlapping_dates):
            # if dates are overlapping, check if timings are overlapping, else allow
            overlapping_timings = has_overlapping_timings(self)
            if overlapping_timings:
                self.throw_overlap_error(overlapping_dates[0])

    def before_insert(self):
        """
            Before insert events to execute
        """
        self.set_datetime()
        if not frappe.db.exists("Employee", {'name':self.employee, 'status':'Active'}):
            frappe.throw(f"{self.employee} - {self.employee_name} is not active and cannot be assigned to a shift")
        
    def set_datetime(self):
        if self.shift_type:
            shift = frappe.get_doc("Shift Type", self.shift_type)
            self.start_datetime = datetime.strptime(f"{self.start_date} {(datetime.min + shift.start_time).time()}", '%Y-%m-%d %H:%M:%S')
            if shift.end_time.total_seconds() < shift.start_time.total_seconds():
                self.end_datetime = datetime.strptime(f"{add_days(self.start_date, 1)} {(datetime.min + shift.end_time).time()}", '%Y-%m-%d %H:%M:%S')
            else:
                self.end_datetime = datetime.strptime(f"{self.start_date} {(datetime.min + shift.end_time).time()}", '%Y-%m-%d %H:%M:%S')


def has_overlapping_timings(self) -> bool:
    """
    Accepts two shift types and checks whether their timings are overlapping
    """
    if datetime.strptime(str(self.start_datetime), '%Y-%m-%d %H:%M:%S').date()>datetime.strptime(today(), '%Y-%m-%d').date():
        frappe.throw(f"Shift cannot be created for date greater than today. Today is {today()}, you requested {self.start_date}")

    existing_shift = frappe.db.sql(f"""
        SELECT * FROM `tabShift Assignment` WHERE
        employee="{self.employee}" AND status='Active' AND docstatus=1 AND (
        (start_datetime BETWEEN '{self.start_datetime}' AND '{self.end_datetime}')
        OR 
        (end_datetime BETWEEN '{self.start_datetime}' AND '{self.end_datetime}')
        )

        ORDER BY end_datetime DESC
    """, as_dict=1)
    if existing_shift:
        shift=existing_shift[0]
        frappe.throw(f"""
            Employee <b>{shift.employee} - {shift.employee_name}</b> already has an active Shift <b><a href='/app/shift-assignment/{shift.name}'>{shift.shift_type}: {shift.name}</a></b> that overlaps within this period.
        """)
        return True
    return False
	