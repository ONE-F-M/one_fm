import frappe


def execute():
	"""shift_category was originally derived from Department, but Department is
	a generic "Operations - ONEFM" bucket shared by every shift-working
	employee whether they're T4 or not -- it never actually contains "t4",
	so no record could ever be classified as T4. Project Allocation (e.g.
	"T4 Airport") is what actually distinguishes them. Re-derives
	shift_category (and t4_route where relevant) for any existing record
	that was misclassified as a result.
	"""
	rows = frappe.db.sql(
		"""
		select name, project_allocation, designation
		from `tabEmployee Resignation`
		where shift_working = 1
		and shift_category != 'T4'
		and project_allocation like '%t4%'
		""",
		as_dict=True,
	)

	for row in rows:
		designation = (row.designation or "").lower()
		if "security" in designation:
			t4_route = "Security"
		elif "janitor" in designation:
			t4_route = "Janitorial"
		else:
			t4_route = "Passenger-Customer Service"

		frappe.db.set_value(
			"Employee Resignation", row.name,
			{"shift_category": "T4", "t4_route": t4_route},
			update_modified=False,
		)
