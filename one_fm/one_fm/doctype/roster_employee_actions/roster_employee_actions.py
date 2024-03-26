# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate, get_link_to_form
from one_fm.processor import sendemail
from frappe.permissions import get_doctype_roles
import datetime
from datetime import timedelta

class RosterEmployeeActions(Document):
	def autoname(self):
		self.name = str(self.start_date) + "|" + str(self.end_date) + "|" + self.action_type  + "|" + self.supervisor

	def after_insert(self):
		# send notification to supervisor
		user_id = frappe.db.get_value("Employee", self.supervisor, ["user_id"])
		if user_id:
			link = get_link_to_form(self.doctype, self.name)
			subject = _("New Action to {action_type}.".format(action_type=self.action_type))
			message = _("""
				You have been issued a Roster Employee Action.<br>
				Please review the employees assigned to you, take necessary actions and update the status.<br>
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
			return '(`tabRoster Employee Actions`.`supervisor`="{employee}" or `tabRoster Employee Actions`.`site_supervisor`="{employee}")'.format(employee = employee)

	return ""


def create():
	frappe.enqueue(create_roster_employee_actions, is_async=True, queue='long')


def create_roster_employee_actions():
    """
    This function creates a Roster Employee Actions document and issues notifications to relevant supervisors
    directing them to schedule employees that are unscheduled and assigned to them.
    It computes employees not scheduled for the span of two weeks, starting from tomorrow.
    """

    # start date to be from tomorrow
    start_date = getdate(add_to_date(cstr(getdate()), days=1))
    # end date to be 14 days after start date
    end_date = getdate(add_to_date(start_date, days=14))
    #-------------------- Roster Employee actions ------------------#
    # fetch employees that are active and don't have a schedule in the specified date range
    active_employees = frappe.db.sql("""select employee from `tabEmployee` where status = 'Active' AND shift_working = 1""", as_dict=1)

    active_employees_combinations = [(employee.employee, date) for employee in active_employees for date in [(start_date + timedelta(days=x)).strftime('%Y-%m-%d') for x in range((end_date - start_date).days + 1)]]

    employees_rostered = frappe.db.sql(f"""SELECT s.employee, s.date
                                    FROM `tabEmployee Schedule` s
                                    WHERE s.date >= '{start_date}' AND s.date <= '{end_date}'
                                    """, as_dict= True)

    employees_rostered_combination = [(roster.employee, (roster.date).strftime('%Y-%m-%d')) for roster in employees_rostered]

    employees_not_rostered = set(active_employees_combinations) - set(employees_rostered_combination)
    try:
        data_dict = {obj[0]: list() for obj in employees_not_rostered}
        for item in employees_not_rostered:
            try:
                data_dict.get(item[0]).append(item[1])
            except Exception as e:
                continue
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error while genrating missing dates(Roster Employee Actions)")
        data_dict = dict()

    list_of_leaves_within_employee_action_period = frappe.db.get_list("Leave Application", {"status": "Approved", "from_date":["<", start_date ], "to_date": [">", end_date]}, pluck="employee")

    employees = ()

    # fetch employees that are not rostered from the result returned by the query and append to tuple
    for emp in employees_not_rostered:
        if emp[0] in list_of_leaves_within_employee_action_period:
            continue
        employees = employees + emp

    # fetch supervisors and list of employees(not rostered) under them
    result = frappe.db.sql("""select sv.employee, sv.site, group_concat(e.employee)
            from `tabEmployee` e
            join `tabOperations Shift Supervisor` sh on sh.parent = e.shift
            join `tabEmployee` sv on sh.supervisor=sv.employee
            where e.employee in {employees}
	    	AND sh.status='Active'
            group by sv.employee """.format(employees=employees))

    # for each supervisor, create a roster action
    for res in result:
        try:
            supervisor = res[0]
            site_supervisor = frappe.get_value('Operations Site', res[1], 'account_supervisor')
            employees = res[2].split(",")

            roster_employee_actions_doc = frappe.new_doc("Roster Employee Actions")
            roster_employee_actions_doc.start_date = start_date
            roster_employee_actions_doc.end_date = end_date
            roster_employee_actions_doc.status = "Pending"
            roster_employee_actions_doc.action_type = "Roster Employee"
            roster_employee_actions_doc.supervisor = supervisor
            roster_employee_actions_doc.site_supervisor = site_supervisor

            for emp in employees:
                roster_employee_actions_doc.append('employees_not_rostered', {
                    'employee': emp,
                    "missing_dates": ", ".join(data_dict.get(emp))
                })

            roster_employee_actions_doc.save()
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Error while generating Roster employee actions")
            continue
        frappe.db.commit()

    #-------------------- END Roster Employee actions ------------------#
