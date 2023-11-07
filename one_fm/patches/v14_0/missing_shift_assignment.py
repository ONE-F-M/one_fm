import frappe

def execute():
    attendance_check = frappe.db.sql("""SELECT name, shift_assignment from `tabAttendance Check` where workflow_state='Pending Approval'""", as_dict=True)
    for att in attendance_check:
        if not frappe.db.exists("Shift Assignment", {'name':att.shift_assignment}):
            doc = frappe.get_doc("Attendance Check",att.name)
            doc.db_set("shift_assignment", "")
            doc.db_set("has_shift_assignment" ,0)
    frappe.db.commit()
