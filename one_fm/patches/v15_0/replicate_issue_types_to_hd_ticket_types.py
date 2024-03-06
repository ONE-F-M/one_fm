import frappe

def execute():
    frappe.db.sql("TRUNCATE TABLE `tabHD Ticket Type`")

    issue_types = frappe.get_all("Issue Type", fields=['name', 'description'])

    for issue_type in issue_types:
        hd_ticket_type = frappe.new_doc("HD Ticket Type")
        hd_ticket_type.name = issue_type.name
        hd_ticket_type.description = issue_type.description
        hd_ticket_type.insert()

    frappe.db.commit()