import frappe

def execute():
    '''
        Remove property setter for non-existing DocType "HD SLA" and 
        "HD Pause SLA" which were used previously to set the default value for the link field 
        to "HD Service Level Agreement Fulfilled On Status" 
        and "HD Pause Service Level Agreement On Status" respectively.
        Also, remove the property setter for "options" of "status" field in "HD Ticket" doctype 
        which was set to "Open, Closed, Replied, On Hold, Pending Deployment" as we are now 
        fetching the options dynamically from the "HD Ticket Status" doctype.
        Also, add default values for the new "HD Ticket Status" doctype.
    '''
    frappe.db.sql(
        """
            DELETE FROM 
                `tabProperty Setter` 
            WHERE
                doc_type IN (
                    'HD Service Level Agreement Fulfilled On Status',
                    'HD Pause Service Level Agreement On Status'
                )    
        """)

    frappe.db.sql(
        """
            DELETE FROM 
                `tabProperty Setter` 
            WHERE
                name = 'HD Ticket-status-options'
        """)
    
    statuses = [
        {
            "label_agent": "Draft",
            "color": "Gray",
            "enabled": 1,
            "category": "Paused",
            "order": 1,
        },
        {
            "label_agent": "On Hold",
            "color": "Orange",
            "enabled": 1,
            "category": "Paused",
            "different_view": 1,
            "label_customer": "On Hold",
            "order": 2,
        },
        {
            "label_agent": "Pending Deployment",
            "color": "Orange",
            "enabled": 1,
            "category": "Paused",
            "order": 3,
        }
    ]
    for status in statuses:
        if not frappe.db.exists("HD Ticket Status", status["label_agent"]):
            frappe.get_doc({"doctype": "HD Ticket Status", **status}).insert()
