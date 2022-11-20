import frappe


def execute():
    frappe.db.sql("""DELETE from `tabCustom Field` WHERE name='Employee-pam_visa';""")
    frappe.db.sql("""DELETE from `tabCustom Field` WHERE name='Employee-pam_authorized_signatory';""")
    frappe.db.sql("""ALTER TABLE `tabEmployee` DROP COLUMN pam_visa;""")
    frappe.db.sql("""ALTER TABLE `tabEMployee` DROP COLUMN pam_authorized_signatory;""")
    frappe.db.sql("""ALTER TABLE `tabPAM FIle` DROP COLUMN contract_file_number;""")
    frappe.db.sql("""ALTER TABLE `tabPAM FIle` DROP COLUMN company_unified_nuumber;""")
    frappe.db.sql("""ALTER TABLE `tabPAM FIle` DROP COLUMN contract_pam_file_number;""")
    frappe.db.sql("""ALTER TABLE `tabPAM FIle` DROP COLUMN main_pam_file;""")
    frappe.db.sql("""ALTER TABLE `tabPAM FIle` DROP COLUMN pam_file_governorate_arabic;""")