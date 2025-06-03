import frappe

def execute():
	add_employee_schedule_index()
	add_employee_index()
	add_attendance_index()
	add_post_schedule_index()
	add_operations_post_index()


def add_employee_schedule_index():
	frappe.db.add_index("Employee Schedule", ["employee", "date", "roster_type", "operations_role"], "employee_schedule_date")
	frappe.db.add_index("Employee Schedule", ["employee"], "employee")
	frappe.db.add_index("Employee Schedule", ["date"], "date")
	frappe.db.add_index("Employee Schedule", ["employee", "date"], "employee_date")
	frappe.db.add_index("Employee Schedule", ["date", "operations_role"], "date_operations_role")
	frappe.db.add_index("Employee Schedule", ["project", "site", "shift", "operations_role", "department"], "roster")


def add_employee_index():
	frappe.db.add_index("Employee", ["employee_name"], "employee_name")



def add_attendance_index():
	frappe.db.add_index("Attendance", ["attendance_date", "employee", "operations_shift"], "attendance_date_employee_shift")
	frappe.db.add_index("Attendance", ["employee", "attendance_date", "docstatus"], "employee_date_docstatus")
	frappe.db.add_index("Attendance", ["operations_shift"], "operations_shift")


def add_post_schedule_index():
	frappe.db.add_index("Post Schedule", ["date", "post_status"], "post_status_date")
	frappe.db.add_index("Post Schedule", ["project", "site", "shift", "operations_role", "date"], "post_map")
	frappe.db.add_index("Post Schedule", ["operations_role", "dat"], "role_date")


def add_operations_post_index():
	frappe.db.add_index("Operations Post", ["project", "site"], "operations_post_project_site")