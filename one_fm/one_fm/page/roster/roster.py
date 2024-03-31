from pandas.core.indexes.datetimes import date_range
from datetime import datetime
from one_fm.one_fm.page.roster.employee_map  import CreateMap,PostMap
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate, now, get_datetime, today, add_days
import pandas as pd, numpy as np
from frappe import _
import json, multiprocessing, os, time, itertools, frappe
from multiprocessing.pool import ThreadPool as Pool
from itertools import product
from one_fm.api.notification import create_notification_log
from one_fm.api.v1.utils import response
from one_fm.utils import query_db_list



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
            distinct emp.name, emp.employee_id, emp.employee_name, emp.image, emp.one_fm_nationality as nationality,
           usr.mobile_no, usr.name as email, emp.designation, emp.department, emp.shift, emp.site,
         emp.project,opsite.account_supervisor_name as site_supervisor,opshift.supervisor_name as shift_supervisor
        from `tabEmployee` as emp, `tabUser` as usr,`tabOperations Shift` as opshift,`tabOperations Site` as opsite
        where
        emp.project is not NULL
        and emp.site is not NULL
        and emp.shift is not NULL
        and emp.user_id=usr.name
        and emp.shift = opshift.name
        and emp.site = opsite.name
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
def get_roster_view(start_date, end_date, assigned=0, scheduled=0, employee_search_id=None, employee_search_name=None, project=None, site=None, shift=None, department=None, operations_role=None, designation=None, isOt=None, limit_start=0, limit_page_length=9999):
    try:
        master_data, formatted_employee_data, post_count_data, employee_filters= {}, {}, {}, {}
        operations_roles_list = []
        employees = []
        asa_filters = "em.status = 'Active'  and em.attendance_by_timesheet = '0' "
        filters = {
            'date': ['between', (start_date, end_date)]
        }
        str_filters = f'es.date between "{start_date}" and "{end_date}"'
        exited_employee_filters = f"""status='Left' and attendance_by_timesheet = '0' and relieving_date between '{start_date}' and '{end_date}'"""
        if operations_role:
            filters.update({'operations_role': operations_role})
            str_filters +=' and es.operations_role = "{}"'.format(operations_role)

        if employee_search_id:
            employee_filters.update({'employee_id': employee_search_id})
            exited_employee_filters += f""" and employee_id = "{employee_search_id}" """
        if employee_search_name:
            employee_filters.update({'employee_name': ("like", "%" + employee_search_name + "%")})
            exited_employee_filters += f""" and employee_name LIKE "%{employee_search_name}%" """
            asa_filters+=f'and asa.employee_name LIKE "%{employee_search_name}%"'

        if project:
            employee_filters.update({'project': project})
            exited_employee_filters += f""" and project =  "{project}" """
            asa_filters+=f' and asa.project = "{project}"'
        if site:
            employee_filters.update({'site': site})
            exited_employee_filters +=f""" and site = "{site}" """
            asa_filters += f' and asa.site = "{site}"'
        if shift:
            employee_filters.update({'shift': shift})
            exited_employee_filters += f""" and shift = "{shift}" """
            asa_filters += f' and asa.shift = "{shift}"'
        if department:
            employee_filters.update({'department': department})
            exited_employee_filters += f""" and department = "{department}" """


        #--------------------- Fetch Employee list ----------------------------#
        #get list of employees that left the company on that month.

        exited_employee_query = """SELECT employee,employee_name from `tabEmployee` where {}""".format(exited_employee_filters)
        exited_employees = frappe.db.sql(exited_employee_query,as_dict=1)
        # exited_employees = frappe.get_all("Employee",employee_filters,['employee','employee_name'])

        if isOt:
            employee_filters.update({'employee_availability' : 'Working'})
            all_active_employees = frappe.db.sql("SELECT name from `tabEmployee` where status in ('Active','Vacation') and attendance_by_timesheet = '0' ",as_dict =1)
            all_active_employee_ids = [i.name for i in all_active_employees]
            employee_filters.update({'employee':['In',all_active_employee_ids]})
            employees = frappe.db.get_list("Employee Schedule", employee_filters, ["distinct employee", "employee_name"], order_by="employee_name asc" ,limit_start=limit_start, limit_page_length=limit_page_length, ignore_permissions=True)
            master_data.update({'total' : len(employees)})
            employees.extend(exited_employees)
            employees = filter_redundant_employees(employees)
            employee_filters.update({'date': ['between', (start_date, end_date)], 'post_status': 'Planned'})
            employee_filters.pop('employee_availability')
            employee_filters.pop('employee')
            employee_filters.pop('attendance_by_timesheet', None)

        else:
            employee_filters.update({'status': ["IN",['Active',"Vacation"]]})
            employee_filters.update({'shift_working':'1'})
            employee_filters.update({'attendance_by_timesheet':'0'})
            if designation:
                employee_filters.update({'designation' : designation})
            employees = frappe.db.get_list("Employee", employee_filters, ["employee", "employee_name", "day_off_category", "number_of_days_off"], order_by="employee_name asc" ,limit_start=limit_start, limit_page_length=limit_page_length, ignore_permissions=True)
            employees.extend(exited_employees)
            employees = filter_redundant_employees(employees)

            #Conditional to ensure that the proceeding code block does not run unless Project,shift or site is queried
            if employee_search_name or shift or site or project:
                employees_asa_q = f"""SELECT distinct asa.employee as employee, asa.employee_name  as employee_name from `tabAdditional Shift Assignment` asa JOIN `tabEmployee`em on em.name =asa.employee where {asa_filters}"""
                employees_asa = frappe.db.sql(employees_asa_q,as_dict=1)
                if len(employees_asa) > 0:
                    employees.extend(employees_asa)
                    employees = filter_redundant_employees(employees)
            master_data.update({'total': len(employees)})
            employee_filters.pop('status', None)
            employee_filters.pop('shift_working', None)
            employee_filters.pop('attendance_by_timesheet', None)
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
        response("Success", 200, master_data)
    except Exception as e:
        # print(frappe.get_traceback())
        return response("Server Error", 500, None, str(frappe.get_traceback()))

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


def get_employee_leave_attendance(employees,start_date):
    """Returns a dict of employees and their corresponding attendance dates if it falls on or after the start date

    Args:
        employees (list): list of employees

    Returns:
        dict: list of dictionaries
    """
    attendance_dict = {}
    all_attendance = frappe.get_all("Attendance",{'attendance_date':['>=',start_date],'employee':["IN",employees],'docstatus':1,'status':'On Leave'},['attendance_date','employee'])
    if all_attendance:
        for each in all_attendance:
            if attendance_dict.get(each.employee):
                attendance_dict[each.employee].append(each.attendance_date)
            else:
                attendance_dict[each.employee] = [each.attendance_date]
    return attendance_dict



@frappe.whitelist()
def schedule_staff(employees, shift, operations_role, otRoster, start_date, project_end_date, keep_days_off=0, request_employee_schedule=0, day_off_ot=None, end_date=None, selected_days_only=0):
    try:
        start_time = time.time()
        _start_date = getdate(start_date)

        validation_logs = []
        user, user_roles, user_employee = get_current_user_details()

        employees = json.loads(employees)
        if not employees:
            frappe.throw("Employees must be selected.")

        employee_list = list({obj["employee"] for obj in employees})
        employee_leave_attendance = get_employee_leave_attendance(employee_list,start_date)
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
                            if  day.date() not in employee_leave_attendance.get(obj,[]):
                                employees.append({"employee": obj, "date": str(day.date())})

            else:
                validation_logs.append("No contract linked with project {project}".format(project=project))

        elif end_date and not cint(project_end_date):
            end_date = getdate(end_date)
            employees = []
            list_of_date = date_range(start_date, end_date)
            for obj in employee_list:
                for day in list_of_date:
                    if  day.date() not in employee_leave_attendance.get(obj,[]):
                        employees.append({"employee": obj, "date": str(day.date())})

        elif not cint(project_end_date) and not end_date and not selected_days_only:
            validation_logs.append("Please set an end date for scheduling the staff.")

        elif cint(project_end_date) and end_date:
            validation_logs.append("Please select either the project end date or set a custom date. You cannot set both!")

        emp_tuple = str(employee_list).replace('[', '(').replace(']',')')
        # date_range = pd.date_range(start=start_date, end=end_date)

        if not cint(request_employee_schedule) and "Projects Manager" not in user_roles and "Operations Manager" not in user_roles:
            all_employee_shift_query = frappe.db.sql("""
                SELECT DISTINCT es.shift, s.supervisor
                FROM `tabEmployee Schedule` es JOIN `tabOperations Shift` s ON es.shift = s.name
                WHERE
                es.date BETWEEN '{start_date}' AND '{end_date}'
                AND es.employee_availability='Working' AND es.employee IN {emp_tuple}
                GROUP BY es.shift
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
            mid_time = time.time()
            extreme_schedule(employees=employees, start_date=start_date, end_date=end_date, shift=shift,
                operations_role=operations_role, otRoster=otRoster, keep_days_off=keep_days_off, day_off_ot=day_off_ot,
                request_employee_schedule=request_employee_schedule, employee_list=employee_list
            )
            # employees_list = frappe.db.get_list("Employee", filters={"name": ["IN", employees]}, fields=["name", "employee_id", "employee_name"])
            update_roster(key="roster_view")
            end_time = time.time()
            print('\n\n\n\n\n\n\n\n\n')
            print('\n\n\n\n\n\n\n\n\n')
            print('\n\n\n\n\n\n\n\n\n')
            print("EXECUTION TIME FOR FULL FUNCTION")
            print(end_time - start_time)
            print("EXECUTION TIME FOR ONLY SCHEDULE FUNCTION")
            print(mid_time - start_time)
            print("EXECUTION TIME FOR ONLY EXTREME SCHEDULE FUNCTION")
            print(end_time - mid_time)
            print('\n\n\n\n\n\n\n\n\n')
            print('\n\n\n\n\n\n\n\n\n')
            print('\n\n\n\n\n\n\n\n\n')
            response("success", 200, {'message':'Successfully rostered employees'})
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Schedule Roster")
        response("error", 200, None, str(e))

def update_roster(key):
    frappe.publish_realtime(key, "Success")


def extreme_schedule(employees, shift, operations_role, otRoster, start_date, end_date, keep_days_off, day_off_ot,
    request_employee_schedule, employee_list):
    if not employees:
        frappe.throw("Please select employees before rostering")
        return
    creation = now()
    owner = frappe.session.user
    start_time, end_time = frappe.db.get_value("Shift Type", frappe.db.get_value("Operations Shift", shift, "shift_type"), ['start_time', 'end_time'])
    operations_shift = frappe.get_doc("Operations Shift", shift, ignore_permissions=True)
    operations_role = frappe.get_doc("Operations Role", operations_role, ignore_permissions=True)
    day_off_ot = cint(day_off_ot)
    if otRoster == 'false':
        roster_type = 'Basic'
    elif otRoster == 'true' or day_off_ot == 1:
        roster_type = 'Over-Time'

    # check for end date
    if end_date:
        end_date = getdate(end_date)
        new_employees = []
        for i in employees:
            if getdate(i['date']) <= end_date:
                new_employees.append(i)
        if new_employees:
            employees = new_employees.copy()
    # check keep days_off
    if cint(keep_days_off):
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
                    if not (i.get('date') in days_off_dict.get(i.get('employee'))):
                        new_employees.append(i)
                if new_employees:
                    employees = new_employees.copy()

    # # get and structure employee dictionary for easy hashing
    employees_list = frappe.db.get_list("Employee", filters={'employee': ['IN', employee_list]}, fields=['name', 'employee_name', 'department'], ignore_permissions=True)
    employees_dict = {}
    for i in employees_list:
        employees_dict[i.name] = i

    # make data structure for the roster
    shift_start, shift_end = frappe.db.get_value("Operations Shift", shift, ["start_time", "end_time"])
    next_day = False
    if shift_start>shift_end:
        next_day = True
    employees_date_dict = {}
    for i in employees:
        if employees_date_dict.get(i['employee']):
            employees_date_dict[i['employee']].append({'date':i['date'],
                'start_datetime': datetime.strptime(f"{i['date']} {shift_start}", '%Y-%m-%d %H:%M:%S'), "end_datetime":datetime.strptime(f"{add_days(i['date'], 1) if next_day else i['date']} {shift_end}", '%Y-%m-%d %H:%M:%S')})
        else:
            employees_date_dict[i['employee']] =[{'date':i['date'], 'start_datetime': datetime.strptime(f"{i['date']} {shift_start}", '%Y-%m-%d %H:%M:%S'), "end_datetime":datetime.strptime(f"{add_days(i['date'], 1) if next_day else i['date']} {shift_end}", '%Y-%m-%d %H:%M:%S')}]

    # check for intersection schedules
    error_msg = """"""
    checklist = []
    shift_start, shift_end = frappe.db.get_value("Operations Shift", shift, ["start_time", "end_time"])
    for emp, dates in employees_date_dict.items():
        datelist = [i['date'] for i in dates]
        if (len(datelist)==1):datelist.append(datelist[0])
        intersect_query = frappe.db.sql(f"""
            SELECT DISTINCT name, date, start_datetime, end_datetime, shift_type, employee_availability, roster_type
            FROM
            `tabEmployee Schedule` WHERE employee='{emp}' AND date IN {tuple(datelist)}
            AND NOT roster_type="{roster_type}"
        """, as_dict=1)
        if intersect_query:
            for iq in intersect_query:
                if not iq.name in checklist:
                    if iq.employee_availability=='Working':
                        for d in dates:
                            if d['date'] == str(iq.date):
                                if (d['start_datetime'] <= iq.start_datetime and iq.end_datetime <= d['end_datetime'] and iq.end_datetime.date()==d['end_datetime'].date()) or (
                                        iq.start_datetime >= d['start_datetime'] and  d['end_datetime'] <= iq.end_datetime and iq.end_datetime.date()==d['end_datetime'].date()
                                    ) or (d['start_datetime'] >= iq.start_datetime and iq.end_datetime >= d['end_datetime']
                                        and iq.end_datetime.date()==d['end_datetime'].date()):
                                    error_msg += f"{emp}, {iq.date}, Requested: <b>{d['start_datetime']} to {d['end_datetime']}</b>, Existing: <b>{iq.start_datetime} to {iq.end_datetime} ({iq.roster_type})</b><hr>\n"
                    checklist.append(iq.name)
    if error_msg:
        error_head = f"""
            Some of the schedules you requested with shift <b>{shift}: {shift_start} - {shift_end}</b> intersect with existing schedule shift time.<br>
            Below list shows: Employee, Date, Requested Schedule and Existing Schedule.
            <hr>
        """
        frappe.throw(error_head+error_msg)
    
    
    if not cint(request_employee_schedule):
    # 	"""
    # 		USE DIRECT SQL TO CREATE ROSTER SCHEDULE.
    # 	"""
        query = """
            INSERT INTO `tabEmployee Schedule` (`name`, `employee`, `employee_name`, `department`, `date`, `shift`, `site`, `project`, `shift_type`, `employee_availability`,
            `operations_role`, `post_abbrv`, `roster_type`, `day_off_ot`, `start_datetime`, `end_datetime`, `owner`, `modified_by`, `creation`, `modified`)
            VALUES
        """
        list_of_date = date_range(start_date, end_date)
        post_data = validate_overfilled_post(list_of_date,operations_shift.name)
        post_number = post_data.get('post_number')
        schedule_data  = post_data.get('schedule_dict')
        if not post_number:post_number=0
        number_to_add_daily = len(employees_dict)
        omitted_days = []
        
        no_of_schedules_on_date = {}
        if not cint(keep_days_off):
            id_list = [] #store for schedules list
            
            for employee, date_values in employees_date_dict.items():
                for datevalue in date_values:
                    if datevalue.get('date') not in omitted_days:
                        already_scheduled = int(schedule_data.get(datevalue.get('date'),0))
                        if number_to_add_daily+already_scheduled <= post_number:
                            employee_doc = employees_dict.get(employee)
                            name = f"{datevalue['date']}_{employee}_{roster_type}"
                            id_list.append(name)
                            query += f"""
                                (
                                    "{name}", "{employee}", "{employee_doc.employee_name}", "{employee_doc.department}", "{datevalue['date']}", "{operations_shift.name}",
                                    "{operations_shift.site}", "{operations_shift.project}", '{operations_shift.shift_type}', "Working",
                                    "{operations_role.name}", "{operations_role.post_abbrv}", "{roster_type}",
                                    {day_off_ot}, "{datevalue.get('start_datetime')}", "{datevalue.get('end_datetime')}", "{owner}", "{owner}", "{creation}", "{creation}"
                                ),"""
                        else:
                            omitted_days.append(datevalue['date'])
                            

            query = query[:-1]

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
                employee_availability = "Working",
                start_datetime= VALUES(start_datetime),
                end_datetime= VALUES(end_datetime)
            """

            # validate_operations_post_overfill(no_of_schedules_on_date, operations_shift.name)

            frappe.db.sql(query, values=[], as_dict=1)
            frappe.db.commit()
            if omitted_days:
                frappe.msgprint(f"Employee Schedules were not created for {','.join(omitted_days)} because {operations_shift.name} will been overfilled for these days if {number_to_add_daily} {'schedules' if int(number_to_add_daily)>1 else 'schedule'} are added.  ")
        else:
            id_list = [] #store for schedules list
            for employee, date_values in employees_date_dict.items():
                for datevalue in date_values:
                    if datevalue.get('date') not in omitted_days:
                        already_scheduled = int(schedule_data.get(datevalue.get('date'),0))
                        if number_to_add_daily+already_scheduled <= post_number:
                            if datevalue['date'] in no_of_schedules_on_date:
                                no_of_schedules_on_date[datevalue['date']] += 1
                            else:
                                no_of_schedules_on_date[datevalue['date']] = 1
                            employee_doc = employees_dict.get(employee)
                            name = f"{datevalue['date']}_{employee}_{roster_type}"
                            id_list.append(name)
                            query += f"""
                                (
                                    "{name}", "{employee}", "{employee_doc.employee_name}", "{employee_doc.department}", "{datevalue['date']}", "{operations_shift.name}",
                                    "{operations_shift.site}", "{operations_shift.project}", '{operations_shift.shift_type}', "Working",
                                    "{operations_role.name}", "{operations_role.post_abbrv}", "{roster_type}",
                                    {day_off_ot}, "{datevalue.get('start_datetime')}", "{datevalue.get('end_datetime')}", "{owner}", "{owner}", "{creation}", "{creation}"
                                ),"""
                        else:
                            omitted_days.append(datevalue['date'])
                            

            query = query[:-1]

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
                employee_availability = "Working",
                start_datetime= VALUES(start_datetime),
                end_datetime= VALUES(end_datetime)
            """

            # validate_operations_post_overfill(no_of_schedules_on_date, operations_shift.name)

            frappe.db.sql(query, values=[], as_dict=1)
            frappe.db.commit()
            if omitted_days:
                frappe.msgprint(f"Employee Schedules were not created for {','.join(omitted_days)} because {operations_shift.name} will been overfilled for these days if {number_to_add_daily} schedule are added.  ")
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
            shifts_dataset = frappe.db.get_list("Operations Shift", filters={"name": ["IN", [i.shift for i in from_schedule]]}, fields=["name", "supervisor", "supervisor_name"], order_by="name ASC")
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


def validate_overfilled_post(date_list,operations_shift):
    start_time = time.time()
    dates = list(set(date_list)) #Remove Duplicates
    date_list = [e.strftime('%Y-%m-%d') for e in dates]
    cond = False
    schedule_dict = {}
    base_query = f""" SELECT date ,count(name) as schedule_count from `tabEmployee Schedule`  WHERE shift = '{operations_shift}' """
    post_number = frappe.db.sql(f""" SELECT count(name) as post_number from `tabOperations Post` where status = 'Active' and site_shift = '{operations_shift}'   """,as_dict=1)
    post_number = post_number[0].get('post_number') if post_number else 0
    if len(date_list)==1:
        cond = f" AND date = {date_list[0]}"
    elif len(date_list)>1:
        cond = f" AND date in {tuple(date_list)}"
    full_query = base_query+cond+" GROUP BY date"
    schedule_number = frappe.db.sql(full_query,as_dict=1)
    for each in schedule_number:
        schedule_dict[each.get('date').strftime('%Y-%m-%d')] = each.schedule_count
    end_time = time.time()
    print('\n\n\n\n\n\n\n\n\n\n')
    print('\n\n\n\n\n\n\n\n\n\n')
    print('\n\n\n\n\n\n\n\n\n\n')
    print('EXECUTION for VALIDATE FUNCTION')
    print(end_time - start_time)
    print('\n\n\n\n\n\n\n\n\n\n')
    print('\n\n\n\n\n\n\n\n\n\n')
    print('\n\n\n\n\n\n\n\n\n\n')
    return{'schedule_dict':schedule_dict,'post_number':post_number}

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

@frappe.whitelist(allow_guest=True)
def unschedule_staff(employees, otRoster,start_date, end_date=None, never_end=0):
    try:
        if otRoster == 'true':
            roster_type = "Over-Time"
        else:
            roster_type = "Basic"
        _start_date = getdate(start_date)
        if end_date:
            stop_date = getdate(end_date)
        else: stop_date = None
        delete_list = []
        employees = json.loads(employees)
        if not employees:
            response("Error", 400, None, {'message':'Employees must be selected.'})
        employees = [i for i in employees if getdate(i['date'])>=_start_date]

        if end_date:
            employees = [i for i in employees if getdate(i['date'])<=stop_date]

        # check if no end date
        if cint(never_end) == 1:
            employees_to_delete = []
            for i in employees:
                if not i['employee'] in employees_to_delete:
                    employees_to_delete.append(i['employee'])
            # delete all schedules greater than start date
            employees_to_delete=str(tuple(employees_to_delete)).replace(',)', ')')
            frappe.db.sql(f"""
                DELETE FROM `tabEmployee Schedule` WHERE employee IN {employees_to_delete} and date>='{start_date}' and roster_type ='{roster_type}'
            """)
        else:
            for i in employees:
                frappe.db.sql(f"""
                    DELETE FROM `tabEmployee Schedule` WHERE employee='{i['employee']}' and date='{i['date']}' and roster_type ='{roster_type}'
                """)
        response("Success", 200, {'message':'Staff(s) unscheduled successfully'})
    except Exception as e:
        frappe.throw(str(e))
        response("Error", 200, None, str(e))

@frappe.whitelist()
def edit_post(posts, values):

    user, user_roles, user_employee = get_current_user_details()

    if "Operations Manager" not in user_roles and "Projects Manager" not in user_roles:
        frappe.throw(_("Insufficient permissions to Edit Post."))

    args = frappe._dict(json.loads(values))

    if args.post_status == "Plan Post":
        if args.plan_end_date and cint(args.project_end_date):
            frappe.throw(_("Cannot set both project end date and custom end date!"))

        if not args.plan_end_date and not cint(args.project_end_date):
            frappe.throw(_("Please set an end date!"))

        frappe.enqueue(plan_post, posts=posts, args=args, is_async=True, queue='long')



    elif args.post_status == "Cancel Post":
        if args.cancel_end_date and cint(args.project_end_date):
            frappe.throw(_("Cannot set both project end date and custom end date!"))

        if not args.cancel_end_date and not cint(args.project_end_date):
            frappe.throw(_("Please set an end date!"))

        frappe.enqueue(cancel_post,posts=posts, args=args, is_async=True, queue='long')




    elif args.post_status == "Suspend Post":
        if args.suspend_to_date and cint(args.project_end_date):
            frappe.throw(_("Cannot set both project end date and custom end date!"))

        if not args.suspend_to_date and not cint(args.project_end_date):
            frappe.throw(_("Please set an end date!"))

        frappe.enqueue(suspend_post, posts=posts, args=args, is_async=True, queue='long')




    elif args.post_status == "Post Off":
        if args.repeat_till and cint(args.project_end_date):
            frappe.throw(_("Cannot set both project end date and custom end date!"))

        if not args.repeat_till and not cint(args.project_end_date):
            frappe.throw(_("Please set an end date!"))

        if args.repeat == "Does not repeat" and cint(args.project_end_date):
            frappe.throw(_("Cannot set both project end date and choose 'Does not repeat' option!"))

        frappe.enqueue(post_off, posts=posts, args=args, is_async=True, queue='long')

    frappe.enqueue(update_roster, key="staff_view", is_async=True, queue='long')

def plan_post(posts, args):
    """ This function sets the post status to planned provided a post, start date and an end date """

    end_date = None

    if args.plan_end_date and not cint(args.project_end_date):
        end_date = args.plan_end_date

    for post in json.loads(posts):
        if cint(args.project_end_date) and not args.plan_end_date:
            project = frappe.db.get_value("Operations Post", post["post"], ["project"])
            if frappe.db.exists("Contracts", {'project': project}):
                contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
                if not end_date:
                    frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
            else:
                frappe.throw(_("No contract linked with project {project}".format(project=project)))

        for date in pd.date_range(start=args.plan_from_date, end=end_date):
            if frappe.db.exists("Post Schedule", {"date": cstr(date.date()), "post": post["post"]}):
                doc = frappe.get_doc("Post Schedule", {"date": cstr(date.date()), "post": post["post"]})
                delete_existing_post_schedules(cstr(date.date()),post['post'])

            doc = frappe.new_doc("Post Schedule")
            doc.post = post["post"]
            doc.date = cstr(date.date())
            doc.post_status = "Planned"
            doc.save()
        frappe.db.commit()

def cancel_post(posts, args):
    end_date = None

    if args.cancel_end_date and not cint(args.project_end_date):
        end_date = args.cancel_end_date

    for post in json.loads(posts):
        if cint(args.project_end_date) and not args.cancel_end_date:
            project = frappe.db.get_value("Operations Post", post["post"], ["project"])
            if frappe.db.exists("Contracts", {'project': project}):
                contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
                if not end_date:
                    frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
            else:
                frappe.throw(_("No contract linked with project {project}".format(project=project)))

        for date in	pd.date_range(start=args.cancel_from_date, end=end_date):
            if frappe.db.exists("Post Schedule", {"date": cstr(date.date()), "post": post["post"]}):
                # doc = frappe.get_doc("Post Schedule", {"date": cstr(date.date()), "post": post["post"]})
                delete_existing_post_schedules(cstr(date.date()),post['post'])

            doc = frappe.new_doc("Post Schedule")
            doc.post = post["post"]
            doc.date = cstr(date.date())
            doc.paid = args.suspend_paid

            doc.post_status = "Cancelled"
            doc.save()
    frappe.db.commit()

def suspend_post(posts, args):
    end_date = None

    if args.suspend_to_date and not cint(args.project_end_date):
        end_date = args.suspend_to_date

    for post in json.loads(posts):
        if cint(args.project_end_date) and not args.suspend_to_date:
            project = frappe.db.get_value("Operations Post", post["post"], ["project"])
            if frappe.db.exists("Contracts", {'project': project}):
                contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
                if not end_date:
                    frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
            else:
                frappe.throw(_("No contract linked with project {project}".format(project=project)))

        for date in	pd.date_range(start=args.suspend_from_date, end=end_date):
            if frappe.db.exists("Post Schedule", {"date": cstr(date.date()), "post": post["post"]}):
                delete_existing_post_schedules(cstr(date.date()),post['post'])

            doc = frappe.new_doc("Post Schedule")
            doc.post = post["post"]
            doc.date = cstr(date.date())
            doc.paid = args.suspend_paid

            doc.post_status = "Suspended"
            doc.save()
    frappe.db.commit()

def post_off(posts, args):
    from one_fm.api.mobile.roster import month_range
    post_off_paid = args.post_off_paid


    if args.repeat == "Does not repeat":
        for post in json.loads(posts):
            set_post_off(post["post"], post["date"], post_off_paid)
    else:
        if args.repeat and args.repeat in ["Daily", "Weekly", "Monthly", "Yearly"]:
            end_date = None

            if args.repeat_till and not cint(args.project_end_date):
                end_date = args.repeat_till

            if args.repeat == "Daily":
                for post in json.loads(posts):
                    if cint(args.project_end_date) and not args.repeat_till:
                        project = frappe.db.get_value("Operations Post", post["post"], ["project"])
                        if frappe.db.exists("Contracts", {'project': project}):
                            contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
                            if not end_date:
                                frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
                        else:
                            frappe.throw(_("No contract linked with project {project}".format(project=project)))

                    for date in	pd.date_range(start=post["date"], end=end_date):
                        set_post_off(post["post"], cstr(date.date()), post_off_paid)

            elif args.repeat == "Weekly":
                week_days = []
                if args.sunday: week_days.append("Sunday")
                if args.monday: week_days.append("Monday")
                if args.tuesday: week_days.append("Tuesday")
                if args.wednesday: week_days.append("Wednesday")
                if args.thursday: week_days.append("Thursday")
                if args.friday: week_days.append("Friday")
                if args.saturday: week_days.append("Saturday")
                for post in json.loads(posts):
                    if cint(args.project_end_date) and not args.repeat_till:
                        project = frappe.db.get_value("Operations Post", post["post"], ["project"])
                        if frappe.db.exists("Contracts", {'project': project}):
                            contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
                            if not end_date:
                                frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
                        else:
                            frappe.throw(_("No contract linked with project {project}".format(project=project)))

                    for date in	pd.date_range(start=post["date"], end=end_date):
                        if getdate(date).strftime('%A') in week_days:
                            set_post_off(post["post"], cstr(date.date()), post_off_paid)

            elif args.repeat == "Monthly":
                for post in json.loads(posts):
                    if cint(args.project_end_date) and not args.repeat_till:
                        project = frappe.db.get_value("Operations Post", post["post"], ["project"])
                        if frappe.db.exists("Contracts", {'project': project}):
                            contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
                            if not end_date:
                                frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
                        else:
                            frappe.throw(_("No contract linked with project {project}".format(project=project)))

                    for date in	month_range(post["date"], end_date):
                        set_post_off(post["post"], cstr(date.date()), post_off_paid)

            elif args.repeat == "Yearly":
                for post in json.loads(posts):
                    if cint(args.project_end_date) and not args.repeat_till:
                        project = frappe.db.get_value("Operations Post", post["post"], ["project"])
                        if frappe.db.exists("Contracts", {'project': project}):
                            contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
                            if not end_date:
                                frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
                        else:
                            frappe.throw(_("No contract linked with project {project}".format(project=project)))

                    for date in	pd.date_range(start=post["date"], end=end_date, freq=pd.DateOffset(years=1)):
                        set_post_off(post["post"], cstr(date.date()), post_off_paid)
    frappe.db.commit()



def delete_existing_post_schedules(date,post):
    try:
        sql_rs = frappe.db.sql(f"""DELETE from `tabPost Schedule` where date = '{date}' and post = '{post}' """)

        frappe.db.commit()
    except:
        frappe.log_error("Error Deleting Post Schedules",frappe.get_traceback())


def set_post_off(post, date, post_off_paid):
    if frappe.db.exists("Post Schedule", {"date": date, "post": post}):
        #Delete existing post schedules
        # doc = frappe.get_doc("Post Schedule", {"date": date, "post": post})
        delete_existing_post_schedules(date,post)

    doc = frappe.new_doc("Post Schedule")
    doc.post = post
    doc.date = date
    doc.paid = post_off_paid

    doc.post_status = "Post Off"
    doc.save()



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
                if getdate(date)>getdate(today()):
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
                            if getdate(date)>getdate(today()):
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
                            if getdate(date).strftime('%A') in week_days and getdate(date)>getdate(today()):
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
                            if getdate(date)>getdate(today()):
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
                            if getdate(date)>getdate(today()):
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
        response("error", 200, None, str(e))


@frappe.whitelist()
def assign_staff(employees, shift, request_employee_assignment):
    if not employees:
        frappe.throw("Please select employees first")
    validation_logs = []
    user, user_roles, user_employee = get_current_user_details()
    shift, site, project = frappe.db.get_value("Operations Shift", shift, ['name', 'site', 'project'])
    if not cint(request_employee_assignment):
        for emp in json.loads(employees):
            emp_project, emp_site, emp_shift = frappe.db.get_value("Employee", emp, ["project", "site", "shift"])
            supervisor = frappe.db.get_value("Operations Shift", emp_shift, ["supervisor"])
            # if user_employee.name != supervisor:
            # 	validation_logs.append("You are not authorized to change assignment for employee {emp}. Please check the Request Employee Assignment option to place a request.".format(emp=emp))

    if len(validation_logs) > 0:
        frappe.throw(str(validation_logs))
        frappe.log_error(str(validation_logs))
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

            return True

        except Exception as e:
            frappe.log_error(str(e))
            frappe.throw(_(str(e)))

def create_request_employee_assignment(employee, from_shift, to_shift):
    req_ea_doc = frappe.new_doc("Request Employee Assignment")
    req_ea_doc.employee = employee
    req_ea_doc.from_shift = from_shift
    req_ea_doc.to_shift = to_shift
    req_ea_doc.save(ignore_permissions=True)


def assign_job(employee, shift, site, project):
    
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
