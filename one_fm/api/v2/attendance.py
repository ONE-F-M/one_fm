import frappe
from frappe.utils import getdate, get_last_day, get_first_day
from one_fm.api.v2.utils import response


@frappe.whitelist()
def get_attendance_list(employee, from_date=None, to_date=None, status=None):
    """
        Get employee sttendance based on filter
    """
    try:
        todays_date = getdate()
        if not (from_date and to_date):
            from_date = str(get_first_day(todays_date))
            to_date = str(get_last_day(todays_date))

        filters = {
            'employee':employee,
            'attendance_date': ["BETWEEN", [from_date, to_date]],
        }
        if status:
            filters['status'] = status
        response('success', 200, frappe.db.get_list("Attendance", filters=filters, ignore_permissions=True))
    except Exception as e:
        response('error', 500, None, str(e))
    
