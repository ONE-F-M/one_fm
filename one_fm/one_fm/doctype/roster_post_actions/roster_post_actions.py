# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from collections import Counter



import frappe
from frappe import _
from collections import defaultdict
from frappe.model.document import Document
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate, get_link_to_form, add_days, add_months, get_first_day, get_last_day
from one_fm.processor import sendemail
from frappe.permissions import get_doctype_roles
from one_fm.one_fm.page.roster.roster import get_current_user_details

class RosterPostActions(Document):
    def after_insert(self):
        # send notification to supervisor
        user_id = frappe.db.get_value("Employee", self.supervisor, ["user_id"])
        if user_id:
            link = get_link_to_form(self.doctype, self.name)
            subject = _("New Action Required")
            message = _("""
				You have been issued a Roster Post Action.<br>
				Please review the Post Type for the specified date in the roster, take necessary actions and update the status.<br>
				Link: {link}""".format(link=link))
            sendemail([user_id], subject=subject, message=message, reference_doctype=self.doctype, reference_name=self.name)




@frappe.whitelist()
def get_permission_query_conditions(user):
	"""
		Method used to set the permission to get the list of docs (Example: list view query)
		Called from the permission_query_conditions of hooks for the DocType Roster Employee Actions
		args:
			user: name of User object or current user
		return conditions query
	"""
	if not user: user = frappe.session.user

	if user == "Administrator":
		return ""

	# Fetch all the roles associated with the current user
	user_roles = frappe.get_roles(user)

	if "System Manager" in user_roles:
		return ""
	if "Operation Admin" in user_roles:
		return ""

	# Get roles allowed to Roster Employee Actions doctype
	doctype_roles = get_doctype_roles('Roster Employee Actions')
	# If doctype roles is in user roles, then user permitted
	role_exist = [role in doctype_roles for role in user_roles]

	if role_exist and len(role_exist) > 0 and True in role_exist:
		employee = frappe.get_value("Employee", {"user_id": user}, ["name"])
		if "Shift Supervisor" in user_roles or "Site Supervisor" in user_roles:
			return '(`tabRoster Post Actions`.`supervisor`="{employee}" or `tabRoster Post Actions`.`site_supervisor`="{employee}")'.format(employee = employee)

	return ""

def create():
	frappe.enqueue(create_roster_post_actions, is_async=True, queue='long')

def create_roster_post_actions():
    """
    This function creates a Roster Post Actions document that issues actions to supervisors to fill operation roles that are not filled or overfilled for a given date range.
    """
    tomorrow = add_days(getdate(), 1)
    next_month = add_months(tomorrow, 1)

    durations = [
    	{
    		"start_date": tomorrow,
    		"end_date": get_last_day(tomorrow)
    	},
    	{
    		"start_date": get_first_day(next_month),
    		"end_date": get_last_day(next_month)
    	},
    ]

    for duration in durations:
        start_date = duration["start_date"]
        end_date = duration["end_date"]

        result_dict = defaultdict(lambda: {
            "not_filled": [],
            "over_filled": []
        })

        # Fetch post schedules in the date range that are active
        post_schedules = frappe.db.sql(f"""
            SELECT ps.name, ps.date, ps.shift, ps.operations_role, ps.post
            FROM `tabPost Schedule` ps
            JOIN `tabOperations Shift` osh ON ps.shift = osh.name
            JOIN `tabOperations Site` os ON ps.site = os.name
            JOIN `tabOperations Post` op ON ps.post = op.name
            JOIN `tabOperations Role` opr ON ps.operations_role = opr.name
            JOIN `tabProject` pr ON opr.project = pr.name
            WHERE ps.post_status = 'Planned'
            AND osh.status = 'Active'
            AND os.status = 'Active'
            AND op.status = 'Active'
            AND opr.status = 'Active'
            AND pr.is_active = 'Yes'
            AND ps.date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY date ASC
        """, as_dict=1)

        # Fetch employee schedules in the date range that are working
        employee_schedules = frappe.db.sql(f"""
            SELECT es.date, es.shift, es.operations_role
            FROM `tabEmployee Schedule` es
            WHERE es.employee_availability = 'Working'
            AND es.date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY date ASC
        """, as_dict=1)

        post_counts = Counter((ps["date"], ps["operations_role"], ps["shift"]) for ps in post_schedules)
        employee_counts = Counter((es["date"], es["operations_role"], es["shift"]) for es in employee_schedules)

        for key, post_count in post_counts.items():
            emp_count = employee_counts.get(key, 0)  # Default to 0 if no employee schedule exists
            date, role, shift = key

            if post_count > emp_count: # If post schedules are more than employee schedules
                result_dict[(role, shift)]["not_filled"].append({
                    "date": date,
                    "quantity": post_count - emp_count
                })

        for key, emp_count in employee_counts.items():
            post_count = post_counts.get(key, 0)  # Default to 0 if no post schedule exists
            date, role, shift = key

            if emp_count > post_count: # If employee schedules are more than post schedules
                result_dict[(role, shift)]["over_filled"].append({
                    "date": date,
                    "quantity": emp_count - post_count
                })

        operations_shifts_info_result = frappe.db.sql("""
            SELECT
                op_shift.name AS shift,
                op_shift.site,
                op_shift.project,
                (
                    SELECT oss.supervisor
                    FROM `tabOperations Shift Supervisor` oss
                    WHERE oss.parent = op_shift.name
                    ORDER BY oss.idx ASC
                    LIMIT 1
                ) AS shift_supervisor,
                op_site.account_supervisor AS site_supervisor
            FROM `tabOperations Shift` op_shift
            LEFT JOIN `tabOperations Site` op_site ON op_site.name = op_shift.site
            WHERE op_shift.status = 'Active'
        """, as_dict=True)

        operations_shifts_info = {
            item["shift"]: item
            for item in operations_shifts_info_result
        }

        # Create one Roster Post Actions document per (operations_role, shift)
        for (role, shift), data in result_dict.items():
            shift_details = operations_shifts_info.get(shift) # If no shift details are found then it means employee schedules exist for inactive shift which should not

            if (not data["not_filled"] and not data["over_filled"]) or not shift_details:
                continue

            try:
                # If start date lies within current month then check for yesterday else check for first day of month (for next month)
                yesterday_repeat_count = frappe.db.get_value(
                    "Roster Post Actions",
                    {
                        "start_date": add_days(start_date, -1) if getdate(start_date).month == getdate(nowdate()).month and getdate(start_date).year == getdate(nowdate()).year else get_first_day(start_date),
                        "operations_role": role,
                        "operations_shift": shift,
                        "creation": ["between", [add_days(nowdate(), -1), nowdate()]],
                    },
                    ["repeat_count"]
                )

                roster_post_actions_doc = frappe.new_doc("Roster Post Actions")
                roster_post_actions_doc.start_date = start_date
                roster_post_actions_doc.end_date = end_date
                roster_post_actions_doc.repeat_count = (yesterday_repeat_count or 0) + 1
                roster_post_actions_doc.status = "Pending"
                roster_post_actions_doc.supervisor = shift_details["shift_supervisor"]
                roster_post_actions_doc.site_supervisor = shift_details["site_supervisor"]
                roster_post_actions_doc.operations_role = role
                roster_post_actions_doc.operations_shift = shift
                roster_post_actions_doc.operations_site = shift_details["site"]
                roster_post_actions_doc.project = shift_details["project"]

                for i in data["not_filled"]:
                    roster_post_actions_doc.append('operations_roles_not_filled', {
                        "date": i["date"],
                        "quantity": i["quantity"]
                    })

                for i in data["over_filled"]:
                    roster_post_actions_doc.append('operations_roles_over_filled', {
                        "date": i["date"],
                        "quantity": i["quantity"]
                    })

                roster_post_actions_doc.save()
            except:
                frappe.log_error(frappe.get_traceback(), "Error while creating roster post actions")

        frappe.db.commit()


@frappe.whitelist()
def get_overfilled_underfilled_posts():
    """ Get the roster post action data for the next 2 weeks"""
    user, user_roles, user_employee = get_current_user_details()

    if not user_employee:
        frappe.throw("No employee record linked to current user")
    # start date to be from tomorrow
    start_date = add_to_date(cstr(getdate()), days=1)
    # end date to be 14 days after start date
    end_date = add_to_date(start_date, days=15)
    shifts = get_applicable_shifts(user_employee.get('name'),user_roles)
    if not shifts:
        return {
            "under_filled": f"""<div class='dialog-box' style='padding: 20px; background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; text-align: center;'>
                            <h4 style='margin: 0; color: #343a40;'>No Shifts found for User {frappe.session.user}</h4>
                            </div>""",
            "over_filled": f"""<div class='dialog-box' style='padding: 20px; background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; text-align: center;'>
                            <h4 style='margin: 0; color: #343a40;'>No Shifts found for User {frappe.session.user}</h4>
                            </div>"""
        }


        # frappe.throw("No shifts found")
    shift_tuple = tuple(shifts)
    shifts_sub_query = f" AND ps.shift in {shift_tuple}" if len(shift_tuple) > 1 else f" AND ps.shift = '{shift_tuple[0]}'"
    # Fetch post schedules in the date range that are active
    post_schedules = frappe.db.sql(f"""
		SELECT ps.name, ps.date, ps.shift, ps.operations_role, ps.post
        FROM `tabPost Schedule` ps
        JOIN `tabOperations Site` os ON ps.site=os.name
        JOIN `tabOperations Post` op ON ps.post=op.name
        JOIN `tabOperations Role` opr ON ps.operations_role=opr.name
        JOIN `tabProject` pr ON opr.project=pr.name
          WHERE
        ps.post_status='Planned' AND os.status='Active'
        AND op.status='Active' AND opr.status='Active'
        AND pr.is_active='Yes' {shifts_sub_query}
        AND ps.date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY date ASC
    """, as_dict=1)


    # Fetch employee schedules for employees who are working
    employee_schedules = frappe.db.get_all("Employee Schedule", {'shift':['IN',shift_tuple],'date': ['between', (start_date, end_date)], 'employee_availability': 'Working'}, ["date", "shift", "operations_role"], order_by="date asc")
    roles_not_filled = set()
    roles_over_filled_set = set()
    list_of_dict_of_operations_roles_not_filled = []
    list_of_dict_of_operations_roles_over_filled = []
    post_counts = Counter((ps["date"], ps["operations_role"], ps["shift"]) for ps in post_schedules)
    employee_counts = Counter((es["date"], es["operations_role"], es["shift"]) for es in employee_schedules)
    # Create a set of tuples (date, shift, operations_role) from employee_schedules for O(1) lookup

    employee_schedule_set = {(es["date"], es["shift"], es["operations_role"]) for es in employee_schedules}
    # First check for unfilled positions
    for ps in post_schedules:
        if ps.operations_role and (ps.date, ps.shift, ps.operations_role) not in employee_schedule_set:
            roles_not_filled.add(ps.operations_role)
            list_of_dict_of_operations_roles_not_filled.append(ps)

    # Then check for overfilled positions separately
    post_schedule_dict = {(ps["date"], ps["operations_role"], ps["shift"]): ps for ps in post_schedules}
    for key, emp_count in employee_counts.items():
        post_count = post_counts.get(key, 0)
        if emp_count > post_count:
            matching_ps = post_schedule_dict.get(key)
            if matching_ps:
                roles_over_filled_set.add(key[1])
                list_of_dict_of_operations_roles_over_filled.append({
                    "name": matching_ps["name"],
                    "date": key[0],
                    "shift": key[2],
                    "operations_role": key[1],
                    "post": matching_ps["post"],
                    "quantity": emp_count - post_count
                })


    roles_not_filled_html = render_operations_roles_html(list_of_dict_of_operations_roles_not_filled)\
          if list_of_dict_of_operations_roles_not_filled else "<div class='alert text-center' role='alert'><h4 class='mb-0'>No Post Count Issues</h4><h5 class='mb-0'>Posts are filled correctly for the next 2 weeks. Great Job!</h5></div>"
    role_over_filled_html = render_operations_roles_html(list_of_dict_of_operations_roles_over_filled,is_over_filled_list=True)\
        if list_of_dict_of_operations_roles_over_filled else "<div class='alert text-center' role='alert'><h4 class='mb-0'>No Post Count Issues</h4><h5 class='mb-0'>Posts are filled correctly for the next 2 weeks. Great Job!</h5></div>"

    return {
         'under_filled':roles_not_filled_html,
         'over_filled':role_over_filled_html
    }




def get_applicable_shifts(employee,user_roles):
    try:
        shifts = []
        if "Operations Manager" in user_roles:
            shifts += get_all_shifts()
        if "Projects Manager" in user_roles:
            shifts += get_project_shifts(employee)
        if "Site Supervisor" in user_roles:
            shifts += get_site_shifts(employee)
        if "Shift Supervisor" in user_roles:
            shifts += get_assigned_shifts(employee)
        if not shifts:
            return []
        return list(set(shifts)) #Remove duplicates

    except:
         frappe.log_error(title = "Error Fetching Post Data",message=frappe.get_traceback())
         frappe.throw("An Error Occurred")


def get_all_shifts():
     all_shifts = frappe.get_all("Operations Shift",{'status':'Active'},pluck ="name")
     return all_shifts


def get_project_shifts(employee):
    active_projects = frappe.get_all("Project",{'status':"Open",'account_manager':employee},pluck ="name")
    if active_projects:
        all_shifts = frappe.get_all("Operations Shift",{'status':'Active','project':['in',active_projects]},pluck ="name")
        return all_shifts
    else:
        return []

def get_site_shifts(employee):
    active_sites = frappe.get_all("Operations Site",{'status':"Active",'account_supervisor':employee},pluck ="name")
    if active_sites:
        all_shifts = frappe.get_all("Operations Shift",{'status':'Active','site':['in',active_sites]},pluck ="name")
        return all_shifts
    else:
        return []


def get_assigned_shifts(employee):
    all_shifts = frappe.db.sql(f"""Select os.name from `tabOperations Shift` os
                                JOIN `tabOperations Shift Supervisor` opss ON os.name = opss.parent
                               WHERE os.status ='Active' and opss.supervisor = '{employee}' """,as_dict=1)
    return [i.name for i in all_shifts]



def render_operations_roles_html(post_list, is_over_filled_list=False):
    """
    Renders HTML table for operations roles that are not filled and overfilled
    Args:
        not_filled_list: List of dicts containing unfilled operations roles
        over_filled_list: List of dicts containing overfilled operations roles
    Returns:
        HTML string containing formatted table
    """


    html = "<table class='table table-bordered'>"
    html += """<thead>
                <tr>
                    <th>Operations Post</th>
                    <th>Operations Role</th>
                    <th>Date</th>
                    <th>Shift</th>
                    <th>Quantity</th>

                </tr>
            </thead><tbody>"""

    # Add not filled roles
    for item in post_list:
        html += f"""<tr>
                        <td>{item.get('post', '')}</td>
                        <td><a  target="_blank" href="/app/roster?main_view='roster'&sub_view='basic'&roster_type='basic'&operations_role={item.get('post')}">{item.get('operations_role', '')}</a></td>
                        <td>{item.get('date', '')}</td>
                        <td>{item.get('shift', '')}</td>
                        {f'<td>{item.get("quantity", "")}</td>'  if  is_over_filled_list else '<td>1</td>' }


                    </tr>"""
    html += "</tbody></table>"
    return html
