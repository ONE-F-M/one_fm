from frappe.model.utils.rename_field import rename_field


def execute():
	"""Carry each export's last run date into the new last_execution_timestamp field."""
	rename_field("Google Sheet Data Export", "last_execution_date", "last_execution_timestamp")
