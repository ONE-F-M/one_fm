from datetime import datetime, date, timedelta
import calendar
import frappe, json
from frappe import _
from frappe.desk.notifications import get_filters_for
from hrms.hr.report.employee_leave_balance.employee_leave_balance import get_data as get_leave_balance
from one_fm.api.v1.utils import response


@frappe.whitelist()
def get_employee_shift(employee_id, date_type='month'):
    """
        Fetch employee information relating to
        leave_balance, shift, penalties and attendance
    """

    # prepare dates
    today = datetime.today()
    _start = today.replace(day=1).date()
    _end = today.replace(day = calendar.monthrange(today.year, today.month)[1]).date()

    if(date_type=='year'):
        _start = date(today.year, 1, 31)
        _end = date(today.year, 12, 31)

    penalty_start_date = datetime.now() - timedelta(days=364)
    penalty_end_date = date(today.year, today.month, today.day)

    data = {
        "leave_balance": "",
        "penalties": "",
        "days_worked": "",
        "shift_time_from": "",
        "shift_time_to": "",
        "shift_location": "",
        "shift_latitude_and_longitude": ""
    }
    try:
        employee = frappe.get_doc('Employee', employee_id)
        shift_assignment =  frappe.db.get_list('Shift Assignment',
           filters=[
               ['employee', '=', employee.name],
           ],
           fields=['name', 'employee', 'site', 'shift_type'],
           order_by='modified desc',
           limit=1,
           )
        if(len(shift_assignment)):
            site = frappe.get_doc("Operations Site", shift_assignment[0].site)
            shift_location = frappe.get_doc("Location", site.site_location)
            shift_type = frappe.get_doc('Shift Type', shift_assignment[0].shift_type)
            days_worked = frappe.db.get_list('Attendance',
                filters=[
                 ['employee', '=', employee.name],
                 ['status', '=', 'Present'],
                 ['attendance_date', 'BETWEEN', [_start, _end]],
                ],
                fields=['COUNT(*) as count', 'name', 'employee', 'status', 'attendance_date'],
                order_by='modified desc',
                )[0].count
            penalties = frappe.db.sql(f"""
				SELECT COUNT(*) as count
				FROM `tabPenalty` p
				WHERE p.recipient_employee="{employee.name}"
				AND p.workflow_state = 'Penalty Accepted'
				AND p.penalty_issuance_time BETWEEN "{penalty_start_date} 00:00:00" AND "{penalty_end_date} 23:59:59";
			""", as_dict=1)[0].count

            # get leav balance filters
            filters=frappe._dict({'from_date':_start, 'to_date':_end, 'employee':employee.name})
            leave_balance = sum([i.closing_balance for i in get_leave_balance(filters)])
            return response(
                f"Employee shift record retrieved from {_start} to {_end}",
                201,
                {
                    'employee': employee.name,
                    'leave_balance': 0, #leave_balance,
                    'penalties': penalties,
                    'days_worked':days_worked,
                    'shift_time_from': shift_type.start_time,
                    'shift_time_to': shift_type.end_time,
                    'shift_location': shift_location.name,
                    'shift_latitude_and_longitude': {
                        'latitude': shift_location.latitude,
                        'longitude': shift_location.longitude,
                    }
                }
            )
        else:
            # return no shift found
            return response(f"No shift found for {employee.name}", 200, None, None)

    except Exception as e:
        # an error occurred
        return response(str(e), 500, None, None)
