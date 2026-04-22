import frappe

def test():
    try:
        doc = frappe.get_doc("DocType", "Employee Resignation Withdrawal Item")
        doc.custom = 0
        doc.module = "One Fm"
        doc.save(ignore_permissions=True)
        print("Successfully exported Employee Resignation Withdrawal Item!")
    except Exception as e:
        print(f"Error: {e}")
