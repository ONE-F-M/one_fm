import frappe

def execute():
    d = frappe.db.sql("""SELECT * FROM `tabAttendance`
                        WHERE name NOT IN (SELECT name, COUNT(attendance_date) AS CNT
                    FROM `tabAttendance` WHERE attendance_date = '2024-01-22'
                    GROUP BY employee, 
                        attendance_date, 
                        roster_type
                    HAVING COUNT(attendance_date) > 1);
                    """)
    print(d)