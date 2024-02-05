import frappe
import datetime
from frappe.utils import getdate

def execute() :
    delete_list = []
    date = getdate('2023-12-20')

    dup_attendance = frappe.db.sql(f"""SELECT name, employee, attendance_date, roster_type, COUNT(*) as count
                        FROM `tabAttendance` WHERE attendance_date >= {date}
                        GROUP BY employee, attendance_date, roster_type
                        HAVING COUNT(*)> 1""", as_dict=1)
    for att in dup_attendance:
        atts = frappe.db.sql(f"""SELECT name, creation, status
                        FROM `tabAttendance`
                        WHERE employee='{att.employee}'
                        AND attendance_date='{att.attendance_date}'
                        AND roster_type= '{att.roster_type}'
                        ORDER BY creation desc""", as_dict=1)
        if att.count== 2:
            if atts[0].status == "Absent":
                delete_list.append (atts[0].name)
            elif atts[1].status =="Absent":
                delete_list.append(atts[1].name)
            else:
                delete_list.append (atts[0].name)
        elif att.count == 3:
            if atts[0].status == "Present":
                delete_list.append (atts[1].name)
                delete_list.append(atts[2].name)
            elif atts[1].status == "Present":
                delete_list.append (atts[0].name)
                delete_list.append (atts[2].name)
            else:
                delete_list.append(atts[0].name)
                delete_list.append (atts[1].name)

    delete_list = tuple(delete_list)
    frappe.db.sql(f"""DELETE FROM `tabAttendance Check` where attendance IN {delete_list}""")
    frappe.db.sql(f"""DELETE FROM `tabAttendance` where name IN {delete_list}""")
