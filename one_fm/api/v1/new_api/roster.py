import frappe
from one_fm.one_fm.page.roster.employee_map  import CreateMap,PostMap
from frappe.utils import getdate, cint, cstr, random_string, now_datetime
import pandas as pd
from frappe import _

@frappe.whitelist()
def get_opening_values():
    """
        Get the opening values the roster page
    """
    projects = frappe.db.sql("SELECT name from `tabProject` where status = 'Open' ",as_dict=1)
    shifts = frappe.db.sql("SELECT name from `tabOperations Shift` ",as_dict=1)
    sites = frappe.db.sql("SELECT name from `tabOperations Site` ",as_dict=1)
    employees = frappe.db.sql("SELECT name from `tabEmployee` where status = 'Active' LIMIT  15 ",as_dict=1)
    return {'projects':projects,'shifts':shifts,'sites':sites,'employees':employees}


@frappe.whitelist()
def get_filtered_values(start_date,end_date,project=None,site=None,shift=None,operations_role=None,limit_start=None,page_length=None):
    import time
    """
        Dynamically return a list of employee data based on selected filters
    """
    try:
        t1 = time.time()
        query_dict,post_filters,master_data = {},{},{}
        str_filters = f'es.date between "{start_date}" and "{end_date}"'
        query_dict['shift_working'] = 1
        query_dict['status'] = 'Active'
        if not limit_start:
            limit_start = 0
        if not page_length:
            page_length = 10
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
        operations_roles_list = frappe.db.get_all("Post Schedule", post_filters, ["distinct operations_role", "post_abbrv"])
        employees = frappe.get_all("Employee", query_dict, ["employee", "employee_name"], order_by="employee_name asc" ,start=limit_start, page_length=page_length)
        post_filters.pop('operations_role',None)
        if employees:
            t2 = time.time()
            basic_ot_roster = CreateMap(start=start_date,end=end_date,employees=employees,filters=str_filters,isOt=None)
            master_data.update({'employees_data': basic_ot_roster.formated_rs})
            return master_data
            
            
    except:
        frappe.log_error(frappe.get_traceback(),'Roster API Error')


@frappe.whitelist()
def unschedule_staff(employee, start_date, end_date=None, never_end=0):
    try:
        if never_end:
            rosters = frappe.get_all("Employee Schedule", {"employee": employee,"date": ('>=', start_date)})
            for roster in rosters:
                frappe.delete_doc("Employee Schedule", roster.name, ignore_permissions=True)
            return True
        else:
            for date in	pd.date_range(start=start_date, end=end_date):
                if frappe.db.exists("Employee Schedule", {"employee": employee, "date":  cstr(date.date())}):
                    roster = frappe.get_doc("Employee Schedule", {"employee": employee, "date":  cstr(date.date())})
                    frappe.delete_doc("Employee Schedule", roster.name, ignore_permissions=True)
            return True
    except Exception as e:
        print(e)
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def schedule_staff_(employee, shift, operations_role, start_date, end_date=None, repeat_days=[], day_off=[]):
    #For each day in the start_date end_date iterable, create an employee schedule for either working or day off
    #depending on if the day falls on a repeat day or day off
    # Key : Monday = 0 ,Sunday = 6
    try:
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
                    roster.shift = shift
                    roster.operations_role = operations_role

                roster.save(ignore_permissions=True)
                return True
            

    except Exception as e:
        frappe.log_error(e)
        frappe.throw(_(e))



@frappe.whitelist()
def schedule_staff(employee, shift, operations_role, start_date, end_date=None, never=0, day_off=None):
    try:
        
        # print(employee, shift, operations_role, start_date, end_date=None, never=0, day_off=None)
        if never:
            end_date = cstr(getdate().year) + '-12-31'
            print(end_date)
            for date in	pd.date_range(start=start_date, end=end_date):
                if frappe.db.exists("Employee Schedule", {"employee": employee, "date": cstr(date.date())}):
                    roster = frappe.get_doc("Employee Schedule", {"employee": employee, "date": cstr(date.date())})
                else:
                    roster = frappe.new_doc("Employee Schedule")
                    roster.employee = employee
                    roster.date = cstr(date.date())

                if day_off and date.date().strftime('%A') == day_off:
                    roster.employee_availability = "Day Off"				
                else:
                    roster.employee_availability = "Working"
                    roster.shift = shift
                    roster.operations_role = operations_role
                
                roster.save(ignore_permissions=True)
            return True
        else:		
            for date in	pd.date_range(start=start_date, end=end_date):
                if frappe.db.exists("Employee Schedule", {"employee": employee, "date":  cstr(date.date())}):
                    roster = frappe.get_doc("Employee Schedule", {"employee": employee, "date":  cstr(date.date())})
                else:
                    roster = frappe.new_doc("Employee Schedule")
                    roster.employee = employee
                    roster.date =  cstr(date.date())
                if day_off and date.date().strftime('%A') == day_off:
                    roster.employee_availability = "Day Off"				
                else:
                    roster.employee_availability = "Working"
                    roster.shift = shift
                    roster.operations_role = operations_role
                    roster.operations_role = operations_role
                print(roster.as_dict())
                roster.save(ignore_permissions=True)
            return True
    except Exception as e:
        frappe.log_error(e)
        frappe.throw(_(e))


