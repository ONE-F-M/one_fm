import frappe

# WI-002301: the tile an employee taps to report a damaged uniform.
#
# The mobile app builds its Requisition section from these records rather than from a
# hard-coded list, so the icon does not exist until they do - and the route the tile opens
# is matched on the service's own name, which is why the name here and the entry in the
# app's serviceRouteMap have to stay in step.
GROUP = "Requisition"
GROUP_ICON = "clipboard-text-outline"

SERVICE = "Uniform Request"
SERVICE_ICON = "tshirt-crew-outline"


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

	if not frappe.db.exists("App Service", SERVICE):
		frappe.get_doc({
			"doctype": "App Service",
			"service": SERVICE,
			"service_group": GROUP,
			"icon": SERVICE_ICON,
			"status": "Active",
			# Anybody in a uniform can damage one, whichever way their attendance is kept.
			"assign_to_timesheet_employees": 1,
			"assign_to_non_timesheet_employees": 1,
		}).insert(ignore_permissions=True)

	verify()


def verify():
	group = frappe.db.get_value("App Service Group", GROUP, ["status"], as_dict=True)
	if not group:
		frappe.throw(f"WI-002301: the {GROUP!r} service group was not created.")
	if group.status != "Active":
		frappe.throw(f"WI-002301: the {GROUP!r} service group is {group.status}.")

	service = frappe.db.get_value(
		"App Service", SERVICE,
		["status", "service_group", "assign_to_timesheet_employees",
		 "assign_to_non_timesheet_employees"],
		as_dict=True,
	)
	if not service:
		frappe.throw(f"WI-002301: the {SERVICE!r} service was not created.")
	if service.status != "Active":
		frappe.throw(f"WI-002301: {SERVICE!r} is {service.status}, so no employee would see it.")
	if service.service_group != GROUP:
		frappe.throw(f"WI-002301: {SERVICE!r} sits under {service.service_group!r}.")
	if not (service.assign_to_timesheet_employees and service.assign_to_non_timesheet_employees):
		frappe.throw(
			f"WI-002301: {SERVICE!r} is offered to only one kind of employee - the app "
			"filters on exactly these two flags."
		)

	print(f"WI-002301: {SERVICE} is available under {GROUP}")
