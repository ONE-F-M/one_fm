import frappe

def execute():
    """
    Remove the 'doc.' prefix from assignment rule conditions for Employee Resignation.
    Assignment rule conditions are evaluated in safe_eval which does not have 'doc' in context.
    """
    frappe.db.sql("""
        UPDATE `tabAssignment Rule` 
        SET assign_condition = REPLACE(assign_condition, 'doc.workflow_state', 'workflow_state'), 
            unassign_condition = REPLACE(unassign_condition, 'doc.workflow_state', 'workflow_state') 
        WHERE document_type = 'Employee Resignation' 
        AND (assign_condition LIKE '%doc.workflow_state%' OR unassign_condition LIKE '%doc.workflow_state%')
    """)
    frappe.db.commit()
