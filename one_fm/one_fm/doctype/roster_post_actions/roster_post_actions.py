# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate, get_link_to_form
from one_fm.processor import sendemail
from frappe.permissions import get_doctype_roles


class RosterPostActions(Document):

	def autoname(self):
		self.name = self.start_date + "|" + self.end_date + "|" + self.action_type  + "|" + self.supervisor

	def after_insert(self):
		# send notification to supervisor
		user_id = frappe.db.get_value("Employee", self.supervisor, ["user_id"])
		if user_id:
			link = get_link_to_form(self.doctype, self.name)
			subject = _("New Action to {action_type}.".format(action_type=self.action_type))
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
    This function creates a Roster Post Actions document that issues actions to supervisors to fill post types that are not filled for a given date range.
    """
    # clear existing

    op_shift = frappe.db.sql(f"""
    	SELECT
			ch.supervisor, p.name
		FROM
			`tabOperations Shift` p, `tabOperations Shift Supervisor` ch
        WHERE
        	p.status='Active' and ch.parent=p.name
    """, as_dict=1)
    shift_dict = {}
    for item in op_shift:
        if item.supervisor in shift_dict.keys():
            shift_dict[item.supervisor].append(item.name)
        else:
            shift_dict[item.supervisor] = [item.name]

    # start date to be from tomorrow
    start_date = add_to_date(cstr(getdate()), days=1)
    # end date to be 14 days after start date
    end_date = add_to_date(start_date, days=14)

    operations_roles_not_filled_set = set()

    list_of_dict_of_operations_roles_not_filled = []


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
        AND pr.is_active='Yes'
        AND ps.date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY date ASC
    """, as_dict=1)


    # Fetch employee schedules for employees who are working
    employee_schedules = frappe.db.get_list("Employee Schedule", {'date': ['between', (start_date, end_date)], 'employee_availability': 'Working'}, ["date", "shift", "operations_role"], order_by="date asc")


    for ps in post_schedules:
        # if there is not any employee schedule that matches the post schedule for the specified date, add to post types not filled
        if not any(es.date == ps.date and es.shift == ps.shift and es.operations_role == ps.operations_role for es in employee_schedules):
            if ps.operations_role:
                operations_roles_not_filled_set.add(ps.operations_role)
                list_of_dict_of_operations_roles_not_filled.append(ps)

    # Convert set to tuple for passing it in the sql query as a parameter
    operations_roles_not_filled = tuple(operations_roles_not_filled_set)

    if not operations_roles_not_filled:
        return

    #Fetch supervisor and post types in his/her shift
    result = frappe.db.sql("""select sv.employee, group_concat(distinct ps.operations_role),
            sh.site
            from `tabPost Schedule` ps
            join `tabOperations Shift Supervisor` sh on sh.parent = ps.shift
            join `tabEmployee` sv on sh.supervisor=sv.employee
            where ps.operations_role in {operations_roles}
            AND sh.status='Active' AND sv.status='Active'
            group by sv.employee""".format(operations_roles=operations_roles_not_filled))


    # For each supervisor, create post actions to fill post type specifying the post types not filled

    for res in result:
        try:
            supervisor = res[0]
            site = frappe.get_value("Operations Site", res[2], 'account_supervisor')
            operations_roles = res[1].split(",")

            check_list = []
            second_check_list = []
            for val in list_of_dict_of_operations_roles_not_filled:
                if val["operations_role"] in operations_roles and val["shift"] in shift_dict[supervisor]:
                    check_list.append(val)

            for item in check_list:
                for second_item in second_check_list:
                    if (item["date"] == second_item["date"]) and (item["shift"] == second_item["shift"]) and (item["operations_role"] == second_item["operations_role"]):
                        second_item["quantity"] = second_item["quantity"] + 1
                        break
                item.update({"quantity": 1})

                second_check_list.append(item)
                check_list.remove(item)

            if second_check_list and len(second_check_list) > 0:
                roster_post_actions_doc = frappe.new_doc("Roster Post Actions")
                roster_post_actions_doc.start_date = start_date
                roster_post_actions_doc.end_date = end_date
                roster_post_actions_doc.status = "Pending"
                roster_post_actions_doc.action_type = "Fill Post Type"
                roster_post_actions_doc.supervisor = supervisor
                roster_post_actions_doc.site_supervisor = site

                for obj in second_check_list:
                    roster_post_actions_doc.append('operations_roles_not_filled', {
                        'operations_role': obj.get("operations_role"),
                        "operations_shift": obj.get("shift"),
                        "date": obj.get("date"),
                        "quantity": obj.get("quantity") if obj.get("quantity") else 1
                    })

                roster_post_actions_doc.save()
                frappe.db.commit()
        except:
            frappe.log_error(frappe.get_traceback(), "Error while creating post actions")

        del check_list
