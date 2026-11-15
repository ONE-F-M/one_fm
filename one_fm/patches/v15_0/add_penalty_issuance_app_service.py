import frappe

# The mobile Home tile for issuing penalties, shown only to Penalty Issuers.
GROUP = "Legal"
GROUP_ICON = "shield-check-outline"

SERVICE = "Penalty Issuance"
SERVICE_ICON = "alert-outline"
ROLE = "Penalty Issuer"


def execute():
	frappe.reload_doc("one_fm", "doctype", "app_service_group")
	frappe.reload_doc("one_fm", "doctype", "app_service")

	if not frappe.db.exists("App Service Group", GROUP):
		frappe.get_doc({
			"doctype": "App Service Group",
			"group_name": GROUP,
			"icon": GROUP_ICON,
			"status": "Active",
		}).insert(ignore_permissions=True)

	if not frappe.db.exists("Role", ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": ROLE, "desk_access": 1}).insert(ignore_permissions=True)

	values = {
		"service_group": GROUP,
		"icon": SERVICE_ICON,
		"status": "Active",
		"role": ROLE,
		# Auto-assigned so role holders get the tile on Home without adding it themselves.
		"auto_assign": 1,
		"assign_to_timesheet_employees": 1,
		"assign_to_non_timesheet_employees": 1,
	}
	if frappe.db.exists("App Service", SERVICE):
		frappe.db.set_value("App Service", SERVICE, values)
	else:
		frappe.get_doc({"doctype": "App Service", "service": SERVICE, **values}).insert(ignore_permissions=True)

	service = frappe.db.get_value("App Service", SERVICE, ["role", "status", "service_group"], as_dict=True)
	if service.role != ROLE or service.status != "Active" or service.service_group != GROUP:
		frappe.throw(f"{SERVICE} App Service was not set up: {service}")
