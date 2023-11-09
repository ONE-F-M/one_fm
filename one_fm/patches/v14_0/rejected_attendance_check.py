import frappe

def execute():
    att_check = frappe.db.sql("""SELECT name, attendance, attendance_status from `tabAttendance Check` 
                                WHERE workflow_state='Rejected'""", as_dict=True)
    for att in att_check:
        if att.attendance and frappe.db.exists("Attendance", {'name':att.attendance}):
            attendance_doc = frappe.get_doc("Attendance", att.attendance)
            attendance_doc.db_set("status", att.attendance_status)
    frappe.db.commit()
            