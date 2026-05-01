# 2026-04-27
import frappe

def execute():
	"""Fix the name column type for DMARC Report.

	The column was created as bigint when autoname was 'autoincrement'.
	Now that naming is Python-based, it must be varchar(140).
	"""
	result = frappe.db.sql(
		"SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
		"WHERE TABLE_NAME = 'tabDMARC Report' AND COLUMN_NAME = 'name' "
		"AND TABLE_SCHEMA = DATABASE()",
		as_dict=True
	)

	if result and result[0].get("DATA_TYPE") == "bigint":
		frappe.db.sql_ddl("ALTER TABLE `tabDMARC Report` MODIFY `name` varchar(140) NOT NULL")
		frappe.db.commit()
