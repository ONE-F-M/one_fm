#update_docstatus
import frappe

def execute():
    att_check = frappe.db.sql("""SELECT name from `tabAttendance Check` 
                                WHERE workflow_state IN ("Approved","Rejected")
                                AND docstatus!=1""", as_dict=True)
    print(att_check)
    for att in att_check:
        att = frappe.get_doc("Attendance Check", att.name)
        att.db_set("docstatus", 1)
    frappe.db.commit()
