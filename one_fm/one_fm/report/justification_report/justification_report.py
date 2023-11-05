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
    categories = ["Invalid media content","Mobile isn't supporting the app","Out-of-site location","User not assigned to shift",\
        "No valid reason","Suddenly, the App stop working!","Employees insist that he/she did check in or out","No Justification at all "]
    column_names = get_date_range(getdate(filters.get('from_date')),getdate(filters.get('to_date')),as_dict=1)
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