import frappe

def run():
    emails = frappe.get_all("Email Queue", fields=["name", "status", "message_id", "creation"], limit=5, order_by="creation desc")
    print("Recent Emails:")
    for e in emails:
        print(e)
