import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow

REQUIRED_ROLES = ["Project Manager", "Security Manager", "Cleaning Head Supervisor", "Line Manager"]


def execute():
	"""Roll out the redesigned Employee Resignation / Employee Resignation Withdrawal
	workflows (per-branch negotiation, T4 department routing, Project Manager as the
	sole Shift-path approver).

	Does NOT auto-create the new Roles required by the new workflow states --
	confirmed against the live site that Project Manager, Security Manager,
	Cleaning Head Supervisor, and Line Manager don't exist yet. Creating a Role is
	an access-control decision, not something a migration patch should decide on its
	own, so this only warns loudly if they're still missing when it runs. Until
	they're created (and someone is actually assigned each role), the "Pending T4
	Admin -> Forward" transitions into Cleaning Head Supervisor / Security Manager /
	Project Manager states will have no one able to act on them.
	"""
	warn_about_missing_roles()
	backfill_shift_category_and_t4_route()
	create_workflow(get_workflow_json_file("employee_resignation.json"))
	create_workflow(get_workflow_json_file("employee_resignation_withdrawal.json"))


def warn_about_missing_roles():
	missing = [role for role in REQUIRED_ROLES if not frappe.db.exists("Role", role)]
	if not missing:
		return

	message = (
		"Employee Resignation v2 workflow installed, but these Roles do not exist yet "
		"and must be created (and assigned to the right people) before their workflow "
		"stages are usable: " + ", ".join(missing)
	)
	print(f"\n*** WARNING: {message} ***\n")
	frappe.log_error(title="Employee Resignation v2: missing Roles", message=message)


def backfill_shift_category_and_t4_route():
	"""shift_category and t4_route are both derived fields (from department and
	designation respectively), and both source fields have always been auto-fetched
	onto Employee Resignation -- so every existing record already has what's needed
	to compute them. No re-collection required."""
	rows = frappe.db.sql(
		"""
		select name, shift_working, department, designation
		from `tabEmployee Resignation`
		where shift_category is null or shift_category = ''
		""",
		as_dict=True,
	)

	for row in rows:
		if not row.shift_working:
			continue

		shift_category = "T4" if row.department and "t4" in row.department.lower() else "Operations"

		update_data = {"shift_category": shift_category}
		if shift_category == "T4":
			designation = (row.designation or "").lower()
			if "security" in designation:
				update_data["t4_route"] = "Security"
			elif "janitor" in designation:
				update_data["t4_route"] = "Janitorial"
			else:
				update_data["t4_route"] = "Passenger-Customer Service"

		frappe.db.set_value("Employee Resignation", row.name, update_data, update_modified=False)
