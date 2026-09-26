import frappe

# Columns left behind by Custom Fields that were removed. Frappe deletes the Custom Field
# row and leaves the column, so the space it takes on the row stays taken. Named one by
# one rather than discovered: a column is dropped for good, and the list is short.
COLUMNS = ("one_fm_work_permit", "pam_authorized_signatory", "pam_visa")


def execute():
	"""WI-002745: free room on tabEmployee for the Occupational Sector column.

	tabEmployee carries 115 varchar(140) columns and sits at 65,182 of InnoDB's 65,535
	byte row limit, so the next one fails outright:

	    (1118, 'Row size too large. The maximum row size for the used table type, not
	     counting BLOBs, is 65535.')

	Each column here is checked three ways before it goes - no field claims it, it exists,
	and every row is empty - so a column that has come back into use, or that turns out to
	hold data after all, is left alone and the migrate still passes.
	"""
	claimed = {df.fieldname for df in frappe.get_meta("Employee").fields}
	claimed |= set(frappe.model.default_fields) | set(frappe.model.optional_fields)

	for column in COLUMNS:
		if column in claimed:
			continue
		if not frappe.db.has_column("Employee", column):
			continue
		if frappe.db.sql(
			f"SELECT 1 FROM `tabEmployee` WHERE `{column}` IS NOT NULL AND `{column}` != '' LIMIT 1"
		):
			continue

		frappe.db.sql_ddl(f"ALTER TABLE `tabEmployee` DROP COLUMN `{column}`")
