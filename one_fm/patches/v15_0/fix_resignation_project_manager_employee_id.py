import frappe

# set_project_manager() used to assign Project's own "Project Manager" field
# (a Link to Employee) straight into these doctypes' project_manager field
# (a Link to User) without resolving it -- any record saved before that was
# fixed has an Employee ID sitting in a User-linked field, which then fails
# link validation ("Could not find Project Manager: HR-EMP-XXXXX") the next
# time the record is opened or saved.
DOCTYPES = [
	"Employee Resignation",
	"Employee Resignation Withdrawal",
	"Employee Resignation Date Adjustment",
]


def execute():
	for doctype in DOCTYPES:
		repair(doctype)


def repair(doctype):
	rows = frappe.db.sql(
		f"""
		select t.name, t.project_manager
		from `tab{doctype}` t
		left join `tabUser` u on u.name = t.project_manager
		where t.project_manager is not null and t.project_manager != '' and u.name is null
		""",
		as_dict=True,
	)

	for row in rows:
		user_id = frappe.db.get_value("Employee", row.project_manager, "user_id")
		if user_id and frappe.db.exists("User", user_id):
			frappe.db.set_value(doctype, row.name, "project_manager", user_id, update_modified=False)
		else:
			frappe.db.set_value(doctype, row.name, "project_manager", None, update_modified=False)
			frappe.log_error(
				title="Employee Resignation v2: could not repair project_manager",
				message=f"{doctype} {row.name} had project_manager={row.project_manager}, which isn't a valid Employee with a User account. Cleared -- please re-set manually.",
			)
