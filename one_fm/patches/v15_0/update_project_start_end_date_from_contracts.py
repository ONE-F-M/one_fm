import frappe


def execute():
    projects_with_contracts = frappe.db.sql("""
        SELECT 
            p.name AS project_name,
            c.start_date,
            c.end_date
        FROM 
            `tabProject` p
        LEFT JOIN 
            `tabContracts` c ON c.project = p.name
        WHERE 
            p.project_type = 'External'
            AND (p.expected_start_date IS NULL OR p.expected_end_date IS NULL)
            AND c.workflow_state = 'Active'
    """, as_dict=1)


    for record in projects_with_contracts:
        if record.start_date and record.end_date:
            frappe.db.sql("""
                UPDATE `tabProject`
                SET expected_start_date = %s, expected_end_date = %s
                WHERE name = %s
            """, (record.start_date, record.end_date, record.project_name))

    frappe.db.commit()
