"""The Client Interview Shortlist script tasks write Attendance and Employee Schedule for other employees, so they run with system permissions again.

The Processa handover moved mark_attendance and the schedule swap out of the controller
into Server Scripts. The controller inserted with ignore_permissions=True; the ported
scripts insert bare. A Server Script runs as the session user, so the Operations
Supervisor who completes the map fails on "You need the 'create' permission on
Attendance": the role carries create, but the blanket User Permission on their own
Employee record denies the document level check for anybody else, and the role has no
submit on Attendance either.
"""

import frappe

# server script -> the writes to guard, as (vulnerable text, replacement)
REPLACEMENTS = {
	"Mark Interview Attendance": (
		(
			"        attendance.insert()\n",
			"        attendance.insert(ignore_permissions=True)\n",
		),
	),
	"Replace Employee Schedules": (
		(
			'                        frappe.get_doc("Attendance", att.name).cancel()\n',
			'                        att_doc = frappe.get_doc("Attendance", att.name)\n'
			"                        att_doc.flags.ignore_permissions = True\n"
			"                        att_doc.cancel()\n",
		),
		(
			'            sa_doc = frappe.get_doc("Shift Assignment", sa.name)\n',
			'            sa_doc = frappe.get_doc("Shift Assignment", sa.name)\n'
			"            sa_doc.flags.ignore_permissions = True\n",
		),
		(
			"    new_schedule.insert()\n",
			"    new_schedule.insert(ignore_permissions=True)\n",
		),
	),
}


def execute():
	for script_name, replacements in REPLACEMENTS.items():
		restore_ignore_permissions(script_name, replacements)


def restore_ignore_permissions(script_name, replacements):
	"""Guard the writes in one Server Script, leaving an already fixed or rewritten script alone."""
	if not frappe.db.exists("Server Script", script_name):
		# The Processa maps are site data, so a site without the Client Interview
		# Shortlist map has nothing to fix.
		return

	script = frappe.db.get_value("Server Script", script_name, "script")
	updated = script

	for vulnerable, fixed in replacements:
		if fixed in updated:
			# Already carries the bypass, from an earlier run or a manual fix.
			continue

		if vulnerable not in updated:
			# Somebody rewrote this part of the script. Replacing it blindly would undo
			# their work, so leave it and name the write that is still unguarded.
			frappe.log_error(
				title="Client Interview Shortlist script not patched",
				message=(
					f"{script_name} no longer contains:\n\n{vulnerable}\n"
					"Add ignore_permissions to that write by hand, otherwise the Operations "
					"Supervisor completing the map fails on a permission error."
				),
			)
			continue

		updated = updated.replace(vulnerable, fixed)

	if updated == script:
		return

	# Saved through the document so that on_update clears the server script cache.
	doc = frappe.get_doc("Server Script", script_name)
	doc.script = updated
	doc.save()
