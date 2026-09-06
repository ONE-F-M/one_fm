import frappe
from one_fm.custom.assignment_rule.assignment_rule import delete_assignment_rule

FYI_OFFBOARDING_OFFICER_RULES = [
	"Resignation - FYI Offboarding Officer",
	"Employee Resignation Date Adjustment - FYI Offboarding Officer",
	"Employee Resignation Withdrawal - FYI Offboarding Officer",
]

# Assignment Rules created by these names were deleted, not renamed. A rule
# can only unassign ToDos stamped with its own name, so ToDos they created
# are permanently orphaned. Value is the workflow_state each was tied to.
ASSIGNMENT_RULE_STAGE = {
	"Resignation - Pending Supervisor": "Pending Supervisor",
	"Resignation - Pending Operations Manager": "Pending Operations Manager",
	"Resignation - Relieving Date Correction": "Pending Relieving Date Correction",
}

ROLE_ASSIGNMENTS = {
	"Project Manager": [
		"m.alsubaie@one-fm.com",
		"abdullah@one-fm.com",
		"a.alazmi@one-fm.com",
		"m.mothaffar@one-fm.com",
	],
	"Security Manager": ["s.alyousef@one-fm.com"],
	"Janitorial Head Supervisor": ["k.patel@one-fm.com"],
}


def execute():
	staff_new_workflow_roles()
	remove_fyi_offboarding_officer_rules()
	reroute_t4_resignations_to_t4_admin()
	reroute_stale_operations_manager_resignations()
	reroute_stale_date_adjustment_operations_manager_records()
	close_orphaned_assignment_rule_todos()
	backfill_current_salary()


def remove_fyi_offboarding_officer_rules():
	# Same doctype can only carry one auto-assignment per save (Frappe's
	# assignment_rule.apply() stops at the first rule that succeeds), so this
	# rule was silently starving the real Supervisor/Project Manager
	# assignment on every resignation that reached Pending Supervisor.
	frappe.db.set_value(
		"ToDo", {"assignment_rule": ["in", FYI_OFFBOARDING_OFFICER_RULES], "status": "Open"},
		"status", "Cancelled",
	)
	for rule_name in FYI_OFFBOARDING_OFFICER_RULES:
		delete_assignment_rule({"name": rule_name})


def staff_new_workflow_roles():
	for role, emails in ROLE_ASSIGNMENTS.items():
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert()

		for email in emails:
			if not frappe.db.exists("User", email):
				frappe.log_error(
					title="Employee Resignation v2 migration: role assignee missing",
					message=f"{email} does not exist as a User -- could not assign the {role} role.",
				)
				continue
			if not frappe.db.exists("Has Role", {"parent": email, "role": role}):
				frappe.get_doc({
					"doctype": "Has Role",
					"parent": email,
					"parenttype": "User",
					"parentfield": "roles",
					"role": role,
				}).insert()


def reroute_t4_resignations_to_t4_admin():
	# T4 sub-flow states are excluded -- a record already past T4 Admin
	# shouldn't be bounced back to redo review it already got.
	t4_chain_states = ("Pending T4 Admin", "Pending Janitorial Head Supervisor", "Pending Security Manager")
	rows = frappe.db.sql(
		"""
		select name
		from `tabEmployee Resignation`
		where shift_category = 'T4'
		and workflow_state not in ('Draft', 'Approved', 'Withdrawn', %s, %s, %s)
		""",
		t4_chain_states,
		as_dict=True,
	)

	for row in rows:
		try:
			doc = frappe.get_doc("Employee Resignation", row.name)
			doc.set_t4_admin()
			frappe.db.set_value(
				"Employee Resignation", row.name,
				{"workflow_state": "Pending T4 Admin", "t4_admin": doc.t4_admin},
				update_modified=False,
			)
			if not doc.t4_admin:
				frappe.log_error(
					title="Employee Resignation v2 migration: no T4 Admin resolved",
					message=f"{row.name} moved to Pending T4 Admin but no user holds that role.",
				)
		except Exception:
			frappe.log_error(
				title="Employee Resignation v2 migration: T4 reroute failed",
				message=f"{row.name}: {frappe.get_traceback()}",
			)


def reroute_stale_operations_manager_resignations():
	rows = frappe.db.sql(
		"""
		select name
		from `tabEmployee Resignation`
		where workflow_state = 'Pending Operations Manager'
		and shift_category != 'T4'
		""",
		as_dict=True,
	)

	for row in rows:
		try:
			doc = frappe.get_doc("Employee Resignation", row.name)
			doc.set_project_manager()
			frappe.db.set_value(
				"Employee Resignation", row.name,
				{"workflow_state": "Pending Project Manager", "project_manager": doc.project_manager},
				update_modified=False,
			)

			if doc.project_manager:
				from frappe.desk.form.assign_to import add as assign_to_add
				assign_to_add({
					"doctype": "Employee Resignation",
					"name": row.name,
					"assign_to": [doc.project_manager],
					"description": "Please review and approve this Resignation.",
				})
			else:
				frappe.log_error(
					title="Employee Resignation v2 migration: no Project Manager resolved",
					message=f"{row.name} moved to Pending Project Manager but no Project Manager could be resolved.",
				)
		except Exception:
			frappe.log_error(
				title="Employee Resignation v2 migration: Operations Manager reroute failed",
				message=f"{row.name}: {frappe.get_traceback()}",
			)


def reroute_stale_date_adjustment_operations_manager_records():
	# Pending Operations Manager was also removed from this doctype's workflow.
	# shift_category/t4_route/project_manager are mirrored from the parent
	# Employee Resignation (set_approver()), so the same T4-vs-Operations split
	# applies: T4 goes back to Pending T4 Admin, everyone else to Pending
	# Project Manager.
	rows = frappe.db.sql(
		"""
		select name
		from `tabEmployee Resignation Date Adjustment`
		where workflow_state = 'Pending Operations Manager'
		""",
		as_dict=True,
	)

	for row in rows:
		try:
			doc = frappe.get_doc("Employee Resignation Date Adjustment", row.name)
			doc.set_approver()

			if doc.shift_category == "T4":
				frappe.db.set_value(
					"Employee Resignation Date Adjustment", row.name,
					{"workflow_state": "Pending T4 Admin", "t4_admin": doc.t4_admin},
					update_modified=False,
				)
				if not doc.t4_admin:
					frappe.log_error(
						title="Employee Resignation v2 migration: no T4 Admin resolved (Date Adjustment)",
						message=f"{row.name} moved to Pending T4 Admin but no user holds that role.",
					)
			else:
				frappe.db.set_value(
					"Employee Resignation Date Adjustment", row.name,
					{"workflow_state": "Pending Project Manager", "project_manager": doc.project_manager},
					update_modified=False,
				)
				if doc.project_manager:
					from frappe.desk.form.assign_to import add as assign_to_add
					assign_to_add({
						"doctype": "Employee Resignation Date Adjustment",
						"name": row.name,
						"assign_to": [doc.project_manager],
						"description": "Please review and approve this Resignation Date Adjustment.",
					})
				else:
					frappe.log_error(
						title="Employee Resignation v2 migration: no Project Manager resolved (Date Adjustment)",
						message=f"{row.name} moved to Pending Project Manager but no Project Manager could be resolved.",
					)
		except Exception:
			frappe.log_error(
				title="Employee Resignation v2 migration: Date Adjustment reroute failed",
				message=f"{row.name}: {frappe.get_traceback()}",
			)


def close_orphaned_assignment_rule_todos():
	rows = frappe.db.sql(
		"""
		select td.name as todo_name, td.assignment_rule, er.workflow_state
		from `tabToDo` td
		inner join `tabEmployee Resignation` er on er.name = td.reference_name
		where td.reference_type = 'Employee Resignation'
		and td.status = 'Open'
		and td.assignment_rule in %s
		""",
		(list(ASSIGNMENT_RULE_STAGE.keys()),),
		as_dict=True,
	)

	for row in rows:
		stale_stage = ASSIGNMENT_RULE_STAGE.get(row.assignment_rule)
		if row.workflow_state != stale_stage:
			frappe.db.set_value("ToDo", row.todo_name, "status", "Cancelled", update_modified=False)


def backfill_current_salary():
	frappe.db.sql(
		"""
		update `tabEmployee Resignation` er
		inner join `tabEmployee` e on e.name = er.employee
		set er.current_salary = e.one_fm_basic_salary
		"""
	)
