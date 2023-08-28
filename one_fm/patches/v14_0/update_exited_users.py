import frappe

def execute():
    return
    # Update the user accounts of exited employees
    update_query = """
                UPDATE `tabUser`
                SET enabled = '0'
                WHERE name IN (
                    SELECT emp.user_id
                    FROM `tabEmployee` emp
                    WHERE emp.status IN ('Left', 'Course Case', 'Absconding')
                        AND emp.user_id IN (
                            SELECT usr.name
                            FROM `tabUser` usr
                            WHERE usr.enabled = '1'
                        )
                )
                """
    frappe.db.sql(update_query)
    frappe.db.commit()