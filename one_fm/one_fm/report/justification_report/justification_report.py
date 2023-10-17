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

def fetch_attendance_check_options():
    """Fetch the current options for Attendance Check and Add to the default categories"""
    last_attendance_check = frappe.get_last_doc("Attendance Check")
    if last_attendance_check:
        for each in last_attendance_check.meta.fields:
            if each.label == 'Justification':
                split_list = each.options.split('\n')
                split_list = [each for each in split_list if each]
                return split_list


def fetch_data(filters):
    datapack = [] 
    categories = ["Invalid media content","Mobile isn't supporting the app","Out-of-site location","User not assigned to shift",\
        "No valid reason","Suddenly, the App stop working!","Employees insist that he/she did check in or out","No Justification at all "]
    column_names = get_date_range(getdate(filters.get('from_date')),getdate(filters.get('to_date')),as_dict=1)
    check_options = fetch_attendance_check_options()
    if check_options:
        for each in check_options:
            if each not in categories:
                categories.insert(-1,each)
    for each in column_names:
        datapack=update_data(each,column_names,datapack,categories)
    return datapack
        
def get_row(value,datapack):
    existing = False
    for index, item in enumerate(datapack):
        if item.get('justification_value') == value:
            existing = True
            return [index,datapack]
    if not existing:
        datapack.append({'justification_value':value})
        return [len(datapack)-1,datapack]
    
def update_data(cur_date,column_names,datapack,categories):
    all_justifications = 0
    total_submitted = frappe.db.count('Attendance Check', {'docstatus': 1,'date':cur_date})

    #Get the attendance for each day
    sql_query = f"""
                SELECT justification, count(justification) as count_justification  from `tabAttendance Check` 
                   where docstatus = 1 and justification !=""  and date = "{cur_date}" GROUP BY justification 
                """
    sql_result = frappe.db.sql(sql_query,as_dict=1)
    for one in categories:
        found = False   
        index,datapack = get_row(one,datapack)
        for each in sql_result:
            if each.justification == one:
                found = True
                datapack[index].update({
                    column_names[cur_date]:each.count_justification
                })
                all_justifications+=each.count_justification
        if not found:
            datapack[index].update({
                    column_names[cur_date]:0
                })
        if one == 'No Justification at all ':
            datapack[index].update({
                    column_names[cur_date]:(total_submitted-all_justifications)
                })
            
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
    
def get_date_range(start_date, end_date,as_dict = False):
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