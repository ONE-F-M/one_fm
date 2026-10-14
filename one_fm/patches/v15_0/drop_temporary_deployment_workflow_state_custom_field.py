import frappe


def execute():
	# workflow_state is now a standard field on Temporary Deployment. A Custom Field of the
	# same name would be appended to the meta a second time, so remove it before the doctype
	# syncs. Deleting a Custom Field keeps its column, so stored states survive.
	frappe.delete_doc("Custom Field", "Temporary Deployment-workflow_state", ignore_missing=True, force=True)
