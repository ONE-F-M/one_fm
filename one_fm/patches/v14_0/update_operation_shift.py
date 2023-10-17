import frappe

def execute():
    att = frappe.db.sql("""SELECT * FROM `tabAttendance` WHERE operations_shift='None' AND status IN ('Present','Absent', 'On Leave')""", as_dict=1)
    for a in att:
        _a = frappe.get_doc("Attendance", a.name)
        if a.shift_assignment:
            sa = frappe.get_value("Shift Assignment", a.shift_assignment, ['shift'])
            _a.db_set('operations_shift', sa)
    frappe.db.commit()