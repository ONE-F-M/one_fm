# Copyright (c) 2025, one_fm and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from collections import Counter
from frappe.utils import today

class LeaveHandover(Document):
	def validate(self):
		if not self.handover_items:
			frappe.throw(_("No responsibilities found for {0}").format(self.employee_name))

	def on_submit(self):
		no_reliever_rows = []
		not_accepted_rows = []

		for item in self.handover_items:
			if not item.reliever:
				no_reliever_rows.append(str(item.idx))

			if item.status != "Accepted":
				not_accepted_rows.append(str(item.idx))

		if no_reliever_rows:
			frappe.throw(
				msg=_("Ensure to set the reliever in row(s) {0} and then proceed").format(", ".join(no_reliever_rows)),
				title=_("No Reliever Set")
			)

		if not_accepted_rows:
			frappe.throw(
				msg=_("Ensure that the reliever in row(s) {0} has accepted and update the status.").format(", ".join(not_accepted_rows)),
				title=_("Not Accepted")
			)

		self.db_set("status", "Submitted")

		if self.leave_start_date == today():
			self.action_handover(revert=False)

	def action_handover(self, revert=False):
		if revert and self.employee_user_id != frappe.session.user:
			frappe.throw(_("You are not authorized to revert this Leave Handover."))
		self.update_doc_assignment(revert=revert)
		if not revert:
			self.assign_role_on_handover()
		else:
			self.revert_roles_assignment()
		status = "Reverted" if revert else "Transferred"
		self.db_set("status", status)

	def update_doc_assignment(self, revert=False):
		for item in self.handover_items:
			field_to_update = {
				"Project": "account_manager",
				"Operations Site": "account_supervisor",
				"Process Task": "employee",
				"Employee": "reports_to",
			}.get(item.reference_doctype)

			if field_to_update:
				employee = item.reliever if not revert else self.employee
				values_to_update = {field_to_update: employee}
				name_field_to_update = {
					"Project": "manager_name",
					"Operations Site": "account_supervisor_name",
					"Process Task": "employee_name",
				}.get(item.reference_doctype)

				if name_field_to_update:
					values_to_update[name_field_to_update] = item.reliever_name if not revert else self.employee_name
				frappe.db.set_value(item.reference_doctype, item.reference_docname, values_to_update)
				if revert:
					frappe.db.set_value("Handover Item", item.name, "status", "Reverted")

	def assign_role_on_handover(self):
		for item in self.handover_items:
			if not item.reliever:
				continue

			reliever_user_id = frappe.db.get_value("Employee", item.reliever, "user_id")
			if not reliever_user_id:
				continue

			# Define the roles based on the reference doctype
			doctype_to_check = item.reference_doctype
			if doctype_to_check not in ["Project", "Operations Site", "Process Task", "Employee"]:
				continue

			roles_to_assign = get_user_roles_for_doctype(reliever_user_id, doctype_to_check)

			# Get the user document and their current roles
			reliever_user = frappe.get_doc("User", reliever_user_id)
			user_roles = frappe.get_roles(reliever_user_id)

			newly_assigned_roles = []

			# Check and assign each role
			frappe.db.set_value("Handover Item", item.name, "reliever_role_profile", reliever_user.role_profile_name)
			reliever_user.db_set("role_profile_name", None)  # Clear role profile to avoid conflicts
			for role in roles_to_assign:
				if frappe.db.exists("Role", role) and role not in user_roles:
					reliever_user.add_roles(role)
					newly_assigned_roles.append(role)

			# If any new roles were assigned, update the handover item
			if newly_assigned_roles:
				frappe.db.set_value(
					"Handover Item",
					item.name,
					"roles_assigned",
					", ".join(newly_assigned_roles)
				)

	def revert_roles_assignment(self):
		for item in self.handover_items:
			if not item.reliever:
				continue

			reliever_user_id = frappe.db.get_value("Employee", item.reliever, "user_id")
			if not reliever_user_id:
				continue

			reliever_user = frappe.get_doc("User", reliever_user_id)

			if item.roles_assigned:
				roles_to_revert = [role.strip() for role in item.roles_assigned.split(",")]
				for role in roles_to_revert:
					if frappe.db.exists("Has Role", {"parent": reliever_user.name, "role": role}):
						reliever_user.remove_roles(role)

			if item.reliever_role_profile:
				reliever_user.db_set("role_profile_name", item.reliever_role_profile)


@frappe.whitelist()
def get_user_roles_for_doctype(user, doctype):
    """
    Returns a list of roles that a user has for a given DocType,
    only if the role grants at least one permission (read, write, create, etc.).
    """
    if not user or not doctype:
        return []

    user_roles = frappe.get_roles(user)

    if "System Manager" in user_roles:
        return ["System Manager"]

    # List of permission fields in DocPerm
    perm_fields = [
        "read", "write", "create", "delete", "submit", "cancel", "amend",
        "report", "import", "export", "print", "email", "share"
    ]
    # Create a list of OR filters to check if any permission is granted
    or_filters = [[field, "=", 1] for field in perm_fields]

    doctype_perms = frappe.get_all(
        "DocPerm",
        fields=["role"],
        filters={"parent": doctype, "role": ("in", user_roles)},
        or_filters=or_filters,
        distinct=True
    )

    return [d.role for d in doctype_perms]

@frappe.whitelist()
def get_handover_data(leave_application):
	handover_items = []
	leave_application_doc = frappe.get_doc("Leave Application", leave_application)
	employee = leave_application_doc.employee

	# Fetch projects
	projects = frappe.get_all(
		"Project",
		filters={"status": "Open", "account_manager": employee},
		fields=["name"],
	)
	for project in projects:
		handover_items.append({
			"reference_doctype": "Project",
			"reference_docname": project.name,
		})

	# Fetch operations sites
	sites = frappe.get_all(
		"Operations Site",
		filters={"status": "Active", "account_supervisor": employee},
		fields=["name"],
	)
	for site in sites:
		handover_items.append({
			"reference_doctype": "Operations Site",
			"reference_docname": site.name,
		})

	# Fetch process tasks
	tasks = frappe.get_all(
		"Process Task",
		filters={"is_active": 1, "employee": employee},
		fields=["name"],
	)
	for task in tasks:
		handover_items.append({
			"reference_doctype": "Process Task",
			"reference_docname": task.name,
		})

	# Fetch employees reporting to the leave applicant
	employees = frappe.get_all(
		"Employee",
		filters={"status": ("in", ["Active", "Vacation"]), "reports_to": employee},
		fields=["name"],
	)
	for emp in employees:
		handover_items.append({
			"reference_doctype": "Employee",
			"reference_docname": emp.name,
		})

	return {
		"employee": leave_application_doc.employee,
		"employee_name": leave_application_doc.employee_name,
		"leave_application": leave_application_doc.name,
		"leave_start_date": leave_application_doc.from_date,
		"resumption_date": leave_application_doc.resumption_date,
		"handover_items": handover_items,
	}

@frappe.whitelist()
def reliever_assignment_on_leave_start(date=None):
	if not date:
		date = today()
	leave_handovers = frappe.get_all(
		"Leave Handover",
		filters={
			"leave_start_date": ["<=", date],
			"resumption_date": [">", date],
			"status": "Submitted"
		},
		fields=["name", "employee"]
	)
	for leave_handover in leave_handovers:
		handover = frappe.get_doc("Leave Handover", leave_handover.name)
		handover.action_handover()