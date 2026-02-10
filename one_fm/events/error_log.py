import frappe, json


@frappe.whitelist()
def create_issue_log(error_log):
    error_log = frappe._dict(json.loads(error_log))

    issue_log = frappe.get_doc({
        'doctype':'HD Ticket',
        'reference_doctype':error_log.doctype,
        'reference_name':error_log.name,
        'subject':error_log.method,
        'status':'Open',
        'description':error_log.error,
        'priority': 'High',
        'ticket_type': 'Bug',
    }).insert(ignore_permissions=True)
    issue_log.add_comment("Comment", error_log.error)
    frappe.db.set_value("Error Log", error_log.name, 'hd_ticket', issue_log.name)
    return issue_log.name


def run_error_log_agent_from_task(doc: dict):
    """
    Background task to automatically create HD Ticket from Error Log.
    Called from background job when Error Log is created.
    
    IMPORTANT: This method should be enqueued with the FULL module path:
        frappe.enqueue(
            method="one_fm.events.error_log.run_error_log_agent_from_task",
            doc=error_log_dict
        )
    
    If enqueued with just "run_error_log_agent_from_task" (without module path),
    Frappe will fail with: "App run_error_log_agent_from_task is not installed"
    
    Args:
        doc: Error Log document dict containing error details
            Required fields: name, doctype, method, error
            Optional fields: hd_ticket (to check for existing ticket)
    
    Returns:
        str: Name of created HD Ticket, or None if ticket already exists or creation fails
    """
    try:
        # Convert dict to frappe._dict if needed
        if isinstance(doc, dict):
            error_log = frappe._dict(doc)
        else:
            error_log = doc
        
        # Check if HD Ticket already exists for this Error Log
        if error_log.get("hd_ticket"):
            frappe.logger().info(f"HD Ticket already exists for Error Log {error_log.get('name')}")
            return
        
        # Check if Error Log document exists in database
        if not frappe.db.exists("Error Log", error_log.get("name")):
            frappe.logger().warning(f"Error Log {error_log.get('name')} not found in database")
            return
        
        # Create HD Ticket from Error Log
        issue_log = frappe.get_doc({
            "doctype": "HD Ticket",
            "reference_doctype": error_log.get("doctype", "Error Log"),
            "reference_name": error_log.get("name"),
            "subject": error_log.get("method", "Error Log"),
            "status": "Open",
            "description": error_log.get("error", ""),
            "priority": "High",
            "ticket_type": "Bug",
        }).insert(ignore_permissions=True)
        
        # Add error details as comment
        if error_log.get("error"):
            issue_log.add_comment("Comment", error_log.get("error"))
        
        # Update Error Log with HD Ticket reference
        frappe.db.set_value("Error Log", error_log.get("name"), "hd_ticket", issue_log.name)
        frappe.db.commit()
        
        frappe.logger().info(f"HD Ticket {issue_log.name} created from Error Log {error_log.get('name')}")
        return issue_log.name
        
    except Exception as e:
        frappe.log_error(
            title="Error in run_error_log_agent_from_task",
            message=frappe.get_traceback()
        )
        # Don't raise exception to prevent job from failing repeatedly
        frappe.logger().error(f"Failed to create HD Ticket from Error Log: {str(e)}")