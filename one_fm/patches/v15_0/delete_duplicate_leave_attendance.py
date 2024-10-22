import frappe
import datetime
from frappe.utils import getdate

def execute() :
    delete_list = []
    date = getdate('2023-12-20')

    dup_attendance = frappe.db.sql(f"""SELECT name, employee, attendance_date, roster_type, COUNT(*) as count
                        FROM `tabAttendance` WHERE status = "On Leave"
                        GROUP BY employee, attendance_date, roster_type
                        HAVING COUNT(*)> 1""", as_dict=1)
    for att in dup_attendance:
        atts = frappe.db.sql(f"""SELECT name, creation, status, owner
                        FROM `tabAttendance`
                        WHERE employee='{att.employee}'
                        AND attendance_date='{att.attendance_date}'
                        AND roster_type= '{att.roster_type}'
                        ORDER BY creation desc""", as_dict=1)
        if att.count== 2:
            if atts[0].owner == "Administrator":
                delete_list.append (atts[0].name)
            else:
                delete_list.append (atts[1].name)

    delete_list = str(tuple(delete_list)).replace(',)', ')')
    frappe.db.sql(f"""DELETE FROM `tabAttendance` where name IN {delete_list}""")
