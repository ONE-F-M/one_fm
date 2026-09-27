import frappe


def execute():
	"""Drop the now-unused `approver` column on Document Request.

	WI-002949: approver_user is filled directly from get_approver_user, so the
	`approver` (Employee) field it used to be fetched through is no longer part
	of the doctype. The field definition is already removed from the JSON; this
	only cleans up the database column left behind on sites that had it.
	"""
	column = "approver"
	if column in frappe.db.get_table_columns("Document Request"):
		frappe.db.sql("ALTER TABLE `tabDocument Request` DROP COLUMN `{0}`".format(column))
		frappe.db.commit()
