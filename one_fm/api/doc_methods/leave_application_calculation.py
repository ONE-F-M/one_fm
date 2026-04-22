import frappe
from frappe.utils import flt, cint, getdate, date_diff
from hrms.hr.doctype.leave_application.leave_application import get_number_of_leave_days as standard_get_number_of_leave_days, get_holidays
import datetime

@frappe.whitelist()
def custom_get_number_of_leave_days(
    employee: str,
    leave_type: str,
    from_date: datetime.date,
    to_date: datetime.date,
    half_day: int | str | None = None,
    half_day_date: datetime.date | str | None = None,
    holiday_list: str | None = None,
) -> float:
    """
    Override for standard get_number_of_leave_days.
    Automatically excludes holidays for non-shift workers,
    and specifically excludes only Fridays for Shift workers on 'Annual Leave'.
    """
    if leave_type != "Annual Leave":
        # Fall back to standard calculation
        return standard_get_number_of_leave_days(
            employee, leave_type, from_date, to_date, half_day, half_day_date, holiday_list
        )

    # Calculate actual calendar days including half day logic
    number_of_days = 0
    if cint(half_day) == 1:
        if getdate(from_date) == getdate(to_date):
            number_of_days = 0.5
        elif half_day_date and getdate(from_date) <= getdate(half_day_date) <= getdate(to_date):
            number_of_days = date_diff(to_date, from_date) + 0.5
        else:
            number_of_days = date_diff(to_date, from_date) + 1
    else:
        number_of_days = date_diff(to_date, from_date) + 1
    
    # Identify if Shift worker
    shift_working = frappe.db.get_value("Employee", employee, "shift_working")
    
    if shift_working:
        # For Shift: (Total Calendar Days) - (Count of Fridays in the period)
        from datetime import timedelta
        start = getdate(from_date)
        end = getdate(to_date)
        
        friday_count = 0
        current = start
        while current <= end:
            if current.weekday() == 4: # Friday
                friday_count += 1
            current += timedelta(days=1)
            
        number_of_days = flt(number_of_days) - friday_count
    else:
        # For Non-Shift: (Total Calendar Days) - (Matching Days in Assigned Holiday List)
        # Even if include_holiday is True on the Leave Type, we force it to skip standard holidays.
        holidays_count = get_holidays(employee, from_date, to_date, holiday_list=holiday_list)
        number_of_days = flt(number_of_days) - flt(holidays_count)
        
    return number_of_days
