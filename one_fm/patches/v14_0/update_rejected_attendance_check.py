import frappe

def execute():
    att_check = frappe.db.sql("""UPDATE
                            `tabAttendance Check` a
                        SET
                            a.workflow_state = "Approved"
                        WHERE
                            a.workflow_state = "Rejected"
                        """)
            