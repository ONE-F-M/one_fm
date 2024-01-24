import frappe

def execute():
    # update the attendance_by_timesheet value in Attendance Check
    frappe.db.sql(f"""  UPDATE
                    `tabAttendance Check` ac,
                    `tabEmployee` e
                SET
                    ac.attendance_by_timesheet = 1 
                WHERE
                    ac.employee = e.name AND e.attendance_by_timesheet = 1;""") 


   