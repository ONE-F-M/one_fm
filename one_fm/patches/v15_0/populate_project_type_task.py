import frappe


def execute():
    try:
        qs = frappe.db.sql("""
            SELECT 
                t.name AS task_name, 
                p.project_type AS project_type
            FROM 
                `tabTask` AS t
            JOIN 
                `tabProject` AS p
            ON 
                t.project = p.name
            WHERE 
                t.project IS NOT NULL
        """, as_dict=True)
        if qs:
            for obj in qs:
                frappe.db.set_value('Task', obj.get("task_name"), 'custom_project_type', obj.get("project_type"))
    except Exception as e:
        print(str(e))