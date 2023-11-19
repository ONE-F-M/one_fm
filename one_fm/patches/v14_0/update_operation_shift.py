import frappe

def execute():
    att = frappe.db.sql("""UPDATE
                            `tabAttendance` a,
                            `tabShift Assignment` sa
                        SET
                            a.operations_shift = sa.shift
                        WHERE
                            a.shift_assignment = sa.name
                            AND a.operations_shift='None'
                        """)