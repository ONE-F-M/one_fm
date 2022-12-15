import frappe

@frappe.whitelist()
def get_opening_values():
    """
        Get the opening values the roster page
    """
    projects = frappe.db.sql("SELECT name from `tabProject` where status = 'Open' ",as_dict=1)
    shifts = frappe.db.sql("SELECT name from `tabOperations Shift` ",as_dict=1)
    sites = frappe.db.sql("SELECT name from `tabOperations Site` ",as_dict=1)
    employees = frappe.db.sql("SELECT name from `tabEmployee` where status = 'Active' ",as_dict=1)
    return {'project':projects,'shifts':shifts,'sites':sites,'employees':employees}

@frappe.whitelist()
def get_project_details(project):
    """
        Fetch the shift,site and employees associated with a project
    """
    shifts = frappe.db.sql(f"SELECT name from `tabOperations Shift` where project = '{project}' ",as_dict=1)
    sites = frappe.db.sql(f"SELECT name from `tabOperations Site` where project = '{project}' ",as_dict=1)
    employees = frappe.db.sql(f"SELECT name from `tabEmployee` where status = 'Active' and project = '{project}' ",as_dict=1)
    return {'shifts':shifts,'sites':sites,'employees':employees}

