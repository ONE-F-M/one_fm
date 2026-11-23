# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Transportation Manifest process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

SCRIPTS = {
	"Sync Manifest Rambo Assignments": """# Runs after every save of a Transportation Manifest. A row needs a Rambo Assignment when
# Requires Reliever is ticked, a reliever is chosen, and the employee is Absent or is Present
# but failed QOA. Such a row gets one submitted Rambo Assignment; a changed row gets a new one;
# a row that no longer needs one loses it (cancelled, then deleted).
# Each row is all or nothing: a failure rolls that row back, is logged and shown to the user,
# and the other rows still sync.
def needs_rambo(row):
	return bool(
		row.requires_reliever
		and row.reliever_employee
		and (row.attendance_status == "Absent" or (row.attendance_status == "Present" and row.qoa_status == "Fail"))
	)


def rambo_values(row):
	employee = frappe.db.get_value("Employee", row.reliever_employee, ["employee_name", "custom_is_rambo_reliever"], as_dict=True) or {}
	supervisor = frappe.db.get_value("Operations Shift", row.operations_shift, "supervisor") if row.operations_shift else None
	return {
		"transportation_manifest": doc.name,
		"manifest_child_row_id": row.name,
		"date": doc.schedule_date,
		"original_employee": row.employee,
		"original_employee_name": frappe.db.get_value("Employee", row.employee, "employee_name") if row.employee else None,
		"employee": row.reliever_employee,
		"employee_name": employee.get("employee_name"),
		"is_rambo_reliever": employee.get("custom_is_rambo_reliever") or 0,
		"shift_supervisor": supervisor,
		"shift_supervisor_user": frappe.db.get_value("Employee", supervisor, "user_id") if supervisor else None,
		"operations_role": row.operations_role,
		"operations_shift": row.operations_shift,
		"operations_site": row.operations_site,
		"project": row.project,
		"start_time": row.start_time,
		"end_time": row.end_time,
		"roster_type": "Basic",
	}


def link_row(row_name, rambo_name):
	frappe.db.set_value("Transportation Manifest Details", row_name, "rambo_assignment", rambo_name, update_modified=False)


def remove_rambo(rambo_name, row_name):
	# The row link goes first, or the delete is refused as linked.
	link_row(row_name, None)
	rambo = frappe.get_doc("Rambo Assignment", rambo_name)
	if rambo.docstatus == 1:
		rambo.cancel()
	frappe.delete_doc("Rambo Assignment", rambo_name)


def sync_row(row):
	existing = frappe.db.get_value("Rambo Assignment", {"manifest_child_row_id": row.name}, "name")
	if not needs_rambo(row):
		if existing:
			remove_rambo(existing, row.name)
		return
	values = rambo_values(row)
	if existing:
		current = frappe.get_doc("Rambo Assignment", existing)
		if current.docstatus == 0:
			# A draft left from before Rambo Assignment was submittable.
			current.update(values)
			current.submit()
			return
		if current.docstatus == 1 and not any(frappe.utils.cstr(current.get(f)) != frappe.utils.cstr(v) for f, v in values.items()):
			# Unchanged: saving the manifest again must not resend the notifications.
			return
		remove_rambo(existing, row.name)
	rambo = frappe.new_doc("Rambo Assignment")
	rambo.update(values)
	rambo.insert()
	rambo.submit()
	link_row(row.name, rambo.name)


failed = []
for row in doc.transportation_manifest_details:
	savepoint = "rambo_sync_" + frappe.generate_hash(length=10)
	frappe.db.savepoint(savepoint)
	try:
		sync_row(row)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		failed.append(row.employee_name or row.employee or row.name)
		frappe.log_error(title="Rambo Assignment sync failed for " + doc.name, message=frappe.get_traceback())

result["rambo_sync_failed"] = bool(failed)
if failed:
	result["rambo_sync_error"] = ", ".join(failed)
	frappe.msgprint(
		frappe._("The Rambo Assignment could not be updated for {0}. The error is in the Error Log.").format(", ".join(failed)),
		indicator="orange",
	)
""",
}


def run(script_name, doc, **task_data):
	"""Run a script the way the Processa engine does and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc,
		"task_data": task_data,
		"result": result,
		"context_doctype": "Transportation Manifest",
		"context_docname": doc.name if doc else None,
		"bpmn_id": "test",
	}
	with patch("frappe.msgprint"):
		exec(SCRIPTS[script_name], namespace)
	return result


class TestSiteScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is None:
				continue
			self.assertEqual(saved.strip(), body.strip(), name)


SYNC = "Sync Manifest Rambo Assignments"
DATE = "2029-01-10"


def _row(**kw):
	values = dict(name="ROW-1", idx=1, employee="HR-EMP-1", employee_name="Worker", requires_reliever=1, reliever_employee="HR-EMP-2",
		attendance_status="Absent", qoa_status=None, operations_shift="SHIFT-1", operations_role="ROLE-1", operations_site="SITE-1",
		project="PROJ-1", start_time="08:00:00", end_time="16:00:00")
	values.update(kw)
	return frappe._dict(values)


def _manifest(*rows):
	return frappe._dict(name="TM-TEST", schedule_date=DATE, transportation_manifest_details=list(rows))


def _lookup(existing=None):
	"""frappe.db.get_value as the script sees it: one optional existing Rambo Assignment."""
	def get_value(doctype, filters=None, fieldname=None, *args, **kwargs):
		if doctype == "Rambo Assignment":
			return existing
		if doctype == "Employee" and isinstance(fieldname, list):
			return frappe._dict(employee_name="Reliever", custom_is_rambo_reliever=1)
		if doctype == "Employee" and fieldname == "employee_name":
			return "Worker"
		if doctype == "Employee" and fieldname == "user_id":
			return "supervisor@example.com"
		if doctype == "Operations Shift":
			return "HR-EMP-SUP"
	return get_value


def _submitted(values):
	rambo = MagicMock(docstatus=1)
	rambo.get.side_effect = lambda field: values.get(field)
	return rambo


class TestSyncManifestRamboAssignments(FrappeTestCase):
	def _run(self, manifest, existing=None, current=None):
		new = MagicMock()
		new.name = "RAMBO-NEW"
		with patch.object(frappe.db, "get_value", side_effect=_lookup(existing)), \
			patch.object(frappe.db, "set_value") as set_value, \
			patch.object(frappe.db, "savepoint"), patch.object(frappe.db, "rollback") as rollback, \
			patch("frappe.new_doc", return_value=new) as new_doc, \
			patch("frappe.get_doc", return_value=current) as get_doc, \
			patch("frappe.delete_doc") as delete_doc, patch("frappe.log_error") as log_error:
			result = run(SYNC, manifest)
		return frappe._dict(result=result, new=new, new_doc=new_doc, set_value=set_value, rollback=rollback,
			get_doc=get_doc, delete_doc=delete_doc, log_error=log_error)

	def _values(self, manifest):
		"""The values the script writes for the first row."""
		r = self._run(manifest)
		return r.new.update.call_args[0][0]

	def test_a_row_without_a_reliever_is_left_alone(self):
		r = self._run(_manifest(_row(requires_reliever=0, reliever_employee=None)))
		r.new_doc.assert_not_called()
		r.delete_doc.assert_not_called()
		self.assertFalse(r.result["rambo_sync_failed"])

	def test_a_present_row_that_passed_qoa_needs_no_reliever(self):
		r = self._run(_manifest(_row(attendance_status="Present", qoa_status="Pass")))
		r.new_doc.assert_not_called()

	def test_an_absent_row_gets_a_submitted_rambo_assignment(self):
		r = self._run(_manifest(_row()))
		r.new.insert.assert_called_once()
		r.new.submit.assert_called_once()
		values = r.new.update.call_args[0][0]
		self.assertEqual(values["employee"], "HR-EMP-2")
		self.assertEqual(values["manifest_child_row_id"], "ROW-1")
		self.assertEqual(values["shift_supervisor_user"], "supervisor@example.com")
		self.assertEqual(values["roster_type"], "Basic")
		r.set_value.assert_any_call("Transportation Manifest Details", "ROW-1", "rambo_assignment", "RAMBO-NEW", update_modified=False)

	def test_a_present_row_that_failed_qoa_gets_one(self):
		r = self._run(_manifest(_row(attendance_status="Present", qoa_status="Fail")))
		r.new.submit.assert_called_once()

	def test_an_unchanged_assignment_is_not_sent_again(self):
		values = self._values(_manifest(_row()))
		# A date read back from the database and an empty time compare equal to what the row holds.
		values = dict(values, date=frappe.utils.getdate(DATE), start_time="08:00:00")
		r = self._run(_manifest(_row()), existing="RAMBO-OLD", current=_submitted(values))
		r.new_doc.assert_not_called()
		r.delete_doc.assert_not_called()

	def test_a_new_reliever_replaces_the_assignment(self):
		values = self._values(_manifest(_row()))
		current = _submitted(dict(values, employee="HR-EMP-9"))
		r = self._run(_manifest(_row()), existing="RAMBO-OLD", current=current)
		current.cancel.assert_called_once()
		r.delete_doc.assert_called_once_with("Rambo Assignment", "RAMBO-OLD")
		r.new.submit.assert_called_once()

	def test_a_row_that_no_longer_needs_one_loses_it(self):
		current = _submitted({})
		r = self._run(_manifest(_row(attendance_status="Present", qoa_status="Pass")), existing="RAMBO-OLD", current=current)
		r.set_value.assert_any_call("Transportation Manifest Details", "ROW-1", "rambo_assignment", None, update_modified=False)
		current.cancel.assert_called_once()
		r.delete_doc.assert_called_once_with("Rambo Assignment", "RAMBO-OLD")
		r.new_doc.assert_not_called()

	def test_an_old_draft_is_submitted_in_place(self):
		draft = MagicMock(docstatus=0)
		r = self._run(_manifest(_row()), existing="RAMBO-OLD", current=draft)
		draft.update.assert_called_once()
		draft.submit.assert_called_once()
		r.new_doc.assert_not_called()

	def test_a_failed_row_is_rolled_back_and_reported(self):
		with patch("frappe.msgprint") as msgprint:
			new = MagicMock()
			new.submit.side_effect = frappe.ValidationError("no shift")
			with patch.object(frappe.db, "get_value", side_effect=_lookup()), patch.object(frappe.db, "set_value"), \
				patch.object(frappe.db, "savepoint"), patch.object(frappe.db, "rollback") as rollback, \
				patch("frappe.new_doc", return_value=new), patch("frappe.log_error") as log_error:
				namespace = {"frappe": frappe, "doc": _manifest(_row(), _row(name="ROW-2", employee_name="Second", attendance_status="Present", qoa_status="Pass")),
					"task_data": {}, "result": {}, "context_doctype": "Transportation Manifest", "context_docname": "TM-TEST", "bpmn_id": "test"}
				exec(SCRIPTS[SYNC], namespace)
		result = namespace["result"]
		self.assertTrue(result["rambo_sync_failed"])
		self.assertEqual(result["rambo_sync_error"], "Worker")
		rollback.assert_called_once()
		log_error.assert_called_once()
		self.assertIn("Worker", msgprint.call_args[0][0])
