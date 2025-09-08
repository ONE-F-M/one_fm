import frappe

def execute():
	for doc in frappe.get_all("Head Hunt", fields=["name", "docstatus"]):
		if doc.get("docstatus") == 1:
			continue  # Skip submitted docs
		head_hunt = frappe.get_doc("Head Hunt", doc.name)
		# Collect all non-empty suggested_position values from child table
		positions = list({item.sugested_position for item in head_hunt.items if item.sugested_position})
		if len(positions) == 1:
			if head_hunt.suggested_position != positions[0]:
				head_hunt.suggested_position = positions[0]
				head_hunt.save(ignore_permissions=True)
		else:
			if head_hunt.suggested_position:
				head_hunt.suggested_position = ""
				head_hunt.save(ignore_permissions=True)
