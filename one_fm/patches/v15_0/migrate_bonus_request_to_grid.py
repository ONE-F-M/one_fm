# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


# Mapping of old checkbox fields to the new justification dropdown values.
# Priority order: if multiple checkboxes were checked, use the first match.
CRITERIA_TO_JUSTIFICATION = [
	("star_performer", "Special Recognition"),
	("significant_effort", "Excellent Performance"),
	("increased_productivity", "Excellent Performance"),
	("improved_work_processes", "Excellent Performance"),
]


def execute():
	"""Migrate existing single-employee Bonus Request records to the new
	multi-employee child table model.

	Steps:
	1. Flip the custom:1 flag on 'Bonus Request Items' to custom:0 so the
	   app-managed version takes over on the next bench migrate.
	2. For each existing Bonus Request that has an 'employee' field value,
	   create a child table row with the employee data.
	3. Set requested_by from the document owner's employee record.
	4. Calculate and set total_bonus_amount.
	"""
	# Step 1: Remove custom flag so app-managed version takes precedence
	if frappe.db.exists("DocType", "Bonus Request Items"):
		frappe.db.set_value("DocType", "Bonus Request Items", "custom", 0)

	# Step 2: Check if the old 'employee' column still exists on Bonus Request
	if not frappe.db.has_column("Bonus Request", "employee"):
		# Already migrated or fresh install — nothing to do
		return

	# Check if the child table exists in the database
	if not frappe.db.table_exists("tabBonus Request Items"):
		# The table will be created by bench migrate; skip migration for now
		frappe.log_error(
			title="Bonus Request Migration",
			message="tabBonus Request Items table does not exist yet. "
			"Run bench migrate first, then re-run this patch."
		)
		return

	# Fetch all existing Bonus Requests that have an employee set
	bonus_requests = frappe.db.get_all(
		"Bonus Request",
		filters={"employee": ["is", "set"]},
		fields=[
			"name", "employee", "bonus_amount", "owner",
			"increased_productivity", "improved_work_processes",
			"significant_effort", "star_performer", "others", "justification"
		],
		limit_page_length=0
	)

	if not bonus_requests:
		return

	count = 0
	for br in bonus_requests:
		try:
			# Skip if this Bonus Request already has child table rows
			existing_items = frappe.db.count(
				"Bonus Request Items",
				{"parent": br.name}
			)
			if existing_items > 0:
				continue

			# Determine justification from old checkbox fields
			justification = ""
			description = ""

			if br.others:
				justification = "Other"
				description = br.justification or ""
			else:
				for field_name, justification_value in CRITERIA_TO_JUSTIFICATION:
					if br.get(field_name):
						justification = justification_value
						break

			if not justification:
				justification = "Excellent Performance"  # Default fallback

			# Create child table row
			child = frappe.get_doc({
				"doctype": "Bonus Request Items",
				"parent": br.name,
				"parentfield": "items",
				"parenttype": "Bonus Request",
				"idx": 1,
				"employee": br.employee,
				"bonus_amount": flt(br.bonus_amount),
				"justification": justification,
				"description": description,
			})
			child.db_insert()

			# Set requested_by from the document owner's employee record
			# Try active first, fall back to any status for historical records
			requester = frappe.db.get_value(
				"Employee",
				{"user_id": br.owner, "status": "Active"},
				"name"
			)
			if not requester:
				requester = frappe.db.get_value(
					"Employee",
					{"user_id": br.owner},
					"name"
				)

			update_values = {
				"total_bonus_amount": flt(br.bonus_amount),
			}
			if requester:
				update_values["requested_by"] = requester

			frappe.db.set_value("Bonus Request", br.name, update_values, update_modified=False)

			count += 1

			# Commit every 100 records to avoid long transactions
			if count % 100 == 0:
				frappe.db.commit()

		except Exception:
			frappe.log_error(
				title="Bonus Request Migration - Failed for {0}".format(br.name),
				message=frappe.get_traceback()
			)

	frappe.db.commit()
	frappe.msgprint(
		"Bonus Request migration completed: {0} record(s) migrated.".format(count)
	)
