import frappe
from frappe.utils import add_days, now, today, now_datetime
from datetime import datetime, timedelta
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

    def get_cut_off(self):
        """
            Get earliest checkin and latest checkout time
        """
        shift_type=frappe.db.get_value("Shift Type", self.shift_type, [
           'begin_check_in_before_shift_start_time', 'allow_check_out_after_shift_end_time',
        ], as_dict=1)
        start_cutoff = self.start_datetime + timedelta(minutes=-shift_type.begin_check_in_before_shift_start_time)
        end_cutoff = self.end_datetime + timedelta(minutes=shift_type.allow_check_out_after_shift_end_time)
        return frappe._dict({
            'start':start_cutoff,
            'end':end_cutoff,
        })
    
    def can_checkin_out(self):
        """
            Check if user can checkin or our based on earliest and latest in or out.
        """
        cutoff = self.get_cut_off()
        if ((now_datetime() < cutoff.start) or (now_datetime() > cutoff.end)):
            return False
        return True
    
    def after_4hrs(self):
        """
            Check if checkin time has exceeded 4hrs, which mean employee is late.
        """
        if (
            (divmod((now_datetime()-self.start_datetime).total_seconds(), 3600)[0] > 4) and not frappe.db.exists(
                "Employee Checkin", {'shift_assignment':self.name})):
            return True
        return False

    def check_existing_checking(self):
        """API to determine the applicable Log type.
        The api checks employee's last lcheckin log type. and determine what next log type needs to be
        Returns:
            True: The log in was "IN", so his next Log Type should be "OUT".
            False: either no log type or last log type is "OUT", so his next Ltg Type should be "IN".
        """
        checkin = frappe.db.get_list("Employee Checkin", filters={
            'employee':self.employee, 'shift_assignment':self.name,
            'roster_type':self.roster_type
            }, 
            fields='log_type',
            order_by="actual_time DESC"
        )
        if checkin:
            # #For Check IN
            if checkin[0].log_type=='OUT':
                return "IN"
            #For Check OUT
            else:
                return "OUT"
        return "IN"

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
	