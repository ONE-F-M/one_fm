import frappe
from one_fm.one_fm.page.roster.employee_map  import CreateMap,PostMap
from frappe.utils import getdate, cint, cstr, random_string, now_datetime, data as convert_string_to_datetime
import pandas as pd
from frappe import _
from one_fm.api.v1.utils import response

@frappe.whitelist()
def get_opening_values():
    """
        Get the opening values the roster page
    """
    projects = frappe.db.sql("SELECT name from `tabProject` where status = 'Open' ",as_dict=1)
    shifts = frappe.db.sql("SELECT name from `tabOperations Shift` ",as_dict=1)
    sites = frappe.db.sql("SELECT name from `tabOperations Site` ",as_dict=1)
    employees = frappe.db.sql("SELECT name, employee_name,  designation, department, cell_number from `tabEmployee` where status = 'Active' LIMIT  15 ",as_dict=1)
    return {'projects':projects,'shifts':shifts,'sites':sites,'employees':employees}


@frappe.whitelist()
def get_filtered_values(start_date,end_date,project=None,site=None,shift=None,operations_role=None,limit_start=None,page_length=None):
    import time
    """
        Dynamically return a list of employee data based on selected filters
    """
    try:
        query_dict,post_filters,master_data = {},{},{}
        str_filters = f'es.date between "{start_date}" and "{end_date}"'
        query_dict['shift_working'] = 1
        query_dict['status'] = 'Active'
        if not limit_start:
            limit_start = 0
        if not page_length:
            page_length = 15
        if project:
            query_dict['project'] = project
            post_filters['project'] = project
        if site:
            query_dict['site'] = site
            post_filters['project'] = project
        if shift:
            query_dict['shift'] = shift
            post_filters['project'] = project
        if operations_role:
            query_dict['operations_role']= operations_role
            post_filters['project'] = project
            str_filters +=' and es.operations_role = "{}"'.format(operations_role)
        post_filters.update({'date': ['between', (start_date, end_date)], 'post_status': 'Planned'})
        employees = frappe.get_all("Employee", query_dict, ["employee", "employee_name"], order_by="employee_name asc" ,start=limit_start, page_length=page_length)
        post_filters.pop('operations_role',None)
        if employees:
            basic_ot_roster = CreateMap(start=start_date,end=end_date,employees=employees,filters=str_filters,isOt=None).formated_rs
            the_set = set()
            filtered_dict = {}
            for emp_name, schedule in basic_ot_roster.items():
                emp_op_role = frappe.db.get_value("Shift Assignment", {"employee_name": emp_name}, "operations_role")
                if emp_op_role:
                    role_name = frappe.db.get_value("Operations Role", emp_op_role, "post_name")
                    the_set.add(role_name)
                    if not role_name in filtered_dict.keys():
                        filtered_dict.update({role_name : [dict({emp_name: schedule})]})
                    else:
                        update = dict({emp_name: schedule})
                        filtered_dict[role_name].append(update)
                else:
                    if not "other" in filtered_dict.keys():
                        filtered_dict.update({"other": [dict({emp_name: schedule})]})
                    else:
                        update = dict({emp_name: schedule})
                        filtered_dict["other"].append(update)
            master_data.update({'employees_data': filtered_dict})
            return response("Successful", 200, master_data)
        return response("No Employee fits the query", 200)
            
            
    except:
        frappe.log_error(frappe.get_traceback(),'Roster API Error')


@frappe.whitelist()
def unschedule_staff(employee, start_date, end_date=None, never_end=0):
    if not employee:
        return response("Bad request", 400, None, "Employee ID must be entered")
    
    if not isinstance(employee, str):
        return response("Bad request", 400, None, "Employee ID has to be a string")
    
    check = frappe.get_doc("Employee", employee)
    if not check:
        return response("Bad Request", 400, None, "Employee Does Not Exist")

    try:
        if never_end:
            rosters = frappe.get_all("Employee Schedule", {"employee": employee,"date": ('>=', start_date)})
            for roster in rosters:
                frappe.delete_doc("Employee Schedule", roster.name, ignore_permissions=True)
                frappe.db.commit()
            return response("Success", 200, None, f"Employee Unscheduled Successfully !")
        else:
            if not end_date:
                end_date = start_date
            for date in	pd.date_range(start=start_date, end=end_date):
                if frappe.db.exists("Employee Schedule", {"employee": employee, "date":  cstr(date.date())}):
                    roster = frappe.get_doc("Employee Schedule", {"employee": employee, "date":  cstr(date.date())})
                    frappe.delete_doc("Employee Schedule", roster.name, ignore_permissions=True)
                    frappe.db.commit()
            return response("Success", 200, None, "Employee Unscheduled Successfully !")
    except Exception as e:
        return response("Internal Server Error !", 500, None, e)



@frappe.whitelist()
def schedule_staff(employee, shift, operations_role, start_date, end_date=None, never=0, repeat_days=[], day_off=[]):
    #For each day in the start_date end_date iterable, create an employee schedule for either working or day off
    #depending on if the day falls on a repeat day or day off
    # Key : Monday = 0 ,Sunday = 6

    try:
        if type(start_date) == str:
            start_date = convert_string_to_datetime.get_datetime(start_date).date()
    
        if not end_date and not never:
            end_date = start_date
        
        obj_shift = frappe.get_doc("Operations Shift", shift)
        if not obj_shift:
            return response("Bad Request", 400, None, "Shift Does Not Exist !")

        obj_operations_role = frappe.get_doc("Operations Role", operations_role)
        if not obj_operations_role:
            return response("Bad Request", 400, None, "Operations Role Does Not Exist!")

        if never:
            end_date = cstr(getdate().year) + '-12-31'

        for date in	pd.date_range(start=start_date, end=end_date):
            if getdate(cstr(date.date())).weekday() in repeat_days or getdate(cstr(date.date())).weekday() in day_off :
                if frappe.db.exists("Employee Schedule", {"employee": employee, "date": cstr(date.date())}):
                    roster = frappe.get_doc("Employee Schedule", {"employee": employee, "date": cstr(date.date())})
                else:
                    roster = frappe.new_doc("Employee Schedule")
                    roster.employee = employee
                    roster.date = cstr(date.date())
                if getdate(cstr(date.date())).weekday() in day_off:
                    roster.employee_availability = "Day Off"				
                else:
                    roster.employee_availability = "Working"
                    roster.shift = obj_shift.name
                    roster.operations_role = obj_operations_role.name
                roster.save(ignore_permissions=True)
                frappe.db.commit()
        return True
    except Exception as e:
        return response("Internal Server Error !", 500, None, e)


