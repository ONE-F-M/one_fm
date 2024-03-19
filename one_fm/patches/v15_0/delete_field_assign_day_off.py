import frappe

def execute():
    column = 'assign_day_off'
    if column in frappe.db.get_table_columns("Shift Request"):
        frappe.db.sql("ALTER TABLE `tabShift Request` drop column {0}".format(column))
        frappe.db.commit()