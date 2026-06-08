"""Fix parentfield mismatch in Bonus Request Items child table rows.

The DocType JSON defines the field as 'bonus_request_employees' but existing
child rows were inserted with parentfield='items'. This updates them to match.
"""
import frappe


def execute():
	count = frappe.db.count(
		"Bonus Request Items",
		{"parentfield": "items"}
	)

	if count == 0:
		print("No rows with parentfield='items' found. Nothing to fix.")
		return

	frappe.db.set_value(
		"Bonus Request Items",
		{"parentfield": "items"},
		"parentfield",
		"bonus_request_employees",
		update_modified=False
	)
	frappe.db.commit()
	print(f"Updated {count} rows: parentfield 'items' -> 'bonus_request_employees'")
