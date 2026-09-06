import frappe


def execute():
	"""add_resignation_buttons created the "Employee Resignation" App Service
	but never set auto_assign=1, so user_app_service()'s one-time seeding logic
	(one_fm/api/v1/configuration.py) never included it for anyone -- new
	employees and existing ones alike. The mobile app's Manage Services screen
	marks it "locked"/Required, but locked only blocks removal; it never adds
	a service that isn't already present, so the label had no actual effect.

	This backfills both halves: flips the master flag so future provisioning
	(new User App Service records) picks it up, and adds it directly to every
	existing User App Service record so employees already using the app get it
	on their home page too, without waiting on a fresh install.
	"""
	service = frappe.db.get_value(
		"App Service", "Employee Resignation",
		["name", "assign_to_timesheet_employees", "assign_to_non_timesheet_employees"],
		as_dict=True,
	)
	if not service:
		return

	frappe.db.set_value("App Service", service.name, "auto_assign", 1, update_modified=False)
	backfill_existing_users(service)
	frappe.db.commit()


def backfill_existing_users(service):
	timesheet_employees = set(frappe.db.get_all(
		"Employee", filters={"attendance_by_timesheet": 1}, pluck="name",
	))

	rows = frappe.db.sql(
		"""
		select uas.name, uas.employee
		from `tabUser App Service` uas
		where not exists (
			select 1 from `tabUser App Service Detail` uasd
			where uasd.parent = uas.name and uasd.service = 'Employee Resignation'
		)
		""",
		as_dict=True,
	)

	for row in rows:
		is_timesheet_employee = row.employee in timesheet_employees
		eligible = (
			service.assign_to_timesheet_employees if is_timesheet_employee
			else service.assign_to_non_timesheet_employees
		)
		if not eligible:
			continue

		try:
			doc = frappe.get_doc("User App Service", row.name)
			doc.append("service_detail", {"service": "Employee Resignation"})
			doc.save(ignore_permissions=True)
		except Exception:
			frappe.log_error(
				title="Employee Resignation auto_assign backfill failed",
				message=f"{row.name}: {frappe.get_traceback()}",
			)
