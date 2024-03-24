from pandas.core.indexes.datetimes import date_range
from frappe.utils import validate_phone_number
from datetime import datetime
from one_fm.one_fm.page.roster.employee_map  import CreateMap,PostMap
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate, now
import pandas as pd, numpy as np
from frappe import _
import json, multiprocessing, os, time, itertools, frappe
from multiprocessing.pool import ThreadPool as Pool
from itertools import product
from one_fm.api.notification import create_notification_log
from one_fm.api.v2.utils import response
from one_fm.utils import query_db_list
from calendar import day_name
from one_fm.operations.doctype.operations_shift.operations_shift import get_active_supervisor




@frappe.whitelist()
def assign_staff(employees, shift, request_employee_assignment=None):
    if not employees:
        response("Bad Request", 400, None, 'Please select employees first')

    validation_logs = []
    user, user_roles, user_employee = get_current_user_details()
    shift, site, project = frappe.db.get_value("Operations Shift", shift, ['name', 'site', 'project'])
    if not cint(request_employee_assignment):
        for emp in json.loads(employees):
            emp_project, emp_site, emp_shift = frappe.db.get_value("Employee", emp, ["project", "site", "shift"])
            

    if len(validation_logs) > 0:
        frappe.log_error(str(validation_logs))
        response("Internal Server Error", 500, None, str(validation_logs) )
        
    else:
        try:
            start = time.time()
            for employee in json.loads(employees):
                if not cint(request_employee_assignment):
                    frappe.enqueue(assign_job, employee=employee, shift=shift, site=site, project=project, is_async=True, queue="long")
                else:
                    emp_project, emp_site, emp_shift = frappe.db.get_value("Employee", employee, ["project", "site", "shift"])
                    site, project = frappe.get_value("Operations Shift", shift, ["site", "project"])
                    if emp_project != project or emp_site != site or emp_shift != shift:
                        frappe.enqueue(create_request_employee_assignment, employee=employee, from_shift=emp_shift, to_shift=shift, is_async=True, queue="long")
            frappe.enqueue(update_roster, key="staff_view", is_async=True, queue="long")
            end = time.time()

            response("Success", 200, {'message':'Shift changed successfully.'})

        except Exception as e:
            frappe.log_error(str(e))
            response("Internal Server Error", 500, None,str(e))


def update_employee_record(employee:dict):
    """summary
     Update the cell number and enrolled details for employee
    Args:
        employee (_type_): dict
    """
    if frappe.db.exists("Employee",employee.get('employee')):
        if employee.get('enrolled') in [0,1]:
            frappe.db.set_value("Employee",employee.get('employee'),'enrolled',employee.get('enrolled') or 0)
        if employee.get('cell_number'):
            frappe.db.set_value("Employee",employee.get('employee'),'cell_number',employee.get('cell_number'))
            if frappe.db.get_value("Employee",employee.get('employee'),'user_id'):
                user_id = frappe.db.get_value("Employee",employee.get('employee'),'user_id')
                frappe.db.set_value("User",user_id,'mobile_no',employee.get('cell_number'))
                frappe.db.set_value("User",user_id,'phone',employee.get('cell_number'))
        frappe.db.commit()
    else:
        response("Resource not found",'404',None,"Employee {}  not found".format(employee.get('employee')))

@frappe.whitelist()
def change_employee_detail(employees:str,field:str=None,value=None)-> bool:
    """ summary
        Update the Employee and User record of a employee
    Args:
        employee (str): Employee ID or Name
        field (str): Field to be changed
        value (str): new value of field
    Returns:
        bool: Returns true if the data was changed successfully.
    """
    
    accepted_fields = ['enrolled','cell_number']
    if not isinstance(employees, str):
        response("Bad Request", 400, None, "Employee value must of type str.")
    
    try:
        employee_json = json.loads(employees)
        if employee_json:
            list(map(update_employee_record,employee_json.get('employees')))
            response('Success',200,{'Data Updated Successfully'})
            
    except Exception as e:
        response("error", 500, False, str(e))

@frappe.whitelist(allow_guest=True)
def get_staff(assigned=1, employee_id=None, employee_name=None, company=None, project=None, site=None, shift=None, department=None, designation=None):
    date = cstr(add_to_date(nowdate(), days=1))
    conds = ""

    if employee_name:
        conds += 'and emp.employee_name="{name}" '.format(name=employee_name)
    if department:
        conds += 'and emp.department="{department}" '.format(department=department)
    if designation:
        conds += 'and emp.designation="{designation}" '.format(designation=designation)
    if company:
        conds += 'and emp.company="{company}" '.format(company=company)

    if project:
        conds += 'and emp.project="{project}" '.format(project=project)
    if site:
        conds += 'and emp.site="{site}" '.format(site=site)
    if shift:
        conds += 'and emp.name="{shift}" '.format(shift=shift)

    if not cint(assigned):
        data = frappe.db.sql("""
            select
                distinct emp.name, emp.employee_id, emp.employee_name, emp.image, emp.one_fm_nationality as nationality, usr.mobile_no, usr.name as email, emp.designation, emp.department, emp.project
            from `tabEmployee` as emp, `tabUser` as usr
            where
            emp.project is NULL
            and emp.site is NULL
            and emp.shift is NULL
            and emp.user_id=usr.name
            {conds}
        """.format(date=date, conds=conds), as_dict=1)
        return data

    data = frappe.db.sql("""
        select
            distinct emp.name, emp.employee_id, emp.employee_name, emp.image, emp.one_fm_nationality as nationality, usr.mobile_no, usr.name as email, emp.designation, emp.department, emp.shift, emp.site, emp.project
        from `tabEmployee` as emp, `tabUser` as usr
        where
        emp.project is not NULL
        and emp.site is not NULL
        and emp.shift is not NULL
        and emp.user_id=usr.name
        {conds}
    """.format(date=date, conds=conds), as_dict=1)
    return data

@frappe.whitelist(allow_guest=True)
def get_staff_filters_data():
    company = frappe.get_list("Company", limit_page_length=9999, order_by="name asc")
    projects = frappe.get_list("Project", limit_page_length=9999, order_by="name asc")
    sites = frappe.get_list("Operations Site", limit_page_length=9999, order_by="name asc")
    shifts = frappe.get_list("Operations Shift", limit_page_length=9999, order_by="name asc")
    departments = frappe.get_list("Department", limit_page_length=9999, order_by="name asc")
    designations = frappe.get_list("Designation", limit_page_length=9999, order_by="name asc")

    return {
        "company": company,
        "projects": projects,
        "sites": sites,
        "shifts": shifts,
        "departments": departments,
        "designations": designations
    }


@frappe.whitelist()
def get_roster_view(start_date: str, end_date: str, assigned: int = 0, scheduled: int = 0, employee_search_id: str = None, 
        employee_search_name: str = None, project: str = None, site: str = None, shift: str = None, department: str = None, 
        operations_role: str = None, designation: str = None, isOt: str = None, limit_start: int = 0, limit_page_length: int  = 9999) -> dict:
    try:
        master_data, formatted_employee_data, post_count_data, employee_filters, additional_assignment_filters={}, {}, {}, {}, {}
        operations_roles_list = []
        employees = []
        
        filters = {
            'date': ['between', (start_date, end_date)]
        }
        str_filters = f'es.date between "{start_date}" and "{end_date}"'

        if operations_role:
            filters.update({'operations_role': operations_role})
            str_filters +=' and es.operations_role = "{}"'.format(operations_role)

        if employee_search_id:
            employee_filters.update({'employee_id': employee_search_id})

        if employee_search_name:
            employee_filters.update({'employee_name': ("like", "%" + employee_search_name + "%")})
            additional_assignment_filters.update({'employee_name': ("like", "%" + employee_search_name + "%")})
        if project:
            employee_filters.update({'project': project})
            additional_assignment_filters.update({'project': project})
        if site:
            employee_filters.update({'site': site})
            additional_assignment_filters.update({'site': site})
        if shift:
            employee_filters.update({'shift': shift})
            additional_assignment_filters.update({'shift': shift})
        if department:
            employee_filters.update({'department': department})


        #--------------------- Fetch Employee list ----------------------------#
        if isOt:
            employee_filters.update({'employee_availability' : 'Working'})
            employees = frappe.db.get_list("Employee Schedule", employee_filters, ["distinct employee", "employee_name"], order_by="employee_name asc" ,limit_start=limit_start, limit_page_length=limit_page_length, ignore_permissions=True)
            master_data.update({'total' : len(employees)})
            employee_filters.update({'date': ['between', (start_date, end_date)], 'post_status': 'Planned'})
            employee_filters.pop('employee_availability')
        else:
            employee_filters.update({'status': 'Active'})
            employee_filters.update({'shift_working':'1'})
            if designation:
                employee_filters.update({'designation' : designation})
            employees = frappe.db.get_list("Employee", employee_filters, ["employee", "employee_name", "day_off_category", "number_of_days_off"], order_by="employee_name asc" ,limit_start=limit_start, limit_page_length=limit_page_length, ignore_permissions=True)
            employees_asa = frappe.db.get_list("Additional Shift Assignment", additional_assignment_filters, ["distinct employee", "employee_name"], order_by="employee_name asc" ,limit_start=limit_start, limit_page_length=limit_page_length, ignore_permissions=True)
            if len(employees_asa) > 0:
                employees.extend(employees_asa)
                employees = filter_redundant_employees(employees)
            master_data.update({'total': len(employees)})
            employee_filters.pop('status', None)
            employee_filters.pop('shift_working', None)
            employee_filters.update({'date': ['between', (start_date, end_date)], 'post_status': 'Planned'})

        if employee_search_name:
            employee_filters.pop('employee_name')
        if employee_search_id:
            employee_filters.pop('employee_id')
        if department:
            employee_filters.pop('department', None)
        if operations_role:
            employee_filters.update({'operations_role': operations_role})
        if designation:
            employee_filters.pop('designation', None)

        #------------------- Fetch Operations Roles ------------------------#
        operations_roles_list = frappe.db.get_list("Post Schedule", employee_filters, ["distinct operations_role", "post_abbrv"], ignore_permissions=True)
        if operations_role:
            employee_filters.pop('operations_role', None)
        employee_filters.pop('date')
        employee_filters.pop('post_status')

        #------------------- Fetch Employee Schedule --------------------#
        #The following section creates a iterable that uses the employee name and id as keys and groups  the  employee data fetched in previous queries

        new_map=CreateMap(start=start_date,end=end_date,employees=employees,filters=str_filters,isOt=isOt)
        master_data.update({'employees_data': new_map.formated_rs})

        #----------------- Get Operations Role count and check fill status -------------------#
        post_map = PostMap(start=start_date,end=end_date,operations_roles_list=operations_roles_list,filters=employee_filters)
        master_data.update({'operations_roles_data': post_map.template})
        # format response for flutter
        employees_data = []
        for k, v in master_data['employees_data'].items():
            for record in v:
                employees_data.append(record)
        master_data['employees_data'] = employees_data
        
        # reformat operations role data
        operations_roles_data = []
        for k, v in master_data['operations_roles_data'].items():
            for record in v:
                record['operations_role'] = k
                operations_roles_data.append(record)
        master_data['operations_roles_data'] = operations_roles_data

        response("Success", 200, master_data)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Get Roster View')
        response("Server Error", 500, None, str(e))

def get_active_employees(start_date, end_date, master_data):
    employees = [i.name for i in frappe.db.get_list('Employee', filters={'status': ['!=', 'Left']})]
    employees += [i.name for i in frappe.db.sql("""
        SELECT name FROM `tabEmployee`
        WHERE status='Left' AND relieving_date BETWEEN '{start_date}' AND '{end_date}'""".format(
        start_date=start_date, end_date=end_date), as_dict=1
    )]
    new_employees = {}
    employees_data = master_data.get('employees_data')
    for k, v in employees_data.items():
        if v[0]['employee'] in employees:
            new_employees[k] = v
    master_data['total'] = len(new_employees)
    master_data['employees_data'] = new_employees

    return master_data


def filter_redundant_employees(employees):
    return list({employee['employee']:employee for employee in employees}.values())

@frappe.whitelist(allow_guest=True)
def get_post_view(start_date, end_date,  project=None, site=None, shift=None, operations_role=None, active_posts=1, limit_start=0, limit_page_length=100):

    user, user_roles, user_employee = get_current_user_details()
    if "Operations Manager" not in user_roles and "Projects Manager" not in user_roles and "Site Supervisor" not in user_roles:
        frappe.throw(_("Insufficient permissions for Post View."))

    filters, master_data, post_data = {}, {}, {}
    if project:
        filters.update({'project': project})
    if site:
        filters.update({'site': site})
    if shift:
        filters.update({'site_shift': shift})
    if operations_role:
        filters.update({'post_template': operations_role})
    post_total = len(frappe.db.get_list("Operations Post", filters))
    post_list = frappe.db.get_list("Operations Post", filters, "name", order_by="name asc", limit_start=limit_start, limit_page_length=limit_page_length)
    fields = ['name', 'post', 'operations_role','date', 'post_status', 'site', 'shift', 'project']

    filters.pop('post_template', None)
    filters.pop('site_shift', None)
    if operations_role:
        filters.update({'operations_role': operations_role})
    if shift:
        filters.update({'shift': shift})
    for key, group in itertools.groupby(post_list, key=lambda x: (x['name'])):
        schedule_list = []
        filters.update({'date': ['between', (start_date, end_date)], 'post': key})
        schedules = frappe.db.get_list("Post Schedule", filters, fields, order_by="date asc, post asc")
        for date in	pd.date_range(start=start_date, end=end_date):
            if not any(cstr(schedule.date) == cstr(date).split(" ")[0] for schedule in schedules):
                schedule = {
                'post': key,
                'date': cstr(date).split(" ")[0]
                }
            else:
                schedule = next((sch for sch in schedules if cstr(sch.date) == cstr(date).split(" ")[0]), {})
            schedule_list.append(schedule)
        post_data.update({key: schedule_list})

    master_data.update({"post_data": post_data, "total": post_total})
    return master_data

@frappe.whitelist()
def get_filtered_operations_role(doctype, txt, searchfield, start, page_len, filters):
    shift = filters.get('shift')
    return frappe.db.sql("""
        select distinct name
        from `tabOperations Role`
        where shift="{shift}"
    """.format(shift=shift))


def get_current_user_details():
    user = frappe.session.user
    user_roles = frappe.get_roles(user)
    user_employee = frappe.get_value("Employee", {"user_id": user}, ["name", "employee_id", "employee_name", "image", "enrolled", "designation"], as_dict=1)
    return user, user_roles, user_employee


# @frappe.whitelist()
# def schedule_staff(employees, shift, operations_role, start_date, otRoster=0, project_end_date=0, 
# 	keep_days_off=0, request_employee_schedule=0, day_off_ot=0, end_date=None, repeat_days=[],
# 	day_off=[]):
# 	try:
# 		validation_logs = []
# 		user, user_roles, user_employee = get_current_user_details()
# 		# employees = json.loads(employees)
# 		if not employees:
# 			frappe.throw("Employees must be selected.")
# 		employee_list = []
# 		for i in employees:
# 			if not i['employee'] in employee_list:
# 				employee_list.append(i['employee'])
		
# 		if cint(project_end_date) and not end_date:
# 			project = frappe.db.get_value("Operations Shift", shift, ["project"])
# 			if frappe.db.exists("Contracts", {'project': project}):
# 				contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
# 				if not end_date:
# 					validation_logs.append("Please set contract end date for contract: {contract}".format(contract=contract))
# 			else:
# 				validation_logs.append("No contract linked with project {project}".format(project=project))

# 		elif end_date and not cint(project_end_date):
# 			end_date = end_date

# 		elif not cint(project_end_date) and not end_date:
# 			validation_logs.append("Please set an end date for scheduling the staff.")

# 		elif cint(project_end_date) and end_date:
# 			validation_logs.append("Please select either the project end date or set a custom date. You cannot set both!")

# 		emp_tuple = str(employee_list).replace('[', '(').replace(']',')')
# 		# date_range = pd.date_range(start=start_date, end=end_date)

# 		if not cint(request_employee_schedule) and "Projects Manager" not in user_roles and "Operations Manager" not in user_roles:
# 			all_employee_shift_query = frappe.db.sql("""
# 				SELECT DISTINCT es.shift, s.supervisor
# 				FROM `tabEmployee Schedule` es JOIN `tabOperations Shift` s ON es.shift = s.name
# 				WHERE
# 				es.date BETWEEN '{start_date}' AND '{end_date}'
# 				AND es.employee_availability='Working' AND es.employee IN {emp_tuple}
# 				GROUP BY es.shift
# 			""".format(start_date=start_date, end_date=end_date, emp_tuple=emp_tuple), as_dict=1)

# 			for i in all_employee_shift_query:
# 				if user_employee.name != i.supervisor:
# 					validation_logs.append("You are not authorized to change this schedule. Please check the Request Employee Schedule option to place a request.")
# 					break

# 		if len(validation_logs) > 0:
# 			frappe.log_error(str(validation_logs), 'Roster Schedule')
# 			frappe.throw(str(validation_logs))
# 		else:
# 			# extreme schedule
# 			extreme_schedule(employees=employees, start_date=start_date, end_date=end_date, shift=shift,
# 				operations_role=operations_role, otRoster=otRoster, keep_days_off=keep_days_off, day_off_ot=day_off_ot,
# 				request_employee_schedule=request_employee_schedule, employee_list=employee_list,
# 				repeat_days=repeat_days, day_off=day_off
# 			)
# 			# employees_list = frappe.db.get_list("Employee", filters={"name": ["IN", employees]}, fields=["name", "employee_id", "employee_name"])
# 			update_roster(key="roster_view")
# 			response("success", 200, {'message':'Successfully rostered employees'})
# 	except Exception as e:
# 		frappe.log_error(frappe.get_traceback(), "Schedule Roster")
# 		response("error", 500, None, str(frappe.get_traceback()))


# def update_roster(key):
# 	frappe.publish_realtime(key, "Success")

# def extreme_schedule(employees, shift, operations_role, otRoster, start_date, end_date, keep_days_off, 
# 	day_off_ot, request_employee_schedule, employee_list, repeat_days, day_off):
# 	if not employees:
# 		frappe.msgprint("Please select employees before rostering")
# 		return
# 	creation = now()
# 	owner = frappe.session.user
# 	# date_range = [i.date() for i in pd.date_range(start=start_date, end=end_date)]
# 	operations_shift = frappe.get_doc("Operations Shift", shift, ignore_permissions=True)
# 	operations_role = frappe.get_doc("Operations Role", operations_role, ignore_permissions=True)
# 	day_off_ot = cint(day_off_ot)
# 	if not cint(otRoster) or cint(day_off_ot):
# 		roster_type = 'Basic'
# 	else:
# 		roster_type = 'Over-Time'

# 	# check for end date
# 	if end_date:
# 		end_date = getdate(end_date)
# 		new_employees = []
# 		for i in employees:
# 			if getdate(i['date']) <= end_date:
# 				new_employees.append(i)
# 		if new_employees:
# 			employees = new_employees.copy()
# 	# check keep days_off
# 	if keep_days_off:
# 		days_off_list = frappe.db.get_list("Employee Schedule", filters={
#             'employee':['IN', [i['employee'] for i in employees]],
#             'date': ['IN', [i['date'] for i in employees]],
#             'employee_availability': 'Day Off'
#         }, fields=['name', 'employee', 'date'])
# 		days_off_dict = {}
# 		if days_off_list:
# 			# build a dict in the form {'hr-emp-0002:['2023-01-01,]}
# 			for i in days_off_list:
# 				if days_off_dict.get(i.employee):
# 					days_off_dict[i.employee].append(str(i.date))
# 				else:
# 					days_off_dict[i.employee] = [str(i.date)]
# 			# remove records from employees
# 			new_employees = []
# 			if employees and len(days_off_dict):
# 				for i in employees:
# 					if not (i['date'] in days_off_dict.get(i['employee'])):
# 						new_employees.append(i)
# 				if new_employees:
# 					employees = new_employees.copy()
# 	# # get and structure employee dictionary for easy hashing
# 	employees_list = frappe.db.get_list("Employee", filters={'employee': ['IN', employee_list]}, fields=['name', 'employee_name', 'department'], ignore_permissions=True)
# 	employees_dict = {}
# 	for i in employees_list:
# 		employees_dict[i.name] = i

# 	if not cint(request_employee_schedule):
# 	# 	"""
# 	# 		USE DIRECT SQL TO CREATE ROSTER SCHEDULE.
# 	# 	"""
# 		query = """
# 			INSERT INTO `tabEmployee Schedule` (`name`, `employee`, `employee_name`, `department`, `date`, `shift`, `site`, `project`, `shift_type`, `employee_availability`, 
# 			`operations_role`, `post_abbrv`, `roster_type`, `day_off_ot`, `owner`, `modified_by`, `creation`, `modified`)
# 			VALUES 
# 		"""
# 		if not cint(keep_days_off):
# 			id_list = [] #store for schedules list
# 			for employee in employees:
# 				employee_doc = employees_dict.get(employee['employee'])
# 				name = f"{employee['date']}_{employee['employee']}_{roster_type}"
# 				id_list.append(name)
# 				weekday_check = getdate(employee['date']).weekday()
# 				if weekday_check in repeat_days:
# 					query += f"""
# 					(
# 						"{name}", "{employee['employee']}", "{employee_doc.employee_name}", "{employee_doc.department}", "{employee['date']}", "{operations_shift.name}", 
# 						"{operations_shift.site}", "{operations_shift.project}", '{operations_shift.shift_type}', "Working", 
# 						"{operations_role.name}", "{operations_role.post_abbrv}", "{roster_type}", 
# 						{day_off_ot}, "{owner}", "{owner}", "{creation}", "{creation}"
# 					),"""
# 				elif weekday_check in day_off:
# 					query += f"""
# 						(
# 							"{name}", "{employee['employee']}", "{employee_doc.employee_name}", "{employee_doc.department}", "{employee['date']}", "", 
# 							"", "", '', "Day Off", 
# 							"", "", "{roster_type}", 
# 							{day_off_ot}, "{owner}", "{owner}", "{creation}", "{creation}"
# 						),"""

# 			query = query[:-1]

# 			query += f"""
# 				ON DUPLICATE KEY UPDATE
# 				modified_by = VALUES(modified_by),
# 				modified = "{creation}",
# 				operations_role = VALUES(operations_role),
# 				post_abbrv = VALUES(post_abbrv),
# 				roster_type = VALUES(roster_type),
# 				shift = VALUES(shift),
# 				project = VALUES(project),
# 				site = VALUES(site),
# 				shift_type = VALUES(shift_type),
# 				day_off_ot = VALUES(day_off_ot),
# 				employee_availability = VALUES(employee_availability)
# 			"""
# 			frappe.db.sql(query, values=[], as_dict=1)
# 			frappe.db.commit()
# 		else:
# 			id_list = [] #store for schedules list
# 			for employee in employees:
# 				employee_doc = employees_dict.get(employee['employee'])
# 				name = f"{employee['date']}_{employee['employee']}_{roster_type}"
# 				id_list.append(name)
# 				weekday_check = getdate(employee['date']).weekday()
# 				if weekday_check in repeat_days:
# 					query += f"""
# 					(
# 						"{name}", "{employee['employee']}", "{employee_doc.employee_name}", "{employee_doc.department}", "{employee['date']}", "{operations_shift.name}", 
# 						"{operations_shift.site}", "{operations_shift.project}", '{operations_shift.shift_type}', "Working", 
# 						"{operations_role.name}", "{operations_role.post_abbrv}", "{roster_type}", 
# 						{day_off_ot}, "{owner}", "{owner}", "{creation}", "{creation}"
# 					),"""
# 				elif weekday_check in day_off:
# 					query += f"""
# 						(
# 							"{name}", "{employee['employee']}", "{employee_doc.employee_name}", "{employee_doc.department}", "{employee['date']}", "", 
# 							"", "", '', "Day Off", 
# 							"", "", "{roster_type}", 
# 							{day_off_ot}, "{owner}", "{owner}", "{creation}", "{creation}"
# 						),"""

# 			query = query[:-1]

# 			query += f"""
#                 ON DUPLICATE KEY UPDATE
#                 modified_by = VALUES(modified_by),
#                 modified = "{creation}",
#                 operations_role = VALUES(operations_role),
#                 post_abbrv = VALUES(post_abbrv),
#                 roster_type = VALUES(roster_type),
#                 shift = VALUES(shift),
#                 project = VALUES(project),
#                 site = VALUES(site),
#                 shift_type = VALUES(shift_type),
#                 day_off_ot = VALUES(day_off_ot),
#                 employee_availability = "Working"
#             """
# 			frappe.db.sql(query, values=[], as_dict=1)
# 			frappe.db.commit()
# 	else:
# 		"""
# 			Handle request employee schedule
# 		"""
# 		from_schedule = frappe.db.get_list(
# 			"Employee Schedule",
# 			filters={
# 				"shift": shift,
# 				"date": ["BETWEEN", [start_date, end_date]],
# 				"employee": ["IN", employee_list]
# 			},
# 			fields=["shift", "site", "project", "employee", "employee_name", "operations_role"],
# 			group_by="employee DESC"
# 		)
# 		if len(from_schedule):
# 			if otRoster == 'false':
# 				roster_type = 'Basic'
# 			elif otRoster == 'true':
# 				roster_type = 'Over-Time'
			
# 			requester, requester_name = frappe.db.get_value("Employee", {"user_id":frappe.session.user}, ["name", "employee_name"])
# 			# get required shift supervisors and make as dict for easy hashing
# 			shifts_dataset = frappe.db.get_list("Operations Shift", filters={"name": ["IN", [i.shift for i in from_schedule]]}, fields=["name", "supervisor", "supervisor_name"], order_by="name ASC")
# 			shift_datadict = {}
# 			for i in shifts_dataset:
# 				shift_datadict[i.name] = i
			
# 			for emp in from_schedule:			
# 				req_es_doc = frappe.new_doc("Request Employee Schedule")
# 				req_es_doc.employee = emp.employee
# 				req_es_doc.from_shift = emp.shift
# 				req_es_doc.from_operations_role = emp.operations_role
# 				req_es_doc.to_shift = shift
# 				req_es_doc.to_operations_role = operations_role.name
# 				req_es_doc.start_date = start_date
# 				req_es_doc.end_date = end_date
# 				req_es_doc.roster_type = roster_type
# 				req_es_doc.save(ignore_permissions=True)
# 			frappe.db.commit()
# 			frappe.msgprint("Request Employee Schedule created successfully")

# 	# update employee additional records
# 	frappe.enqueue(update_employee_shift, employees=employees, shift=shift, owner=owner, creation=creation)


@frappe.whitelist()
def schedule_staff(employees, shift, operations_role, start_date, otRoster=0, project_end_date=0, 
	keep_days_off=0, request_employee_schedule=0, day_off_ot=0, end_date=None, repeat_days=[],
	day_off=[]):
    try:
        _start_date = getdate(start_date)
        
        validation_logs = []
        user, user_roles, user_employee = get_current_user_details()
        if not employees:
            frappe.throw("Employees must be selected.")

        employee_list = list({obj["employee"] for obj in employees})
        
        if cint(project_end_date) and not end_date:
            project = frappe.db.get_value("Operations Shift", shift, ["project"])
            if frappe.db.exists("Contracts", {'project': project}):
                contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
                if not end_date:
                    validation_logs.append("Please set contract end date for contract: {contract}".format(contract=contract))
                else:
                    employees = []
                    list_of_date = date_range(start_date, end_date)
                    for obj in employee_list:
                        for day in list_of_date:
                            employees.append({"employee": obj, "date": str(day.date())})

            else:
                validation_logs.append("No contract linked with project {project}".format(project=project))

        elif end_date and not cint(project_end_date):
            end_date = getdate(end_date)
            employees = []
            list_of_date = date_range(start_date, end_date)
            for obj in employee_list:
                for day in list_of_date:
                    employees.append({"employee": obj, "date": str(day.date())})

        # elif not cint(project_end_date) and not end_date:
        #     validation_logs.append("Please set an end date for scheduling the staff.")

        elif cint(project_end_date) and end_date:
            validation_logs.append("Please select either the project end date or set a custom date. You cannot set both!")

        emp_tuple = str(employee_list).replace('[', '(').replace(']',')')
        # date_range = pd.date_range(start=start_date, end=end_date)

        if not cint(request_employee_schedule) and "Projects Manager" not in user_roles and "Operations Manager" not in user_roles:
            all_employee_shift_query = frappe.db.sql("""
                SELECT DISTINCT es.shift, s.employee as supervisor
                    FROM `tabEmployee Schedule` es 
                    JOIN `tabOperations Shift Supervisors` s ON es.shift = s.parent
                    JOIN (
                        SELECT parent, MIN(hierarchy) as max_hierarchy
                        FROM `tabOperations Shift Supervisors`
                        GROUP BY parent
                    ) max_hierarchies ON s.parent = max_hierarchies.parent AND s.hierarchy = max_hierarchies.max_hierarchy
                    WHERE
                        es.date BETWEEN '{start_date}' AND '{end_date}'
                        AND es.employee_availability = 'Working' AND es.employee IN {emp_tuple}
                    GROUP BY es.shift
                    ORDER BY s.hierarchy
            """.format(start_date=start_date, end_date=end_date, emp_tuple=emp_tuple), as_dict=1)

            # for i in all_employee_shift_query:
            #     if user_employee.name != i.supervisor:
            #         validation_logs.append("You are not authorized to change this schedule. Please check the Request Employee Schedule option to place a request.")
            #         break

        if len(validation_logs) > 0:
            frappe.log_error(str(validation_logs), 'Roster Schedule')
            frappe.throw(str(validation_logs))
        else:
            # extreme schedule
            resp = extreme_schedule(employees=employees, start_date=start_date, end_date=end_date, shift=shift,
                operations_role=operations_role, otRoster=otRoster, keep_days_off=keep_days_off, day_off_ot=day_off_ot,
                request_employee_schedule=request_employee_schedule, employee_list=employee_list, repeat_days=repeat_days, day_off=day_off
            )
            # employees_list = frappe.db.get_list("Employee", filters={"name": ["IN", employees]}, fields=["name", "employee_id", "employee_name"])
            update_roster(key="roster_view")
            print(resp)
            if type(resp) == dict:
                resp = frappe._dict(resp)
                response("success", 200, {'message':'Successfully rostered employees'})
            response(resp.status, resp.code, resp.data)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Schedule Roster")
        response("error", 500, None, str(e))

def update_roster(key):
    frappe.publish_realtime(key, "Success")


def extreme_schedule(employees, shift, operations_role, otRoster, start_date, end_date, keep_days_off, day_off_ot, 
    request_employee_schedule, employee_list, repeat_days=[],
	day_off=[]):
    if not employees:
        frappe.throw("Please select employees before rostering")
        return
    creation = now()
    owner = frappe.session.user
    # date_range = [i.date() for i in pd.date_range(start=start_date, end=end_date)]
    operations_shift = frappe.get_doc("Operations Shift", shift, ignore_permissions=True)
    operations_role = frappe.get_doc("Operations Role", operations_role, ignore_permissions=True)
    day_off_ot = cint(day_off_ot)
    if otRoster == 0:
        roster_type = 'Basic'
    elif otRoster == 1 or day_off_ot == 1:
        roster_type = 'Over-Time'

    # check for start and enddate
    if end_date:
        end_date = getdate(end_date)
        new_employees = []
        for i in employees:
            if getdate(i['date']) <= end_date:
                new_employees.append(i)
        if new_employees:
            employees = new_employees.copy()
    # check keep days_off
    if keep_days_off:
        days_off_list = frappe.db.get_list("Employee Schedule", filters={
            'employee':['IN', [i['employee'] for i in employees]],
            'date': ['IN', [i['date'] for i in employees]],
            'employee_availability': 'Day Off'
        }, fields=['name', 'employee', 'date'])
        days_off_dict = {}
        if days_off_list:
            # build a dict in the form {'hr-emp-0002:['2023-01-01,]} 
            for i in days_off_list:
                if days_off_dict.get(i.employee):
                    days_off_dict[i.employee].append(str(i.date))
                else:
                    days_off_dict[i.employee] = [str(i.date)]
            # remove records from employees
            new_employees = []
            if employees and len(days_off_dict):
                for i in employees:
                    if not (i['date'] in days_off_dict.get(i['employee'])):
                        new_employees.append(i)
                if new_employees:
                    employees = new_employees.copy()
    
    # # get and structure employee dictionary for easy hashing
    employees_list = frappe.db.get_list("Employee", filters={'employee': ['IN', employee_list]}, fields=['name', 'employee_name', 'department'], ignore_permissions=True)
    employees_dict = {}
    for i in employees_list:
        employees_dict[i.name] = i
    
    if not cint(request_employee_schedule):
    # 	"""
    # 		USE DIRECT SQL TO CREATE ROSTER SCHEDULE.
    # 	"""
        query = """
            INSERT INTO `tabEmployee Schedule` (`name`, `employee`, `employee_name`, `department`, `date`, `shift`, `site`, `project`, `shift_type`, `employee_availability`, 
            `operations_role`, `post_abbrv`, `roster_type`, `day_off_ot`, `owner`, `modified_by`, `creation`, `modified`)
            VALUES 
        """
        query_body = """"""
        if not cint(keep_days_off):
            id_list = [] #store for schedules list
            for employee in employees:
                employee_doc = employees_dict.get(employee['employee'])
                name = f"{employee['date']}_{employee['employee']}_{roster_type}"
                id_list.append(name)
                if not repeat_days and not day_off:
                    query_body += f"""
                    (
                        "{name}", "{employee['employee']}", "{employee_doc.employee_name}", "{employee_doc.department}", "{employee['date']}", "{operations_shift.name}", 
                        "{operations_shift.site}", "{operations_shift.project}", '{operations_shift.shift_type}', "Working", 
                        "{operations_role.name}", "{operations_role.post_abbrv}", "{roster_type}", 
                        {day_off_ot}, "{owner}", "{owner}", "{creation}", "{creation}"
                    ),"""
                    query_exists = True
                else:
                    weekday_check = getdate(employee['date']).weekday()
                    if weekday_check in repeat_days:
                        query_body += f"""
                        (
                            "{name}", "{employee['employee']}", "{employee_doc.employee_name}", "{employee_doc.department}", "{employee['date']}", "{operations_shift.name}", 
                            "{operations_shift.site}", "{operations_shift.project}", '{operations_shift.shift_type}', "Working", 
                            "{operations_role.name}", "{operations_role.post_abbrv}", "{roster_type}", 
                            {day_off_ot}, "{owner}", "{owner}", "{creation}", "{creation}"
                        ),"""
                    elif weekday_check in day_off:
                        query_body += f"""
                            (
                                "{name}", "{employee['employee']}", "{employee_doc.employee_name}", "{employee_doc.department}", "{employee['date']}", "", 
                                "", "", '', "Day Off", 
                                "", "", "{roster_type}", 
                                {day_off_ot}, "{owner}", "{owner}", "{creation}", "{creation}"
                            ),"""
            if query_body:
                query_body = query_body[:-1]
                query = query + query_body
            else:
                return {'status':"success", 'code':200, 'data':{'message':'No schedule created because selected dates is not in repeat_days or day_off'}}
            
            query += f"""
                ON DUPLICATE KEY UPDATE
                modified_by = VALUES(modified_by),
                modified = "{creation}",
                operations_role = VALUES(operations_role),
                post_abbrv = VALUES(post_abbrv),
                roster_type = VALUES(roster_type),
                shift = VALUES(shift),
                project = VALUES(project),
                site = VALUES(site),
                shift_type = VALUES(shift_type),
                day_off_ot = VALUES(day_off_ot),
                employee_availability = "Working"
            """
            # frappe.log_error(query, 'ROSTER QUERY')
            frappe.db.sql(query, values=[], as_dict=1)
            frappe.db.commit()
        else:
            id_list = [] #store for schedules list
            for employee in employees:
                employee_doc = employees_dict.get(employee['employee'])
                name = f"{employee['date']}_{employee['employee']}_{roster_type}"
                id_list.append(name)
                if not repeat_days and not day_off:
                    query_body += f"""
                    (
                        "{name}", "{employee['employee']}", "{employee_doc.employee_name}", "{employee_doc.department}", "{employee['date']}", "{operations_shift.name}", 
                        "{operations_shift.site}", "{operations_shift.project}", '{operations_shift.shift_type}', "Working", 
                        "{operations_role.name}", "{operations_role.post_abbrv}", "{roster_type}", 
                        {day_off_ot}, "{owner}", "{owner}", "{creation}", "{creation}"
                    ),"""
                else:
                    weekday_check = getdate(employee['date']).weekday()
                    if weekday_check in repeat_days:
                        query_body += f"""
                        (
                            "{name}", "{employee['employee']}", "{employee_doc.employee_name}", "{employee_doc.department}", "{employee['date']}", "{operations_shift.name}", 
                            "{operations_shift.site}", "{operations_shift.project}", '{operations_shift.shift_type}', "Working", 
                            "{operations_role.name}", "{operations_role.post_abbrv}", "{roster_type}", 
                            {day_off_ot}, "{owner}", "{owner}", "{creation}", "{creation}"
                        ),"""
                    elif weekday_check in day_off:
                        query_body += f"""
                            (
                                "{name}", "{employee['employee']}", "{employee_doc.employee_name}", "{employee_doc.department}", "{employee['date']}", "", 
                                "", "", '', "Day Off", 
                                "", "", "{roster_type}", 
                                {day_off_ot}, "{owner}", "{owner}", "{creation}", "{creation}"
                            ),"""

            if query_body:
                query_body = query_body[:-1]
                query = query + query_body
            else:
                return {'status':"success", 'code':200, 'data':{'message':'No schedule created because selected dates is not in repeat_days or day_off'}}
                
            
            query += f"""
                ON DUPLICATE KEY UPDATE
                modified_by = VALUES(modified_by),
                modified = "{creation}",
                operations_role = VALUES(operations_role),
                post_abbrv = VALUES(post_abbrv),
                roster_type = VALUES(roster_type),
                shift = VALUES(shift),
                project = VALUES(project),
                site = VALUES(site),
                shift_type = VALUES(shift_type),
                day_off_ot = VALUES(day_off_ot),
                employee_availability = "Working"
            """
            # frappe.log_error(query, 'ROSTER QUERY')
            frappe.db.sql(query, values=[], as_dict=1)
            frappe.db.commit()
    else:
        """
            Handle request employee schedule
        """
        from_schedule = frappe.db.get_list(
            "Employee Schedule",
            filters={
                "shift": shift,
                "date": ["BETWEEN", [start_date, end_date]],
                "employee": ["IN", employee_list]
            },
            fields=["shift", "site", "project", "employee", "employee_name", "operations_role"],
            group_by="employee DESC"
        )
        if len(from_schedule):
            if otRoster == 'false':
                roster_type = 'Basic'
            elif otRoster == 'true':
                roster_type = 'Over-Time'
            
            requester, requester_name = frappe.db.get_value("Employee", {"user_id":frappe.session.user}, ["name", "employee_name"])
            # get required shift supervisors and make as dict for easy hashing
            shifts_dataset = frappe.db.get_list("Operations Shift", filters={"name": ["IN", [i.shift for i in from_schedule]]}, fields=["name"], order_by="name ASC")
            shift_datadict = {}
            for i in shifts_dataset:
                shift_datadict[i.name] = i
            
            for emp in from_schedule:			
                req_es_doc = frappe.new_doc("Request Employee Schedule")
                req_es_doc.employee = emp.employee
                req_es_doc.from_shift = emp.shift
                req_es_doc.from_operations_role = emp.operations_role
                req_es_doc.to_shift = shift
                req_es_doc.to_operations_role = operations_role.name
                req_es_doc.start_date = start_date
                req_es_doc.end_date = end_date
                req_es_doc.roster_type = roster_type
                req_es_doc.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.msgprint("Request Employee Schedule created successfully")

    # update employee additional records
    frappe.enqueue(update_employee_shift, employees=employees, shift=shift, owner=owner, creation=creation)
    return {'status':"success", 'code':200, 'data':{'message':'Roster scheduled successfully.'}}

def update_employee_shift(employees, shift, owner, creation):
    """Update employee assignment"""

    site, project = frappe.get_value("Operations Shift", shift, ["site", "project"])
    # structure employee record
    # filter and sort, check if employee site and project match retrieved
    employees_data = frappe.db.get_list("Employee", filters={"name": ["IN", employees]}, fields=["name", "employee_name", "employee_id", "project", "site", "shift"])
    unmatched_record = {}
    matched_record = []
    no_shift_assigned = []
    for emp in employees_data:
        if emp.project and emp.project != project or emp.site and emp.site != site or emp.shift and emp.shift != shift:
            unmatched_record[emp.name] = emp
        elif emp.project == project and emp.site == site and emp.shift == shift:
            matched_record.append(emp.name)
        else:
            no_shift_assigned.append(emp.name)


    # start with unmatched
    if unmatched_record:
        query = """
            INSERT INTO `tabAdditional Shift Assignment` (`name`, `employee`, `employee_name`, `employee_id`, `site`, `shift`, `project`, `owner`, `modified_by`, `creation`, `modified`)
            VALUES 
        """
        for k, emp in unmatched_record.items():
            query += f"""(
                    "{emp.name}|{shift}", "{emp.name}", "{emp.employee_name}", "{emp.employee_id}", "{site}", "{shift}", 
                    "{project}", "{owner}", "{owner}", "{creation}", "{creation}"
            ),"""
        query = query.replace(", None", '')
        query = query[:-1]
        query += """
            ON DUPLICATE KEY UPDATE
            project = VALUES(project),
            site = VALUES(site),
            shift = VALUES(shift),
            modified_by = VALUES(modified_by),
            modified = VALUES(modified)
        """
        frappe.db.sql(query)

    if matched_record:
        frappe.db.delete("Additional Shift Assignment", {
            "employee": ["IN", matched_record]
        })

    if no_shift_assigned:
        for employee in no_shift_assigned:
            """ This function updates the employee project, site and shift in the employee doctype """
            frappe.db.set_value("Employee", employee, {"project":project, "site":site, "shift":shift})

    frappe.db.commit()


def update_employee_assignment(employee, project, site, shift):
    """ This function updates the employee project, site and shift in the employee doctype """
    frappe.db.set_value("Employee", employee, "project", val=project)
    frappe.db.set_value("Employee", employee, "site", val=site)
    frappe.db.set_value("Employee", employee, "shift", val=shift)


@frappe.whitelist()
def schedule_leave(employees, leave_type, start_date, end_date):
    try:
        for employee in json.loads(employees):
            for date in	pd.date_range(start=start_date, end=end_date):
                if frappe.db.exists("Employee Schedule", {"employee": employee["employee"], "date": cstr(date.date())}):
                    roster = frappe.get_doc("Employee Schedule", {"employee": employee["employee"], "date": cstr(date.date())})
                    roster.shift = None
                    roster.shift_type = None
                    roster.project = None
                    roster.site = None
                else:
                    roster = frappe.new_doc("Employee Schedule")
                    roster.employee = employee["employee"]
                    roster.date = cstr(date.date())
                roster.employee_availability = leave_type
                roster.save(ignore_permissions=True)
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)

@frappe.whitelist()
def unschedule_staff(employees, start_date=None, end_date=None, never_end=0):
    try:
        #If start date and end date are provided
        if all([start_date,end_date]):
            if getdate(start_date) > getdate(end_date):
                frappe.throw("Start date cannot be after End date")
                response("Error", 500, None, "Start date cannot be after End date")
            else:
                all_employees=tuple([i['employee'] for i in json.loads(employees)])
                if len(all_employees)>1:
                    sql_query_list = [f"""DELETE FROM `tabEmployee Schedule` WHERE employee in {all_employees} AND date BETWEEN '{start_date}' and '{end_date}';"""]
                elif len(all_employees)==1:
                    selected_employee = all_employees[0]
                    sql_query_list = [f"""DELETE FROM `tabEmployee Schedule` WHERE employee = '{selected_employee}' AND date BETWEEN '{start_date}' and '{end_date}';"""]
                res =  query_db_list(sql_query_list, commit=True)
                if res.error:
                    response("Error", 500, None, res.msg)
                response("Success", 200, {'message':f'Staff(s) unscheduled between {start_date} and {end_date} successfully'})
        else:
            if end_date:
                stop_date = getdate(end_date)
            else: stop_date = None
            delete_list = []
            employees = json.loads(employees)
            if not employees:
                response("Error", 400, None, {'message':'Employees must be selected.'})
            delete_dict = {}
            new_employees = []
            if not start_date:
                start_date = employees[0]['date']
            if end_date:
                for i in employees:
                    if not getdate(i['date']) >= stop_date:
                        new_employees.append(i)
                employees = new_employees
            for i in employees:
                if cint(never_end) == 1:
                    _end_date = f'>="{start_date}"'
                else:
                    _end_date = '="'+str(i['date'])+'"'
                _line = f"""DELETE FROM `tabEmployee Schedule` WHERE employee="{i['employee']}" AND date{_end_date};"""
                if not _line in delete_list:
                    delete_list.append(_line)

            if delete_list:
                res = query_db_list(delete_list, commit=True)
                if res.error:
                    response("Error", 500, None, res.msg)
            response("Success", 200, {'message':'Staff(s) unscheduled successfully'})
    except Exception as e:
        frappe.throw(str(e))
        response("Error", 500, None, str(e))

def get_project_enddate_for_edit_post(post):
    project = frappe.db.get_value("Operations Post", post, ["project"])
    if frappe.db.exists("Contracts", {'project': project}):
        contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
        if not end_date:
            response("Error", 400, None, _("No end date set for contract {contract}".format(contract=contract)))
        return end_date
    else:
        response("Error", 400, None, _("No contract linked with project {project}".format(project=project)))


@frappe.whitelist()
def edit_post(posts, values):

    try:
        user, user_roles, user_employee = get_current_user_details()

        if "Operations Manager" not in user_roles and "Projects Manager" not in user_roles:
            response("Permission Error", 401, None, _("Insufficient permissions to Edit Post."))
        posts = json.loads(posts)
        args = frappe._dict(json.loads(values))


        if args.post_status == "Plan Post":
            # frappe.enqueue(plan_post, posts=posts, args=args, is_async=True, queue='long')
            plan_post(posts=posts, args=args)


        elif args.post_status == "Cancel Post":
            if args.cancel_end_date and cint(args.project_end_date):
                response("Error", 400, None, _("Cannot set both project end date and custom end date!"))
            cancel_post(posts=posts, args=args)
            # frappe.enqueue(cancel_post,posts=posts, args=args, is_async=True, queue='long')


        elif args.post_status == "Suspend Post":
            if args.suspend_to_date and cint(args.project_end_date):
                response("Error", 400, None, _("Cannot set both project end date and custom end date!"))

            # if not args.suspend_to_date and not cint(args.project_end_date):
            # 	frappe.throw(_("Please set an end date!"))
            suspend_post(posts=posts, args=args)
            # frappe.enqueue(suspend_post, posts=posts, args=args, is_async=True, queue='long')


        elif args.post_status == "Post Off":    
            if args.repeat_till and cint(args.project_end_date):
                response("Error", 400, None, _("Cannot set both project end date and custom end date!"))

            if args.repeat == "Does not repeat" and cint(args.project_end_date):
                response("Error", 400, None, _("Cannot set both project end date and choose 'Does not repeat' option!"))
            post_off(posts=posts, args=args)
            # frappe.enqueue(post_off, posts=posts, args=args, is_async=True, queue='long')

        response("Success", 201, {"msg":"Post Schedule created."})
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Edit Post')
        response("Error", 500, None, _(str(e)))

def plan_post(posts, args):
    """ This function sets the post status to planned provided a post, start date and an end date """

    end_date = None

    if args.plan_end_date and not cint(args.project_end_date):
        end_date = args.plan_end_date

    if cint(args.project_end_date) and not args.plan_end_date:
        end_date = get_project_enddate_for_edit_post(posts[0]['post'])

    # filter if plan_from_date
    if args.plan_from_date:
        plan_from_date = getdate(args.plan_from_date)
        # print(posts)
        posts = [post for post in posts if getdate(post['date'])>=plan_from_date]
    # filter if plan_end_date
    if end_date:
        end_date = getdate(end_date)
        posts = [post for post in posts if getdate(post['date'])<=end_date]
        posts = extend_edit_post(posts, str(end_date))
    for post in posts:
        if frappe.db.exists("Post Schedule", {"date": post['date'], "post": post["post"]}):
            doc = frappe.get_doc("Post Schedule", {"date": post['date'], "post": post["post"]})
        else:
            doc = frappe.new_doc("Post Schedule")
            doc.post = post["post"]
            doc.date = post['date']
        doc.post_status = "Planned"
        doc.save()
    frappe.db.commit()

def cancel_post(posts, args):
    end_date = None
    if args.cancel_end_date and not cint(args.project_end_date):
        end_date = args.cancel_end_date

    if cint(args.project_end_date) and not args.cancel_end_date:
        end_date = get_project_enddate_for_edit_post(posts[0]['post'])
        
     #filter if both cancel_from_date and cancel_end_date both exist   
    if args.cancel_from_date and end_date:
        posts = set_post_based_on_from_date_and_to_date(args.cancel_from_date, end_date, posts)

    # filter if plan_from_date
    elif args.cancel_from_date:
        cancel_from_date = getdate(args.plan_from_date)
        posts = [post for post in posts if getdate(post['date'])>=cancel_from_date]
        
    # filter if plan_end_date
    elif end_date:
        end_date = getdate(end_date)
        posts = [post for post in posts if getdate(post['date'])<=end_date]
        posts = extend_edit_post(posts, str(end_date))
    

    for post in posts:
        if frappe.db.exists("Post Schedule", {"date": post['date'], "post": post["post"]}):
            doc = frappe.get_doc("Post Schedule", {"date": post['date'], "post": post["post"]})
        else:
            doc = frappe.new_doc("Post Schedule")
            doc.post = post["post"]
            doc.date = post['date']
        doc.paid = args.suspend_paid
        doc.unpaid = args.suspend_unpaid
        doc.post_status = "Cancelled"
        doc.save()
        frappe.db.commit()

def suspend_post(posts, args):
    end_date = None
    if args.suspend_to_date and not cint(args.project_end_date):
        end_date = args.suspend_to_date

    if cint(args.project_end_date) and not args.suspend_to_date:
        end_date = get_project_enddate_for_edit_post(posts[0]['post'])

    # filter if plan_from_date
    if args.suspend_from_date:
        suspend_from_date = getdate(args.suspend_from_date)
        posts = [post for post in posts if getdate(post['date'])>=suspend_from_date]
    # filter if plan_end_date
    if end_date:
        end_date = getdate(end_date)
        posts = [post for post in posts if getdate(post['date'])<=end_date]
        posts = extend_edit_post(posts, str(end_date))

    for post in posts:
        if frappe.db.exists("Post Schedule", {"date": post['date'], "post": post["post"]}):
            doc = frappe.get_doc("Post Schedule", {"date": post['date'], "post": post["post"]})
        else:
            doc = frappe.new_doc("Post Schedule")
            doc.post = post["post"]
            doc.date = post['date']
        doc.paid = args.suspend_paid
        doc.unpaid = args.suspend_unpaid
        doc.post_status = "Suspended"
        doc.save()
    frappe.db.commit()

def post_off(posts, args):
    from one_fm.api.mobile.roster import month_range
    post_off_paid = args.post_off_paid
    post_off_unpaid = args.post_off_unpaid

    if args.repeat == "Does not repeat":
        if args.off_from_date and args.off_to_date:
            posts = set_post_based_on_from_date_and_to_date(args.off_from_date, args.off_to_date, posts)

        for post in posts:
            set_post_off(post["post"], post["date"], post_off_paid, post_off_unpaid)
    else:
        if args.repeat and args.repeat in ["Daily", "Weekly", "Monthly", "Yearly"]:
            end_date = None

            if args.repeat_till and not cint(args.project_end_date):
                end_date = args.repeat_till
            
            if cint(args.project_end_date) and not args.repeat_till:
                end_date = get_project_enddate_for_edit_post(posts[0]['post'])
                
            if args.off_from_date and args.off_to_date:
                posts = set_post_based_on_from_date_and_to_date(args.off_from_date, args.off_to_date, posts)

            # if end_date and all(args.off_from_date, args.off_to_date):
                # posts = [post for post in posts if getdate(post['date'])<=end_date]
                # posts = extend_edit_post(posts, str(end_date))
                
            if args.repeat == "Daily":
                for post in posts:
                    set_post_off(post["post"], post["date"], post_off_paid, post_off_unpaid)

            elif args.repeat == "Weekly":
                week_days = []
                if args.repeat_days:
                    check_days = range(8)
                    for integer in args.repeat_days:
                        if integer in check_days:
                            week_days.append(day_name[integer])
                        else:
                            continue
                        
                for post in posts:
                    if getdate(post['date']).strftime('%A') in week_days:
                            set_post_off(post["post"], post['date'], post_off_paid, post_off_unpaid)

            elif args.repeat == "Monthly":
                for post in posts:
                    for date in	month_range(post["date"], end_date):
                        set_post_off(post["post"], post['date'], post_off_paid, post_off_unpaid)

            elif args.repeat == "Yearly":
                for post in posts:
                    for date in	pd.date_range(start=post["date"], end=end_date, freq=pd.DateOffset(years=1)):
                        set_post_off(post["post"], post['date'], post_off_paid, post_off_unpaid)
    frappe.db.commit()
    
def set_post_based_on_from_date_and_to_date(start_date, end_date, posts):
    from_date = getdate(start_date)
    to_date = getdate(end_date)
    posts = [post for post in posts if getdate(post['date']) <= to_date and getdate(post['date']) >= from_date]
    posts = extend_edit_post(posts, str(to_date))
    return posts

def set_post_off(post, date, post_off_paid, post_off_unpaid):
    if frappe.db.exists("Post Schedule", {"date": date, "post": post}):
        doc = frappe.get_doc("Post Schedule", {"date": date, "post": post})
    else:
        doc = frappe.new_doc("Post Schedule")
        doc.post = post
        doc.date = date
    doc.paid = post_off_paid
    doc.unpaid = post_off_unpaid
    doc.post_status = "Post Off"
    doc.save()

def extend_edit_post(posts, end_date):
    """
        Add more entry ({post:'xxx', dated:''}) to post if end date
        is greater than current entry
    """
    if len(posts):
        _end_date = getdate(end_date)
        posts = sorted(posts, key=lambda i: (i['date'], i['post']))
        last_post = posts[-1]
        if(_end_date) > getdate(last_post['date']):
            # get post names
            post_names = []
            for i in posts:
                if not i['post'] in post_names:
                    post_names.append(i['post'])
            # generate date range
            for d in pd.date_range(last_post['date'], end_date):
                for i in post_names:
                    posts.append({'post':i, 'date':str(d).split(' ')[0]})
    return posts



@frappe.whitelist()
def dayoff(employees, selected_dates=0, repeat=0, repeat_freq=None, week_days=[], repeat_till=None, project_end_date=None):
    """
        Set days of done with sql query for instant response
    """
    try:
        creation = now()
        owner = frappe.session.user
        roster_type = "Basic"
        id_list = []
        query = """
            INSERT INTO `tabEmployee Schedule` (`name`, `employee`, `date`, `shift`, `site`, `project`, `shift_type`, `employee_availability`, 
            `operations_role`, `post_abbrv`, `roster_type`, `day_off_ot`, `owner`, `modified_by`, `creation`, `modified`)
            VALUES 
        """
        querycontent = """"""


        if not repeat_till and not cint(project_end_date) and not selected_dates:
            frappe.throw(_("Please select either a repeat till date or check the project end date option."))

        from one_fm.api.mobile.roster import month_range
        if cint(selected_dates):
            for employee in json.loads(employees):
                date = employee['date']
                name = f"{date}_{employee['employee']}_{roster_type}"
                id_list.append(name)
                querycontent += f"""(
                    "{name}", "{employee["employee"]}", "{date}", "", "", "", 
                    '', "Day Off", "", "", "Basic", 
                    0, "{owner}", "{owner}", "{creation}", "{creation}"
                ),"""
        else:
            if repeat and repeat_freq in ["Daily", "Weekly", "Monthly", "Yearly"]:
                end_date = None
                if repeat_till and not cint(project_end_date):
                    end_date = repeat_till

                if repeat_freq == "Daily":
                    for employee in json.loads(employees):
                        if cint(project_end_date):
                            project = frappe.db.get_value("Employee", {'employee': employee["employee"]}, ["project"])
                            if frappe.db.exists("Contracts", {'project': project}):
                                contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
                                if not end_date:
                                    frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
                            else:
                                frappe.throw(_("No contract linked with project {project}".format(project=project)))
                        for date in	pd.date_range(start=employee["date"], end=end_date):
                            name = f"{date.date()}_{employee['employee']}_{roster_type}"
                            id_list.append(name)
                            querycontent += f"""(
                                "{name}", "{employee["employee"]}", "{date.date()}", "", "", "", 
                                '', "Day Off", "", "", "Basic", 
                                0, "{owner}", "{owner}", "{creation}", "{creation}"
                            ),"""

                elif repeat_freq == "Weekly":
                    for employee in json.loads(employees):
                        if cint(project_end_date):
                            project = frappe.db.get_value("Employee", {'employee': employee["employee"]}, ["project"])
                            if frappe.db.exists("Contracts", {'project': project}):
                                contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
                                if not end_date:
                                    frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
                            else:
                                frappe.throw(_("No contract linked with project {project}".format(project=project)))
                        for date in	pd.date_range(start=employee["date"], end=end_date):
                            if getdate(date).strftime('%A') in week_days:
                                name = f"{date.date()}_{employee['employee']}_{roster_type}"
                                id_list.append(name)
                                querycontent += f"""(
                                    "{name}", "{employee["employee"]}", "{date.date()}", "", "", "", 
                                    '', "Day Off", "", "", "Basic", 
                                    0, "{owner}", "{owner}", "{creation}", "{creation}"
                                ),"""

                elif repeat_freq == "Monthly":
                    for employee in json.loads(employees):
                        if cint(project_end_date):
                            project = frappe.db.get_value("Employee", {'employee': employee["employee"]}, ["project"])
                            if frappe.db.exists("Contracts", {'project': project}):
                                contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
                                if not end_date:
                                    frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
                            else:
                                frappe.throw(_("No contract linked with project {project}".format(project=project)))
                        for date in	month_range(employee["date"], end_date):
                            name = f"{date.date()}_{employee['employee']}_{roster_type}"
                            id_list.append(name)
                            querycontent += f"""(
                                "{name}", "{employee["employee"]}", "{date.date()}", "", "", "", 
                                '', "Day Off", "", "", "Basic", 
                                0, "{owner}", "{owner}", "{creation}", "{creation}"
                            ),"""

                elif repeat_freq == "Yearly":
                    for employee in json.loads(employees):
                        if cint(project_end_date):
                            project = frappe.db.get_value("Employee", {'employee': employee["employee"]}, ["project"])
                            if frappe.db.exists("Contracts", {'project': project}):
                                contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
                                if not end_date:
                                    frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
                            else:
                                frappe.throw(_("No contract linked with project {project}".format(project=project)))
                        for date in	pd.date_range(start=employee["date"], end=end_date, freq=pd.DateOffset(years=1)):
                            name = f"{date.date()}_{employee['employee']}_{roster_type}"
                            id_list.append(name)
                            querycontent += f"""(
                                "{name}", "{employee["employee"]}", "{date.date()}", "", "", "", 
                                '', "Day Off", "", "", "Basic", 
                                0, "{owner}", "{owner}", "{creation}", "{creation}"
                            ),"""

        if querycontent:
            querycontent = querycontent[:-1]
            query += querycontent
            query += f"""
                ON DUPLICATE KEY UPDATE
                modified_by = VALUES(modified_by),
                modified = "{creation}",
                operations_role = "",
                post_abbrv = "",
                roster_type = "",
                shift = "",
                project = "",
                site = "",
                shift_type = "",
                day_off_ot = 0,
                roster_type = "Basic",
                employee_availability = "Day Off"
            """
            frappe.db.sql(query, values=[], as_dict=1)
            frappe.db.commit()
        response("success", 200, {'message':'Days Off set successfully.'})
    except Exception as e:
        response("error", 500, None, str(e))




def create_request_employee_assignment(employee, from_shift, to_shift):
    req_ea_doc = frappe.new_doc("Request Employee Assignment")
    req_ea_doc.employee = employee
    req_ea_doc.from_shift = from_shift
    req_ea_doc.to_shift = to_shift
    req_ea_doc.save(ignore_permissions=True)


def assign_job(employee, shift, site, project):
    start = time.time()
    frappe.set_value("Employee", employee, "shift", shift)
    frappe.set_value("Employee", employee, "site", site)
    frappe.set_value("Employee", employee, "project", project)


@frappe.whitelist(allow_guest=True)
def search_staff(key, search_term):
    conds = ""
    if key == "customer" and search_term:
        conds += 'and prj.customer like "%{customer}%" and emp.project=prj.name'.format(customer=search_term)
    elif key == "employee_id" and search_term:
        conds += 'and emp.employee_id like "%{employee_id}%" '.format(employee_id=search_term)
    elif key == "project" and search_term:
        conds += 'and emp.project like "%{project}%" '.format(project=search_term)
    elif key == "site" and search_term:
        conds += 'and emp.site like "%{site}%" '.format(site=search_term)
    elif key == "employee_name" and search_term:
        conds += 'and emp.employee_name like "%{name}%" '.format(name=search_term)

    data = frappe.db.sql("""
        select
            distinct emp.name, emp.employee_id, emp.employee_name, emp.image, emp.one_fm_nationality as nationality, usr.mobile_no, usr.name as email, emp.designation, emp.department, emp.shift, emp.site, emp.project
        from `tabEmployee` as emp, `tabUser` as usr, `tabProject` as prj
        where
        emp.user_id=usr.name
        {conds}
    """.format(conds=conds), as_dict=1)
    return data

@frappe.whitelist()
def get_employee_detail(employee_pk):
    if employee_pk:
        pk, employee_id, employee_name, enrolled, cell_number = frappe.db.get_value("Employee", employee_pk, ["name", "employee_id", "employee_name", "enrolled", "cell_number"])
        return {'pk':pk, 'employee_id': employee_id, 'employee_name': employee_name, 'enrolled': enrolled, "cell_number": cell_number}


@frappe.whitelist()
def roster_search_bar(project=None, site=None, shift=None, employee=None):
    """
        This API method filters projects, sites, shifts and employee based on input.
        Dependency moves from Project -> Site -> Shift -> Employee
    """
    try:
        projects, sites, shifts, employees = [], [], [], {}
        shifts_data = []
        if project and site and shift:
            shifts_data = frappe.db.get_list("Operations Shift",
                filters={'project':project, 'site':site, 'name':shift}, 
                fields=["project", "site", "name"], 
                ignore_permissions=True
            )
            employees = frappe.db.get_list("Employee", filters={'project':project, 'site':site, 'shift':shift}, 
                fields=["name", "project", "site", "shift", "employee_id", "employee_name"], 
                ignore_permissions=True)
        elif project and site and employee:
            employee_data = frappe.db.get_list("Employee", filters={'name':employee, 'project':project, 'site':site}, 
                fields=["name", "project", "site", "shift", "employee_id", "employee_name"], 
                ignore_permissions=True)
            if employee_data:
                employee_data = employee_data[0]
                if not (employee_data.project in projects):projects.append(employee_data.project)
                if not (employee_data.site in sites):sites.append(employee_data.site)
                if not (employee_data.shift in shifts):shifts.append(employee_data.shift)
                employees = employee_data
        elif project and site:
            shifts_data = frappe.db.get_list("Operations Shift",
                filters={'project':project, 'site':site}, 
                fields=["project", "site", "name"], 
                ignore_permissions=True
            )
            employees = frappe.db.get_list("Employee", filters={'project':project, 'site':site, 'status':'Active', 'shift_working':1}, 
                fields=["name", "project", "site", "shift", "employee_id", "employee_name"], 
                ignore_permissions=True)
        elif project and shift:
            shifts_data = frappe.db.get_list("Operations Shift",
                filters={'project':project, 'name':shift}, 
                fields=["project", "site", "name"], 
                ignore_permissions=True
            )
            employees = frappe.db.get_list("Employee", filters={'project':project, 'shift':shift, 'status':'Active', 'shift_working':1}, 
                fields=["name", "project", "site", "shift", "employee_id", "employee_name"], 
                ignore_permissions=True)
        elif project and employee:
            employee_data = frappe.db.get_list("Employee", filters={'name':employee, 'project':project, 'status':'Active', 'shift_working':1}, 
                fields=["name", "project", "site", "shift", "employee_id", "employee_name"], 
                ignore_permissions=True)
            if employee_data:
                employee_data = employee_data[0]
                if not (employee_data.project in projects):projects.append(employee_data.project)
                if not (employee_data.site in sites):sites.append(employee_data.site)
                if not (employee_data.shift in shifts):shifts.append(employee_data.shift)
                employees = employee_data
        elif project:
            shifts_data = frappe.db.get_list("Operations Shift",
                filters={'project':project}, 
                fields=["project", "site", "name"], 
                ignore_permissions=True
            )
            employees = frappe.db.get_list("Employee", filters={'project':project, 'status':'Active', 'shift_working':1}, 
                fields=["name", "project", "site", "shift", "employee_id", "employee_name"], 
                ignore_permissions=True)
        elif site:
            shifts_data = frappe.db.get_list("Operations Shift",
                filters={'site':site}, 
                fields=["project", "site", "name"], 
                ignore_permissions=True
            )
            employees = frappe.db.get_list("Employee", filters={'site':site, 'status':'Active', 'shift_working':1}, 
            fields=["name", "project", "site", "shift", "employee_id", "employee_name"], 
            ignore_permissions=True)
        elif shift:
            shifts_data = frappe.db.get_list("Operations Shift",
                filters={'name':shift}, 
                fields=["project", "site", "name"], 
                ignore_permissions=True
            )
            employees = frappe.db.get_list("Employee", filters={'shift':shift, 'status':'Active', 'shift_working':1}, 
                fields=["name", "project", "site", "shift", "employee_id", "employee_name"], 
                ignore_permissions=True)
        elif employee:
            employee_data = frappe.db.get_list("Employee", filters={'name':employee,'status':'Active', 'shift_working':1}, 
                fields=["name", "project", "site", "shift", "employee_id", "employee_name"], 
                ignore_permissions=True)
            if employee_data:
                employee_data = employee_data[0]
                if not (employee_data.project in projects):projects.append(employee_data.project)
                if not (employee_data.site in sites):sites.append(employee_data.site)
                if not (employee_data.shift in shifts):shifts.append(employee_data.shift)
                employees = employee_data
        else:
            projects = [i.name for i in frappe.db.get_list("Project", ignore_permissions=True)]
            sites = [i.name for i in frappe.db.get_list("Operations Site", ignore_permissions=True)]
            shifts = [i.name for i in frappe.db.get_list("Operations Shift", ignore_permissions=True)]
            employees = frappe.db.get_list("Employee", filters={'status':'Active', 'shift_working':1}, 
                fields=["name", "project", "site", "shift", "employee_id", "employee_name"], 
                ignore_permissions=True)
        # sort data
        for i in shifts_data:
            if not i.project in projects:projects.append(i.project)
            if not i.site in sites:sites.append(i.site)
            if not i.name in shifts:shifts.append(i.name)

        data = {
            'projects':projects,
            'sites':sites,
            'shifts':shifts,
            'employees':employees
        }
        return response("success", 200, data)
    except Exception as e:
        response("Bad Request", 500, None, str(e))
