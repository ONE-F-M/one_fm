# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

from frappe.utils import getdate
from datetime import timedelta, date
import frappe


def execute(filters=None):
    columns, data = [], []
    columns = get_columns(filters)
    data = fetch_data(filters)
    return columns, data


def fetch_created_attendance_check(supervisor,filters):
    created_query = f"""
            select  DATE_FORMAT(ac.date, '%d-%b') AS formatted_date, IFNULL(count(ac.name),0) as number from
            `tabAttendance Check`ac JOIN `tabEmployee`emp on ac.shift_supervisor = emp.name
               where emp.employee_name  = '{supervisor}' and ac.date BETWEEN
               '{filters.get("from_date")}' and '{filters.get("to_date")}' and ac.docstatus = 1
            GROUP BY ac.date
              """

    present_query = f"""
            select  DATE_FORMAT(ac.date, '%d-%b') AS formatted_date, IFNULL(count(ac.name),0) as number from
            `tabAttendance Check`ac JOIN `tabEmployee`emp on ac.shift_supervisor = emp.name
               where emp.employee_name  = '{supervisor}' and ac.date BETWEEN
               '{filters.get("from_date")}' and '{filters.get("to_date")}' and ac.docstatus = 1 and ac.attendance_status = 'Present'
            GROUP BY ac.date
              """

    created_rs = frappe.db.sql(created_query,as_dict=1)
    created_rd = {row.formatted_date:row.number for row in created_rs}
    present_rs = frappe.db.sql(present_query,as_dict=1)
    present_rd = {row.formatted_date:row.number for row in present_rs}
    return [created_rd,present_rd]


def fetch_daily_count(supervisor,filters):
    #Fetch the daily checkin and attendance check of each supervisor

    query = f"""
            select  DATE_FORMAT(ecn.date, '%d-%b') AS formatted_date, IFNULL(count(ecn.name),0) as number from `tabEmployee Checkin`ecn JOIN `tabOperations Shift Supervisor`ops on ops.parent = ecn.operations_shift 
               where ecn.log_type = "IN" and ops.supervisor_name = '{supervisor}' and ecn.date BETWEEN
               '{filters.get("from_date")}' and '{filters.get("to_date")}'
            GROUP BY ecn.date
              """
    result_set = frappe.db.sql(query,as_dict=1)
    result_dict = {row.formatted_date:row.number for row in result_set}
    return result_dict



def fetch_data(filters):
    column_names = get_date_range(getdate(filters.get('from_date')),getdate(filters.get('to_date')),as_dict=1)
    init_dict = {}
    for one in column_names.values():
        init_dict[one] = 0
    query = f"""
                SELECT DISTINCT ecn.operations_shift,ops.supervisor_name
                FROM `tabEmployee Checkin`ecn JOIN `tabOperations Shift`ops ON
                ops.name = ecn.operations_shift
                WHERE ecn.date BETWEEN '{filters.get("from_date")}' and '{filters.get("to_date")}'

            """
    result_set = frappe.db.sql(query,as_dict=1)
    if result_set:
        unique_supervisors = list(set([i.supervisor_name for i in result_set]))
        datapack = update_data(unique_supervisors,filters,init_dict,column_names)
        return datapack

def update_data(supervisors,filters,init_dict,column_names):
    # Fill in the first row of nested data
    datapack = []
    # its_fine_pack= init_dict.copy() #Initialize 0 values
    # created_check_pack = init_dict.copy()
    # justification_pack = init_dict.copy()

    for each in supervisors:
        its_fine_pack= init_dict.copy() #Initialize 0 values
        created_check_pack = init_dict.copy()
        justification_pack = init_dict.copy()
        its_fine_pack.update({
            'supervisor_value':"It's Fine",
            'supervisor':each,
            'indent':1})
        created_check_pack.update({
            'supervisor_value':"Ask supervisor for justification",
            'supervisor':each,
               'indent':1,
        })
        justification_pack.update({
            'supervisor_value':"justified",
            'supervisor':each,
            'indent':1,
        })
        daily_count = fetch_daily_count(each,filters)
        created_count,present_count = fetch_created_attendance_check(each,filters)

        its_fine_pack.update(daily_count)
        created_check_pack.update(created_count)
        justification_pack.update(present_count)
        percentage_scores = {}
        for one in created_check_pack:
            if one in column_names.values():
                created_check_pack[one] = int(created_check_pack[one]) - int(justification_pack[one])
                try:
                    percentage_scores[one] = (its_fine_pack[one]/(its_fine_pack[one]+created_check_pack[one]))*100
                    percentage_scores[one] = str(percentage_scores[one])+'%'
                except ZeroDivisionError:
                    percentage_scores[one] = '0%'
        percentage_scores.update({
            'supervisor_value':each
        })
        datapack.append(percentage_scores)
        datapack.append(its_fine_pack)

        datapack.append(created_check_pack)
        datapack.append(justification_pack)



    return datapack



def get_columns(filters):
    #Ensure that the dates follow the correct format
    if getdate(filters.get('from_date')) > getdate(filters.get('to_date')):
        frappe.throw("From date cannot be after To Date")
    columns = [{
            "label": " ",
            "fieldname": 'supervisor_value',
            "fieldtype": "Data",
            "width": 200,
        }]
    daterange = get_date_range(getdate(filters.get('from_date')),getdate(filters.get('to_date')))
    for value in daterange:
        s_date = value.strftime('%d-%b')
        columns.append(
            {
            "label": s_date,
            "fieldname": s_date,
            "fieldtype": "Int",
            "width": 100,
        }
        )
    return columns



def get_date_range(start_date, end_date,as_dict = False):
    dates = [] if not as_dict else {}
    for n in range(int((end_date - start_date).days)):
        if not as_dict:
            dates.append(start_date + timedelta(n))
        else:
            dates[start_date + timedelta(n)]=(start_date + timedelta(n)).strftime('%d-%b')
    if not as_dict:
        dates.append(end_date) if not as_dict else dates.append({end_date:end_date.strftime('%d-%b')})
    else:
        dates[end_date]=(end_date).strftime('%d-%b')

    return dates
