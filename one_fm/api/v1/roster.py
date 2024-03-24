import frappe
from frappe import _
from frappe.utils import getdate, cint, cstr, random_string, now_datetime, data as convert_string_to_datetime
from frappe.client import get_list
import pandas as pd
import json, base64, ast, itertools, datetime
from frappe.client import attach_file
from one_fm.one_fm.page.roster.roster import get_post_view as _get_post_view  # , get_roster_view as _get_roster_view
from one_fm.api.v1.utils import response
from one_fm.utils import get_current_shift
from one_fm.one_fm.page.roster.employee_map import CreateMap, PostMap


# @frappe.whitelist()
# def get_roster_view(start_date, end_date, all=1, assigned=0, scheduled=0, project=None, site=None, shift=None, department=None, operations_role=None):
# 	try:
# 		return _get_roster_view(start_date, end_date, all, assigned, scheduled, project, site, shift, department, operations_role)
# 	except Exception as e:
# 		return frappe.utils.response.report_error(e.http_status_code)

@frappe.whitelist()
def get_roster_view(date, shift=None, site=None, project=None, department=None):
    try:
        filters = {
            'date': date
        }
        if project:
            filters.update({'project': project})
        if site:
            filters.update({'site': site})
        if shift:
            filters.update({'shift': shift})
        if department:
            filters.update({'department': department})

        fields = ["employee", "employee_name", "date", "operations_role", "post_abbrv", "employee_availability",
                  "shift"]
        user, user_roles, user_employee = get_current_user_details()
        
        if "Operations Manager" in user_roles or "Projects Manager" in user_roles:
            projects = get_assigned_projects(user_employee.name)
            assigned_projects = []
            for assigned_project in projects:
                assigned_projects.append(assigned_project.name)

            filters.update({"project": ("in", assigned_projects)})
            roster = frappe.get_all("Employee Schedule", filters, fields)
            master_data = []
            for key, group in itertools.groupby(roster, key=lambda x: (x['post_abbrv'], x['operations_role'])):
                employees = list(group)
                master_data.append({"employees": employees, "post": key[0], "count": len(employees)})
            return master_data

        elif "Site Supervisor" in user_roles:
            sites = get_assigned_sites(user_employee.name, project)
            assigned_sites = []
            for assigned_site in sites:
                assigned_sites.append(assigned_site.name)
            filters.update({"site": ("in", assigned_sites)})
            roster = frappe.get_all("Employee Schedule", filters, fields)
            
            master_data = []
            for key, group in itertools.groupby(roster, key=lambda x: (x['post_abbrv'], x['operations_role'])):
                employees = list(group)
                master_data.append({"employees": employees, "post": key[0], "count": len(employees)})
            return master_data

        elif "Shift Supervisor" in user_roles:
            shifts = get_assigned_shifts(user_employee.name, site)
            assigned_shifts = []
            for assigned_shift in shifts:
                assigned_shifts.append(assigned_shift.name)
            filters.update({"shift": ("in", assigned_shifts)})

            roster = frappe.get_all("Employee Schedule", filters, fields)
            master_data = []
            for key, group in itertools.groupby(roster, key=lambda x: (x['post_abbrv'], x['operations_role'])):
                employees = list(group)
                master_data.append({"employees": employees, "post": key[0], "count": len(employees)})
            return master_data
    except Exception as e:
        frappe.log_error(title="API Roster Vie", message=frappe.get_traceback())
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_weekly_staff_roster(start_date, end_date):
    try:
        user, user_roles, user_employee = get_current_user_details()
        roster = frappe.db.sql("""
			SELECT shift, employee, date, employee_availability, operations_role
			FROM `tabEmployee Schedule`
			WHERE employee="{emp}"
			AND date BETWEEN date("{start_date}") AND date("{end_date}")
		""".format(emp=user_employee.name, start_date=start_date, end_date=end_date), as_dict=1)
        print(roster)
        return roster
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_current_user_details():
    user = frappe.session.user
    user_roles = frappe.get_roles(user)
    user_employee = frappe.get_value("Employee", {"user_id": user},
                                     ["name", "employee_id", "employee_name", "image", "enrolled", "designation"],
                                     as_dict=1)
    return user, user_roles, user_employee


@frappe.whitelist()
def get_post_view(date, shift=None, site=None, project=None, department=None):
    try:
        filters = {
            'date': date
        }
        if project:
            filters.update({'project': project})
        if site:
            filters.update({'site': site})
        if shift:
            filters.update({'shift': shift})
        if department:
            filters.update({'department': department})

        fields = ["post", "post_status", "date", "operations_role", "shift"]
        user, user_roles, user_employee = get_current_user_details()

        if "Operations Manager" in user_roles or "Projects Manager" in user_roles:
            projects = get_assigned_projects(user_employee.name)
            assigned_projects = []
            for assigned_project in projects:
                assigned_projects.append(assigned_project.name)

            filters.update({"project": ("in", assigned_projects)})
            roster = frappe.get_all("Post Schedule", filters, fields)
            print(roster)
            for post in roster:
                post.update({"count": 1})
            return roster

        elif "Site Supervisor" in user_roles:
            sites = get_assigned_sites(user_employee.name, project)
            assigned_sites = []
            for assigned_site in sites:
                assigned_sites.append(assigned_site.name)
            filters.update({"site": ("in", assigned_sites)})
            roster = frappe.get_all("Post Schedule", filters, fields)
            print(roster)

            master_data = []
            # for key, group in itertools.groupby(roster, key=lambda x: (x['post_abbrv'], x['operations_role'])):
            # 	employees = list(group)
            # 	master_data.append({"employees": employees, "post": key[0], "count": len(employees)})

            for post in roster:
                post.update({"count": 1})
            return roster

        elif "Shift Supervisor" in user_roles:
            shifts = get_assigned_shifts(user_employee.name, site)
            assigned_shifts = []
            for assigned_shift in shifts:
                assigned_shifts.append(assigned_shift.name)
            filters.update({"shift": ("in", assigned_shifts)})

            roster = frappe.get_all("Post Schedule", filters, fields)
            print(roster)
            # for key, group in itertools.groupby(roster, key=lambda x: (x['post_abbrv'], x['operations_role'])):
            # 	employees = list(group)
            # 	master_data.append({"employees": employees, "post": key[0], "count": len(employees)})
            for post in roster:
                post.update({"count": 1})
            return roster

    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)



@frappe.whitelist()
def edit_post(post, post_status, start_date, end_date, paid=0, never_end=0, repeat=0, repeat_freq=None):
    try:
        if never_end:
            project = frappe.get_value("Operations Post", post, ["project"])
            end_date = frappe.get_value("Contracts", {"project": project}, ["end_date"])
        if repeat:
            if repeat_freq == "Daily":
                for date in pd.date_range(start=start_date, end=end_date):
                    create_edit_post(cstr(date.date()), post, post_status, paid)
            elif repeat_freq == "Weekly":
                day = getdate(start_date).strftime('%A')
                for date in pd.date_range(start=start_date, end=end_date):
                    if date.date().strftime('%A') == day:
                        create_edit_post(cstr(date.date()), post, post_status, paid)
            elif repeat_freq == "Monthly":
                for date in month_range(start_date, end_date):
                    # print(cstr(date.date()))
                    if end_date >= cstr(date.date()):
                        print(cstr(date.date()))
                        create_edit_post(cstr(date.date()), post, post_status, paid)
        else:
            for date in pd.date_range(start=start_date, end=end_date):
                create_edit_post(cstr(date.date()), post, post_status, paid)
        frappe.db.commit()
        return True

    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


def create_edit_post(date, post, post_status, paid):
    if frappe.db.exists("Post Schedule", {"date": date, "post": post}):
        post_schedule = frappe.get_doc("Post Schedule", {"date": date, "post": post})
    else:
        post_schedule = frappe.new_doc("Post Schedule")
        post_schedule.post = post
        post_schedule.date = date
    post_schedule.post_status = post_status
    if cint(paid):
        post_schedule.paid = 1
        
    else:
        
        post_schedule.paid = 0
    post_schedule.save(ignore_permissions=True)


@frappe.whitelist()
def day_off(employee, date, repeat=0, repeat_freq=None, repeat_till=None):
    try:
        if repeat:
            if repeat_freq == "Daily":
                for date in pd.date_range(start=date, end=repeat_till):
                    create_day_off(employee, cstr(date.date()))
            elif repeat_freq == "Weekly":
                day = getdate(date).strftime('%A')
                for date in pd.date_range(start=date, end=repeat_till):
                    if date.date().strftime('%A') == day:
                        create_day_off(employee, cstr(date.date()))
            elif repeat_freq == "Monthly":
                for date in month_range(date, repeat_till):
                    # print(cstr(date.date()))
                    if repeat_till >= cstr(date.date()):
                        print(cstr(date.date()))
                        create_day_off(employee, cstr(date.date()))
        else:
            create_day_off(employee, date)
        frappe.db.commit()
        return True
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


def month_range(start, end):
    rng = pd.date_range(start=pd.Timestamp(start) - pd.offsets.MonthBegin(),
                        end=end,
                        freq='MS')
    ret = (rng + pd.offsets.Day(pd.Timestamp(start).day - 1)).to_series()
    ret.loc[ret.dt.month > rng.month] -= pd.offsets.MonthEnd(1)
    return pd.DatetimeIndex(ret)


def create_day_off(employee, date):
    if frappe.db.exists("Employee Schedule", {"employee": employee, "date": date}):
        roster = frappe.get_doc("Employee Schedule", {"employee": employee, "date": date})
        roster.shift = None
        roster.shift_type = None
        roster.operations_role = None
        roster.post_abbrv = None
        roster.site = None
        roster.project = None
    else:
        roster = frappe.new_doc("Employee Schedule")
        roster.employee = employee
        roster.date = date
    roster.employee_availability = "Day Off"
    roster.save(ignore_permissions=True)


@frappe.whitelist()
def get_unassigned_project_employees(project, date, limit_start=None, limit_page_length=20):
    try:
        # Todo add date range
        return frappe.get_list("Employee", fields=["name", "employee_name"], filters={"project": project},
                               order_by="name asc",
                               limit_start=limit_start, limit_page_length=limit_page_length, ignore_permissions=True)
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_unscheduled_employees(date, shift):
    try:
        employees = frappe.db.sql("""
			select name as employee_id, employee_name 
			from `tabEmployee`
			where 
				shift="{shift}"
			and name not in(select employee from `tabEmployee Schedule` where date="{date}" and shift="{shift}")
		""".format(date=date, shift=shift), as_dict=1)
        return employees
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_assigned_employees(shift, date, limit_start=None, limit_page_length=20):
    try:
        # Todo add date range
        return frappe.get_list("Employee Schedule", fields=["employee", "employee_name", "operations_role"],
                               filters={"shift": shift, "date": date}, order_by="employee_name asc",
                               limit_start=limit_start, limit_page_length=limit_page_length, ignore_permissions=True)
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_assigned_projects(employee_id):
    try:
        user, user_roles, user_employee = get_current_user_details()
        if "Operations Manager" in user_roles:
            return frappe.get_list("Project", {"project_type": "External"}, limit_page_length=9999, order_by="name asc")

        if "Projects Manager" in user_roles:
            return frappe.get_list("Project", {"account_manager": employee_id, "project_type": "External"},
                                   limit_page_length=9999, order_by="name asc")
        return []
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_assigned_sites(employee_id, project=None):
    try:
        user, user_roles, user_employee = get_current_user_details()
        filters = {}
        if project:
            filters.update({"project": project})
        if project is None and (
                "Operations Manager" in user_roles or "Projects Manager" in user_roles or "Site Supervisor" in user_roles):
            return frappe.get_list("Operations Site", limit_page_length=9999, order_by="name asc")

        elif "Operations Manager" in user_roles or "Projects Manager" in user_roles:
            return frappe.get_list("Operations Site", filters, limit_page_length=9999, order_by="name asc")

        elif "Site Supervisor" in user_roles:
            filters.update({"account_supervisor": employee_id})
            return frappe.get_list("Operations Site", filters, limit_page_length=9999, order_by="name asc")
        return []

    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_assigned_shifts(employee_id, project=None, site=None):
    try:
        user, user_roles, user_employee = get_current_user_details()
        filters = {}
        if project:
            filters.update({"project": project})
        if site:
            filters.update({"site": site})

        if site is None and (
                "Operations Manager" in user_roles or "Projects Manager" in user_roles or "Site Supervisor" in user_roles):
            return frappe.get_list("Operations Shift", limit_page_length=9999, order_by="name asc")

        elif "Operations Manager" in user_roles or "Projects Manager" in user_roles or "Site Supervisor" in user_roles:
            return frappe.get_list("Operations Shift", filters, limit_page_length=9999, order_by="name asc")

        elif "Shift Supervisor" in user_roles:
            filters.update({"employee": employee_id})
            return frappe.get_all("Operations Shift Supervisors", filters, ['parent as name'], order_by="name asc")
            
            
        return []

    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_departments():
    try:
        return frappe.get_list("Department", {"is_group": 0}, limit_page_length=9999, order_by="name asc")

    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_operations_posts(shift=None):
    try:
        user, user_roles, user_employee = get_current_user_details()

        if shift is None and (
                "Operations Manager" in user_roles or "Projects Manager" in user_roles or "Site Supervisor" in user_roles):
            return frappe.get_list("Operations Post", limit_page_length=9999, order_by="name asc")

        if "Operations Manager" in user_roles or "Projects Manager" in user_roles or "Site Supervisor" in user_roles or "Shift Supervisor" in user_roles:
            return frappe.get_list("Operations Post", {"site_shift": shift}, "post_template", limit_page_length=9999,
                                   order_by="name asc")

        return []
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_designations():
    try:
        return frappe.db.get_list("Designation", limit_page_length=9999, order_by="name asc")
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_post_details(post_name):
    try:
        return frappe.get_value("Operations Post", post_name, "*")
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


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
            rosters = frappe.get_all("Employee Schedule", {"employee": employee, "date": ('>=', start_date)})
            for roster in rosters:
                frappe.delete_doc("Employee Schedule", roster.name, ignore_permissions=True)
                frappe.db.commit()
            return response("Success", 200, None, f"Employee Unscheduled Successfully !")
        else:
            if not end_date:
                end_date = start_date
            for date in pd.date_range(start=start_date, end=end_date):
                if frappe.db.exists("Employee Schedule", {"employee": employee, "date": cstr(date.date())}):
                    roster = frappe.get_doc("Employee Schedule", {"employee": employee, "date": cstr(date.date())})
                    frappe.delete_doc("Employee Schedule", roster.name, ignore_permissions=True)
                    frappe.db.commit()
            return response("Success", 200, None, "Employee Unscheduled Successfully !")
    except Exception as e:
        return response("Internal Server Error !", 500, None, e)

@frappe.whitelist()
def schedule_staff(employee, shift, operations_role, start_date, end_date=None, never=0, repeat_days=[], day_off=[],
                   overtime=0):
    # For each day in the start_date end_date iterable, create an employee schedule for either working or day off
    # depending on if the day falls on a repeat day or day off
    # Key : Monday = 0 ,Sunday = 6

    try:
        if type(start_date) == str:
            start_date = convert_string_to_datetime.get_datetime(start_date).date()

        if not end_date and not never:
            end_date = start_date

        obj_shift = frappe.get_doc("Operations Shift", shift)
        if not obj_shift:
            return response("Bad Request", 400, None, "Shift Does Not Exist")

        obj_operations_role = frappe.get_doc("Operations Role", operations_role)
        if not obj_operations_role:
            return response("Bad Request", 400, None, "Operations Role Does Not Exist!")

        if never:
            end_date = cstr(getdate().year) + "-12-31"

        for date in pd.date_range(start=start_date, end=end_date):
            if getdate(cstr(date.date())).weekday() in repeat_days or getdate(cstr(date.date())).weekday() in day_off:
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
                if overtime:
                    roster.roster_type = "Over-Time"
                roster.save(ignore_permissions=True)
                frappe.db.commit()
        return response("Success", 201, None, f"Employee Scheduled successfully ")
    except Exception as e:
        return response("Internal Server Error !", 500, None, e)


@frappe.whitelist()
def schedule_leave(employee, leave_type, start_date, end_date):
    try:
        for date in pd.date_range(start=start_date, end=end_date):
            print(employee, date.date())
            if frappe.db.exists("Employee Schedule", {"employee": employee, "date": cstr(date.date())}):
                roster = frappe.get_doc("Employee Schedule", {"employee": employee, "date": cstr(date.date())})
                roster.shift = None
                roster.shift_type = None
                roster.project = None
                roster.site = None
            else:
                roster = frappe.new_doc("Employee Schedule")
                roster.employee = employee
                roster.date = cstr(date.date())
            roster.employee_availability = leave_type
            roster.save(ignore_permissions=True)
        return True
    except Exception as e:
        print(e)
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def post_handover(post, date, initiated_by, handover_to, docs_check, equipment_check, items_check, docs_comment=None,
                  equipment_comment=None, items_comment=None, attachments=[]):
    try:
        handover = frappe.new_doc("Post Handover")
        handover.post = post
        handover.date = date
        handover.initiated_by = initiated_by
        handover.handover_to = handover_to
        handover.docs_check = docs_check
        handover.equipment_check = equipment_check
        handover.items_check = items_check
        handover.docs_comment = docs_comment
        handover.equipment_comment = equipment_comment
        handover.items_comment = items_comment
        handover.save()

        for attachment in ast.literal_eval(attachments):
            attach_file(filename=random_string(6) + ".jpg", filedata=base64.b64decode(attachment),
                        doctype=handover.doctype, docname=handover.name)

        return True
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_handover_posts(shift=None):
    try:
        filters = {"handover": 1}
        if shift:
            filters.update({"site_shift": shift})
        return frappe.get_list("Operations Post", filters)
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


def has_checkout(shift, employee):
    checkin = frappe.db.sql("""SELECT * FROM `tabEmployee Checkin` empChkin
							WHERE shift_assignment = '{shift}'
                            AND employee ='{employee}'
                            AND log_type = 'OUT'""".format(shift=shift.name, employee=employee), as_dict=1)
    if checkin:
        return True
    else:
        return False

@frappe.whitelist()
def get_report_comments(report_name):
    try:
        comments = frappe.get_list("Comment", {"reference_doctype": "Shift Report", "reference_name": report_name,
                                               "comment_type": "Comment"}, "*")
        return comments
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_filtered_values(start_date, end_date, project=None, site=None, shift=None, operations_role=None,
                        limit_start=None, page_length=None):
    """
        Dynamically return a list of employee data based on selected filters
    """
    try:
        query_dict, post_filters, master_data = {}, {}, {}
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
            query_dict['operations_role'] = operations_role
            post_filters['project'] = project
            str_filters += ' and es.operations_role = "{}"'.format(operations_role)
        post_filters.update({'date': ['between', (start_date, end_date)], 'post_status': 'Planned'})
        employees = frappe.get_all("Employee", query_dict, ["employee", "employee_name"], order_by="employee_name asc",
                                   start=limit_start, page_length=page_length)
        post_filters.pop('operations_role', None)
        if employees:
            basic_ot_roster = CreateMap(start=start_date, end=end_date, employees=employees, filters=str_filters,
                                        isOt=None).formated_rs
            the_set = set()
            filtered_dict = {}
            for emp_name, schedule in basic_ot_roster.items():
                emp_op_role = frappe.db.get_value("Shift Assignment", {"employee_name": emp_name}, "operations_role")
                if emp_op_role:
                    role_name = frappe.db.get_value("Operations Role", emp_op_role, "post_name")
                    the_set.add(role_name)
                    if not role_name in filtered_dict.keys():
                        filtered_dict.update({role_name: [dict({emp_name: schedule})]})
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
        frappe.log_error(frappe.get_traceback(), 'Roster API Error')


@frappe.whitelist()
def get_opening_values():
    """
		Get the opening values the roster page
	"""
    projects = frappe.db.sql("SELECT name from `tabProject` where status = 'Open' ", as_dict=1)
    shifts = frappe.db.sql("SELECT name from `tabOperations Shift` ", as_dict=1)
    sites = frappe.db.sql("SELECT name from `tabOperations Site` ", as_dict=1)
    employees = frappe.db.sql(
        "SELECT name, employee_name,  designation, department, cell_number from `tabEmployee` where status = 'Active' LIMIT  15 ",
        as_dict=1)
    data = {'projects': projects, 'shifts': shifts, 'sites': sites, 'employees': employees}
    return response("Success", 200, data)


@frappe.whitelist()
def get_opening_post_values():
    """
		Get the opening values for the roster post page
	"""
    posts = frappe.db.sql("SELECT post_name from `tabOperations Post`", as_dict=1)
    return response("Success", 200, posts)
