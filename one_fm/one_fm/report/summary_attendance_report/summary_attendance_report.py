# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
import time
from frappe import _
from frappe.utils import getdate
from datetime import timedelta, date


def execute(filters=None):
    columns, data = [], []
    columns = get_columns(filters)
    data = fetch_data(filters)
    return columns, data

def use_the_app(date):
    sql_result = frappe.db.sql(f"SELECT  employee from  `tabEmployee Checkin` where date = '{date}'",as_dict=1)
    if sql_result:
        employees=[each.employee for each in sql_result]
        employees_set = set(employees) # remove duplicates
        employee_list = list(employees_set)
        return len(employee_list)
    else:
        return 0
    

def fetch_no_checkin(date,active_employees):
    sql_result = frappe.db.sql(f"SELECT  employee from  `tabEmployee Checkin` where date = '{date}'",as_dict=1)
    if sql_result:
        employees=[each.employee for each in sql_result]
        employees_set = set(employees) # remove duplicates
        employee_list = list(employees_set)
        # checkin_employees = [i.employee for i in sql_result]
        no_checkin_employees =  [one for one in active_employees if one not in employee_list]
        return len(no_checkin_employees)
    return 0
        



def get_not_applicable(date,active_employees):
    shift_employees = get_assigned_shift(date)
    schedule_employees = get_scheduled_employees(date)
    result_set = [e for e in active_employees if e not in shift_employees and e not in schedule_employees]
    return len(result_set)


def get_scheduled_employees(date):
    value = frappe.db.sql(f"""SELECT DISTINCT employee from `tabEmployee Schedule` where date = '{date}'  """,as_dict=1)
    return [each.employee for each in value] if value else list() 
    

def get_assigned_shift(date):
    value = frappe.db.sql(f"""SELECT DISTINCT employee from `tabShift Assignment` where start_date = '{date}'  """,as_dict=1)
    return [each.employee for each in value] if value else list() 


def get_exited_employees(date):
    # Get the count of justified records from that date
    sql_result = frappe.db.sql(f"""SELECT Count(name) as exited from `tabEmployee` where status = 'Left' and relieving_date = '{date}' """,as_dict = 1)
    if sql_result:
        return sql_result[0].get('exited')
    else:
        return 0
    


def get_row(value,datapack):
    for index, item in enumerate(datapack):
        if item.get('attendance_value') == value:
            return index
        

def get_justified(selected_date):
    #Get the count of justified records from that date
    sql_result = frappe.db.sql(f"""SELECT Count(justification) as c_justification from `tabAttendance Check` where docstatus = 1 and date = '{selected_date}' and justification IS NOT NULL""",as_dict = 1)
    if sql_result:
        return sql_result[0].get('c_justification')
    return 0




def update_data(cur_date,dates,datapack,active_employees):
    day_values = {}
    value_fields = ['Use the App','Justified','Absent (AB)','Day Off (DO)','Sick Leave (SL)',\
              'Annual Leave (AL)','Work From Home (WFH)','Exited (EX)',"NA","Didn't Use the App"]
    #Get the attendance for each day
    sql_query = f"""SELECT 
                                (Select count(status) from `tabAttendance` where docstatus=1 and status = 'Present' and  attendance_date ='{cur_date}') as present,
                                (Select count(attendance_status) from `tabAttendance Check` where docstatus=1 and attendance_status = 'Absent' and  date ='{cur_date}') as absent,
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
                data_dict[dates[cur_date]] = use_the_app(cur_date)
                day_values['present'] = data_dict[dates[cur_date]]
            elif one == "Absent (AB)" and sql_result:
                data_dict[dates[cur_date]] = int(sql_result[0].absent)
                day_values['absent'] = int(sql_result[0].absent)
            elif one == "Day Off (DO)" and sql_result:
                data_dict[dates[cur_date]] = int(sql_result[0].day_off)
                day_values['day_off'] = int(sql_result[0].day_off)
            elif one == "Sick Leave (SL)" and sql_result:
                data_dict[dates[cur_date]] = int(sql_result[0].sick_leave)
                day_values['sick_leave'] = int(sql_result[0].sick_leave)
            elif one == "Annual Leave (AL)" and sql_result:
                data_dict[dates[cur_date]] = int(sql_result[0].annual_leave)
                day_values['annual_leave'] = int(sql_result[0].annual_leave)
            elif one == "Work From Home (WFH)" and sql_result:
                data_dict[dates[cur_date]] =int(sql_result[0].work_from_home)
                day_values['work_from_home'] = int(sql_result[0].work_from_home)
            elif one == "Justified" and sql_result:
                data_dict[dates[cur_date]] = get_justified(cur_date)
                day_values['justified'] = get_justified(cur_date)
            elif one == "Exited (EX)" and sql_result:
                data_dict[dates[cur_date]] = get_exited_employees(cur_date)
                day_values['exited'] = get_exited_employees(cur_date)
            elif one == "NA" and sql_result:
                data_dict[dates[cur_date]] = get_not_applicable(cur_date,active_employees)
                day_values['na'] = data_dict[dates[cur_date]]
            elif one == "Didn't Use the App" and sql_result:
                data_dict[dates[cur_date]] = get_no_app_use(day_values,cur_date,active_employees)
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
                data_dict[dates[cur_date]] = use_the_app(cur_date)
                day_values['present'] = data_dict[dates[cur_date]]
            
        
            datapack.append(data_dict)
                
        
    return datapack
        
        

def get_no_app_use(day_values,cur_date,active_employees):
    
    no_app = fetch_no_checkin(cur_date,active_employees)    
    return (no_app-(day_values.get('justified',0)+day_values.get('day_off',0)+day_values.get('work_from_home',0)+day_values.get('absent',0)+day_values.get('annual_leave',0)+day_values.get('sick_leave',0)+day_values.get('exited',0)+day_values.get('na',0)))




def fetch_data(filters):
    active_employee = frappe.get_list("Employee", {"status":"Active"},['name'])
    active_employees = [emp.name for emp in active_employee]
    datapack = [] 
    column_names = get_date_range(getdate(filters.get('from_date')),getdate(filters.get('to_date')),as_dict=1)
    for each in column_names:
        datapack=update_data(each,column_names,datapack,active_employees)
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
        
        
        