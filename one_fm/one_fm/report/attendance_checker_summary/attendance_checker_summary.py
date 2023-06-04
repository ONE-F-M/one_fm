# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate
from datetime import timedelta, date


def execute(filters=None):
    columns, data = [], []
    columns = get_columns(filters)
    data = fetch_data(filters)
    return columns, data



# {
# 	"label": _("Doctype"),
# 	"fieldname": "doctype",
# 	"fieldtype": "Data",
# 	"width": 180
# 			}


# def set_data_in_value(value,dates,is_total):
#     for one in dates:
#         print(one)
        


def get_row(value,datapack):
    for index, item in enumerate(datapack):
        if item.get('attendance_value') == value:
            return index

def update_data(cur_date,dates,datapack):
    
    value_fields = ['Use the App',"Didn't Use the App",'Justfied','Absent (AB)','Day Off (DO)','Sick Leave (SL)',\
              'Annual Leave (AL)','Work From Home (WFH)','Exited (EX)', "Not Available (NA)"]
    sql_query = f"""SELECT 
                                (Select count(status) from `tabAttendance` where docstatus=1 and status = 'Present' and  attendance_date ='{cur_date}') as present,
                                (Select count(status) from `tabAttendance` where docstatus=1 and status = 'Day Off' and  attendance_date ='{cur_date}') as day_off,
                                (Select count(status) from `tabAttendance` where docstatus=1 and status = 'On Leave' and leave_type ='Sick Leave' and  attendance_date ='{cur_date}') as sick_leave,
                                (Select count(status) from `tabAttendance` where docstatus=1 and status = 'On Leave' and leave_type ='Annual Leave' and  attendance_date ='{cur_date}') as annual_leave,
                                (Select count(status) from `tabAttendance` where docstatus=1 and status = 'Work From Home'  and  attendance_date ='{cur_date}') as work_from_home
                """
    sql_result = frappe.db.sql(sql_query,as_dict=1)
    for one in value_fields:
        if (datapack):
            index = get_row(one,datapack)
            if index not in [None]:
                data_dict = datapack[index]
            else:
                data_dict = {
                        'attendance_value':one,
                        'parent':'Total',
                        'indent':1
                        }
            if one == "Use the App" and sql_result:
                data_dict[dates[cur_date]] = sql_result[0].present
            elif one == "Day Off (DO)" and sql_result:
                data_dict[dates[cur_date]] = sql_result[0].day_off
            if index  or data_dict:
                if index not in [None]:
                    datapack[index] = data_dict
                elif data_dict:
                    datapack.append(data_dict)
                
        else:
            data_dict = {}
            data_dict = {
                        'attendance_value':one,
                        'parent':'Total',
                        'indent':1
                        }
            if one == "Use the App" and sql_result:
                data_dict[dates[cur_date]] = sql_result[0].present
            elif one == 'Day Off (DO)' and sql_result:
                data_dict[dates[cur_date]] = sql_result[0].day_off
        
            datapack.append(data_dict)
                
        
    return datapack
        


def fetch_data(filters):
    datapack = [] 
    column_names = get_date_range(getdate(filters.get('from_date')),getdate(filters.get('to_date')),as_dict=1)
    for each in column_names:
        datapack=update_data(each,column_names,datapack)
    return datapack
        
    

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
    
        


def get_columns(filters):
    #Ensure that the dates follow the correct format
    if getdate(filters.get('from_date')) > getdate(filters.get('to_date')):
        frappe.throw("From date cannot be after To Date")
    columns = [{
			"label": " ",
			"fieldname": 'attendance_value',
			"fieldtype": "Data",
			"width": 200,
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
        
        
        