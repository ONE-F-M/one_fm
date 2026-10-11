import frappe
from frappe.permissions import add_permission, update_permission_property

# The Temporary Deployment Lifecycle process map drives every state change, assigns the
# review tasks and creates the Temporary Posts. An active Workflow adds Actions that move
# the record without the process instance, and the two rules would assign twice.
ASSIGNMENT_RULES = (
	"Assigning Operations Manager for Approval- Temporary Deployment",
	"Returning to Operations Supervisor of Temporary Deployment",
)


def execute():
	if frappe.db.exists("Workflow", "Temporary Deployment"):
		frappe.db.set_value("Workflow", "Temporary Deployment", "is_active", 0)
		frappe.cache.hdel("workflow", "Temporary Deployment")

	for name in ASSIGNMENT_RULES:
		if frappe.db.exists("Assignment Rule", name):
			frappe.db.set_value("Assignment Rule", name, "disabled", 1)

	# Process scripts run as the user who started the instance (the Supervisor who created the
	# deployment); the Manager completes the review tasks. Either may create Temporary Posts.
	for role in ("Operations Supervisor", "Operations Manager"):
		add_permission("Temporary Post", role, 0)
		update_permission_property("Temporary Post", role, 0, "create", 1, validate=False)

	frappe.clear_cache(doctype="Temporary Post")
	frappe.clear_cache(doctype="Temporary Deployment")
