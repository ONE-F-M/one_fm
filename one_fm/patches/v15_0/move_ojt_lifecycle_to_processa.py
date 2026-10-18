import frappe
from frappe.permissions import add_permission, update_permission_property

# The On the Job Training Lifecycle process map now drives every state change, assigns the
# review tasks and maintains the trainee's Employee Schedules. An active Workflow adds Actions
# that move the record without the process instance, and the two rules would assign twice.
ASSIGNMENT_RULES = (
	"Assigning Project Manager for Approval",
	"Returning to Operations Supervisor of OJT Request",
)

# Map scripts run as the Supervisor or Project Manager who clicked the task.
PERMISSIONS = {
	"Employee Schedule": ("read", "write", "create", "delete"),
	"Shift Assignment": ("read", "cancel", "delete"),
}
ROLES = ("Operations Supervisor", "Project Manager")


def execute():
	if frappe.db.exists("Workflow", "On the Job Training"):
		frappe.db.set_value("Workflow", "On the Job Training", "is_active", 0)
		frappe.cache.hdel("workflow", "On the Job Training")

	for name in ASSIGNMENT_RULES:
		if frappe.db.exists("Assignment Rule", name):
			frappe.db.set_value("Assignment Rule", name, "disabled", 1)

	for doctype, rights in PERMISSIONS.items():
		for role in ROLES:
			add_permission(doctype, role, 0)
			for right in rights:
				update_permission_property(doctype, role, 0, right, 1, validate=False)

	frappe.clear_cache(doctype="On the Job Training")
