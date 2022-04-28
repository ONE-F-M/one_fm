from __future__ import unicode_literals
import frappe

def execute():
    print('Preparing Payroll Employee Detail')
    frappe.reload_doctype('Payroll Employee Detail')
    print('Removing index key iban_number_2 from iban_number....')
    frappe.db.sql("""ALTER TABLE `tabPayroll Employee Detail` DROP INDEX iban_number_2;""")
    print('Done')
