# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Request for Material process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Set Request for Material Status": """# Keeps Status in step with the state, as the RFM Workflow's state rows did.
status = {"Pending Approval": "Draft", "Approved": "Approved", "Rejected": "Rejected", "Cancelled": "Cancelled"}.get(doc.workflow_state)
if status and doc.status != status:
	frappe.db.set_value("Request for Material", doc.name, "status", status)
""",
	"Check Request for Material Decision": """# Approve or Reject needs the Required Date, and a description of the damage on every uniform row.
# Sets result["step_valid"]; on False the process reopens the Pending Approval task.
issues = []
if not doc.schedule_date:
	issues.append(frappe._("Set the Required Date before deciding this request."))
for item in doc.items:
	if item.is_uniform_request and not item.requested_description:
		issues.append(frappe._("Row #{0}: describe the damage before deciding this request.").format(item.idx))
result["step_valid"] = not issues
if issues:
	frappe.msgprint("<br>".join(issues), title=frappe._("Cannot Decide Yet"), indicator="red")
""",
	"Notify Request for Material Requester": """# Tells the requester their request was approved, by email and in the notification bell.
from one_fm.purchase.doctype.request_for_material.request_for_material import create_notification_log, send_email

if doc.requested_by:
	approver = frappe.session.user
	message = "Request for Material <a href='{0}'>{1}</a> is {2} by {3}.".format(frappe.utils.get_url(doc.get_url()), doc.name, doc.workflow_state, approver)
	message += "You will be notified of the expected delivery date as soon as the order is processed"
	subject = "{0} {1} your Request for Material {2}".format(doc.workflow_state, frappe.utils.get_fullname(approver), doc.name)
	send_email(doc, [doc.requested_by], message, subject)
	create_notification_log(subject, message, [doc.requested_by], doc)
""",
	"Assign Request for Material Technical Verification": """from frappe.desk.form.assign_to import add

# When technical verification is needed and no remarks are in yet, gives the verifier a ToDo to add them.
if doc.technical_verification_needed == "Yes" and doc.technical_verification_from and not doc.technical_remarks:
	if not frappe.db.exists("ToDo", {"reference_type": doc.doctype, "reference_name": doc.name, "allocated_to": doc.technical_verification_from, "status": "Open"}):
		add({
			"doctype": doc.doctype,
			"name": doc.name,
			"assign_to": [doc.technical_verification_from],
			"description": frappe._("Please add Your Technical Remarks for the Item Descriptions"),
		})
		doc.add_comment("Comment", frappe._("Waiting for Technical Verification"))
""",
	"Assign Request for Material Warehouse Supervisor": """# The approved request goes to the employee on the Requisition process task P-TASK-2026-00017
# (the Warehouse Supervisor who processes approved requests), or to every Warehouse Supervisor when it has none.
user = frappe.db.get_value("Process Task", {"name": "P-TASK-2026-00017", "is_active": 1}, "employee_user")
result["assigned_user"] = user or ""
result["assigned_role"] = "" if user else "Warehouse Supervisor"
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
		"context_doctype": "Request for Material",
		"context_docname": doc.name,
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


MODULE = "one_fm.purchase.doctype.request_for_material.request_for_material"


def rfm(**kw):
	doc = frappe.new_doc("Request for Material")
	doc.name = "RFM-PROCESSA-TEST-1"
	doc.update(kw)
	return doc


def uniform_row(description=None):
	return {"is_uniform_request": 1, "size": "XL", "attach_photo": "/files/x.jpg", "qty": 1, "requested_description": description}


class TestSetRequestForMaterialStatus(FrappeTestCase):
	def test_each_state_sets_the_status_the_workflow_set(self):
		for state, status in (("Pending Approval", "Draft"), ("Approved", "Approved"), ("Rejected", "Rejected"), ("Cancelled", "Cancelled")):
			with patch("frappe.db.set_value") as set_value:
				run("Set Request for Material Status", rfm(workflow_state=state, status="Pending"))
			set_value.assert_called_once_with("Request for Material", "RFM-PROCESSA-TEST-1", "status", status)

	def test_draft_and_an_unchanged_status_are_left_alone(self):
		with patch("frappe.db.set_value") as set_value:
			run("Set Request for Material Status", rfm(workflow_state="Draft"))
			run("Set Request for Material Status", rfm(workflow_state="Approved", status="Approved"))
		set_value.assert_not_called()


class TestCheckRequestForMaterialDecision(FrappeTestCase):
	def test_the_required_date_is_needed(self):
		doc = rfm(type="Individual", schedule_date=None, items=[uniform_row("Torn")])
		self.assertFalse(run("Check Request for Material Decision", doc)["step_valid"])

	def test_a_uniform_row_needs_a_description(self):
		doc = rfm(type="Individual", schedule_date=frappe.utils.today(), items=[uniform_row()])
		self.assertFalse(run("Check Request for Material Decision", doc)["step_valid"])

	def test_a_complete_request_may_be_decided(self):
		doc = rfm(type="Individual", schedule_date=frappe.utils.today(), items=[uniform_row("Torn")])
		self.assertTrue(run("Check Request for Material Decision", doc)["step_valid"])

	def test_other_rows_need_no_description(self):
		doc = rfm(type="Stock", schedule_date=frappe.utils.today(), items=[{"qty": 1}])
		self.assertTrue(run("Check Request for Material Decision", doc)["step_valid"])

	def test_it_never_throws(self):
		with patch("frappe.msgprint") as msgprint:
			namespace = {"frappe": frappe, "doc": rfm(type="Individual", items=[uniform_row()]), "task_data": {}, "result": {}}
			exec(SCRIPTS["Check Request for Material Decision"], namespace)
		self.assertIn("describe the damage", msgprint.call_args[0][0])


class TestNotifyRequestForMaterialRequester(FrappeTestCase):
	def test_the_requester_is_told_by_email_and_bell(self):
		with patch(MODULE + ".send_email") as send_email, patch(MODULE + ".create_notification_log") as bell:
			run("Notify Request for Material Requester", rfm(workflow_state="Approved", requested_by="emp@example.com"))
		self.assertEqual(send_email.call_args[0][1], ["emp@example.com"])
		self.assertTrue(send_email.call_args[0][3].startswith("Approved"))
		self.assertEqual(bell.call_args[0][2], ["emp@example.com"])

	def test_no_requester_no_message(self):
		with patch(MODULE + ".send_email") as send_email:
			run("Notify Request for Material Requester", rfm(workflow_state="Approved", requested_by=None))
		send_email.assert_not_called()


class TestAssignRequestForMaterialTechnicalVerification(FrappeTestCase):
	def test_the_verifier_gets_a_todo(self):
		doc = rfm(technical_verification_needed="Yes", technical_verification_from="tech@example.com")
		with patch("frappe.desk.form.assign_to.add") as add, patch("frappe.db.exists", return_value=None), patch.object(type(doc), "add_comment"):
			run("Assign Request for Material Technical Verification", doc)
		self.assertEqual(add.call_args[0][0]["assign_to"], ["tech@example.com"])

	def test_not_needed_or_already_remarked_gives_nothing(self):
		for kw in ({"technical_verification_needed": "No", "technical_verification_from": "tech@example.com"},
				{"technical_verification_needed": "Yes", "technical_verification_from": "tech@example.com", "technical_remarks": "OK"}):
			with patch("frappe.desk.form.assign_to.add") as add:
				run("Assign Request for Material Technical Verification", rfm(**kw))
			add.assert_not_called()

	def test_an_open_todo_is_not_duplicated(self):
		doc = rfm(technical_verification_needed="Yes", technical_verification_from="tech@example.com")
		with patch("frappe.desk.form.assign_to.add") as add, patch("frappe.db.exists", return_value="TODO-1"):
			run("Assign Request for Material Technical Verification", doc)
		add.assert_not_called()


class TestAssignRequestForMaterialWarehouseSupervisor(FrappeTestCase):
	def test_the_process_task_employee_gets_it(self):
		with patch("frappe.db.get_value", return_value="ws@example.com"):
			self.assertEqual(run("Assign Request for Material Warehouse Supervisor", rfm()), {"assigned_user": "ws@example.com", "assigned_role": ""})

	def test_without_one_every_warehouse_supervisor_gets_it(self):
		with patch("frappe.db.get_value", return_value=None):
			self.assertEqual(run("Assign Request for Material Warehouse Supervisor", rfm()), {"assigned_user": "", "assigned_role": "Warehouse Supervisor"})


class TestMovedLogicLeftTheController(FrappeTestCase):
	def test_no_emails_assignments_or_decision_throw_in_python(self):
		from one_fm.purchase.doctype.request_for_material.request_for_material import RequestforMaterial

		for name in ("notify_material_requester", "assign_for_technical_verification", "assign_to_warehouse_supervisor", "validate_uniform_request_before_approval"):
			self.assertFalse(hasattr(RequestforMaterial, name), name)
