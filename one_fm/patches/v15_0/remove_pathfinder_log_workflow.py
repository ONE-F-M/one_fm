import frappe


# Mapping from old workflow_state values to new status values.
WORKFLOW_STATE_TO_STATUS = {
	"Draft": "Backlog",
	"Pending Process Classification": "Backlog",
	"Pending Process Definition": "Backlog",
	"Pending Review": "Backlog",
	"Pending Story Definition": "Backlog",
	"In Development": "Active",
	"In Staging": "Active",
	"In Production": "Active",
	"Completed": "Deployed",
}


def execute():
	"""Remove the Pathfinder Log workflow and migrate workflow_state → status."""

	# 1. Migrate existing workflow_state values to the new status field.
	if frappe.db.has_column("Pathfinder Log", "workflow_state"):
		for old_state, new_status in WORKFLOW_STATE_TO_STATUS.items():
			frappe.db.sql(
				"""
				UPDATE `tabPathfinder Log`
				SET `status` = %s
				WHERE `workflow_state` = %s
				  AND (`status` IS NULL OR `status` = '' OR `status` = 'Backlog')
				""",
				(new_status, old_state),
			)

	# 2. Migrate legacy state labels in the Time Log child table so
	#    existing rows display the new status names.
	for old_state, new_status in WORKFLOW_STATE_TO_STATUS.items():
		frappe.db.sql(
			"""
			UPDATE `tabPathfinder Log Time`
			SET `state` = %s
			WHERE `state` = %s
			""",
			(new_status, old_state),
		)

	# 3. Ensure no records have a blank status (safety net).
	frappe.db.sql(
		"""
		UPDATE `tabPathfinder Log`
		SET `status` = 'Backlog'
		WHERE `status` IS NULL OR `status` = ''
		"""
	)

	# 4. Delete the Workflow document.
	if frappe.db.exists("Workflow", "Pathfinder Log"):
		frappe.delete_doc("Workflow", "Pathfinder Log", ignore_permissions=True)

	frappe.db.commit()
