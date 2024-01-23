# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate
from datetime import timedelta, date

def execute(filters=None):
    columns, data = [], []
    columns = get_columns(filters)
    data = fetch_data(filters)
    return columns, data

def fetch_data(filters):
    datapack = []

    column_dates = get_date_range(getdate(filters.get('from_date')),getdate(filters.get('to_date')),as_dict=1)
    for column_date in column_dates:
        datapack=update_data(column_date, column_dates[column_date], datapack)
        print(datapack)

    return datapack


def update_data(cur_date, column_date_field, datapack):
    # Set total attendance check in the day, row 1
    set_day_total_attendance_check(cur_date, column_date_field, datapack)

    # Set total basic roster-type attendance check in the day, row 2
    set_day_total_basic_attendance_check(cur_date, column_date_field, datapack)
    
    # Set total over-time roster-type attendance check in the day, row 3
    set_day_total_overtime_attendance_check(cur_date, column_date_field, datapack)

    # Set total pending approval attendance check in the day, row 4
    set_day_total_pending_approval_acheck(cur_date, column_date_field, datapack)

    # Set total approved attendance check in the day, row 5
    set_day_total_approved_attendance_check(cur_date, column_date_field, datapack)

    # Set attendance status count for the day, starts from row 6
    datapack, row_index = set_attendance_status_day_count(cur_date, column_date_field, datapack)

    # Set Justification details of attendance check for the day
    set_justification_details(cur_date, column_date_field, datapack, row_index)
    

    return datapack

def set_day_total_attendance_check(cur_date, column_date_field, datapack):
    # Get total attendance check in the day
    total_attendance_check = frappe.db.count('Attendance Check', {'date':cur_date, 'docstatus': ['<', 2]})
    if len(datapack) == 0:
        # Add new row Total and  column value to the report
        datapack.append({'justification_value': 'Cumulative Total', column_date_field: total_attendance_check})
    else:
        # Add cloumn value to the row in the report
        datapack[0].update({column_date_field: total_attendance_check})

    return datapack

def set_day_total_basic_attendance_check(cur_date, column_date_field, datapack):
    # Get total attendance check in the day for basic roster type
    
    total_basic_attendance_check = frappe.db.count('Attendance Check', {'date':cur_date, 'docstatus': ['<', 2], "roster_type": "Basic"})
    if len(datapack) == 1:
        # Add new row Total for Basic Roster types  and column value to the report
        datapack.append({'justification_value': 'Total (Basic)', column_date_field: total_basic_attendance_check})
    else:
        # Add column value to the row in the report
        datapack[1].update({column_date_field: total_basic_attendance_check})

    return datapack

def set_day_total_overtime_attendance_check(cur_date, column_date_field, datapack):
    # Get total attendance check in the day for overtime roster-type
    total_attendance_check = frappe.db.count('Attendance Check', {'date':cur_date, 'docstatus': ['<', 2],  "roster_type": "Over-Time"})
    if len(datapack) == 2:
        # Add new row Total for Over-time Roster types and column value to the report
        datapack.append({'justification_value': 'Total (Overtime)', column_date_field: total_attendance_check})
    else:
        # Add column value to the row in the report
        datapack[2].update({column_date_field: total_attendance_check})

    return datapack

def set_day_total_pending_approval_acheck(cur_date, column_date_field, datapack):
    pending_apporval = frappe.db.count('Attendance Check', {'date':cur_date, 'docstatus': ['<', 2], 'workflow_state': 'Pending Approval'})
    if len(datapack) == 3:
        print("hey", pending_apporval)
        # Add new row Pending Approval and column value to the report
        datapack.append({'justification_value': 'Pending Approval', column_date_field: pending_apporval})
    else:
        print("boy", pending_apporval)
        # Add cloumn value to the row in the report
        datapack[3].update({column_date_field: pending_apporval})

    return datapack

def set_day_total_approved_attendance_check(cur_date, column_date_field, datapack):
    total_approved = frappe.db.count('Attendance Check', {'date':cur_date, 'docstatus': 1, 'workflow_state': 'Approved'})
    if len(datapack) == 4:
        # Add new row Total Approved and column value to the report
        datapack.append({'justification_value': 'Total Approved', column_date_field: total_approved})
    else:
        # Add cloumn value to the row in the report
        datapack[4].update({column_date_field: total_approved})

    return datapack

def set_attendance_status_day_count(cur_date, column_date_field, datapack):
    #Get the attendance status counts for the date
    query = f"""
        select
            attendance_status, count(attendance_status) as count_attendance_status
        from
            `tabAttendance Check`
        where
            docstatus = 1 and date = "{cur_date}" and workflow_state = "Approved"
        group by
            attendance_status
    """
    attendance_status_counts = frappe.db.sql(query, as_dict=1)

    status_count_data = {item['attendance_status']: item['count_attendance_status'] for item in attendance_status_counts}

    # Get attendance status options from the doctype definition of Attendance Check
    attendance_status_options = frappe.get_meta("Attendance Check").get_options("attendance_status").split('\n')
    # Remove first empty option
    attendance_status_options.pop(0)

    # Attendance status count adds from 5th row(index will be 4)
    row_index = 4
    for attendance_status in attendance_status_options:
        # Set total attendance_status of attendance check in the day
        attendance_status_count = status_count_data[attendance_status] if attendance_status in status_count_data else 0
        if len(datapack) == row_index:
            # Add new status row to the report
            datapack.append({'justification_value': attendance_status})
        # Add cloumn value to the row in the report
        datapack[row_index].update({column_date_field: attendance_status_count})
        row_index += 1

    return datapack, row_index

def set_justification_details(cur_date, column_date_field, datapack, row_index):
    # Get justification options from the doctype definition of Attendance Check
    justifications = frappe.get_meta("Attendance Check").get_options("justification").split('\n')
    # Remove first empty option
    justifications.pop(0)

    #Get the attendance checks for the date
    query = f"""
        select
            justification, count(justification) as count_justification
        from
            `tabAttendance Check`
        where
            docstatus = 1 and justification !=""  and date = "{cur_date}" and workflow_state = "Approved"
        group by
            justification
    """
    attendance_checks = frappe.db.sql(query, as_dict=1)

    for justification in justifications:
        if len(datapack) == row_index:
            datapack.append({'justification_value': justification})

        justification_day_count = 0

        for attendance_check in attendance_checks:
            if attendance_check.justification == justification:
                justification_day_count = attendance_check.count_justification

        datapack[row_index].update({column_date_field: justification_day_count})
        row_index += 1

    return datapack

def get_columns(filters):
    if getdate(filters.get('from_date')) > getdate(filters.get('to_date')):
        frappe.throw("From date cannot be after To Date")
    columns = [{
            "label": " ",
            "fieldname": 'justification_value',
            "fieldtype": "Data",
            "width": 300,
        }]
    daterange = get_date_range(getdate(filters.get('from_date')),getdate(filters.get('to_date')))
    for value in daterange:
        s_date = value.strftime('%d-%b')
        columns.append(
            {
            "label": s_date,
            "fieldname": s_date.lower(),
            "fieldtype": "Int",
            "width": 100,
        }
        )
    return columns

def get_date_range(start_date, end_date, as_dict = False):
    dates = [] if not as_dict else {}
    for n in range(int((end_date - start_date).days)):
        if not as_dict:
            dates.append(start_date + timedelta(n))
        else:
            dates[start_date + timedelta(n)]=(start_date + timedelta(n)).strftime('%d-%b').lower()
    if not as_dict:
        dates.append(end_date) if not as_dict else dates.append({end_date:end_date.strftime('%d-%b').lower()})
    else:
        dates[end_date]=(end_date).strftime('%d-%b').lower()

    return dates
