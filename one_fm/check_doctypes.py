import frappe

def check_doctypes():
    docs = frappe.get_all("DocType", filters={"module": "one_fm"}, fields=["name"])
    print([d.name for d in docs])

def run():
    check_doctypes()
