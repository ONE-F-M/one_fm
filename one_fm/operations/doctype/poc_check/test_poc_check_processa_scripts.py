# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the POC Check process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

import json
import os
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

import one_fm
from one_fm.patches.v15_0.move_poc_check_lifecycle_to_processa import execute as retire_poc_check

SITE = "_Test POC Check Site"

SCRIPTS = {
	"Set POC Check Operations Manager": """# Default the Operations Manager from Operation Settings so the user task has someone to assign.
if not doc.operations_manager_user:
    doc.operations_manager_user = frappe.db.get_single_value("Operation Settings", "default_operation_manager")
    doc.save()

result["operations_manager_user"] = doc.operations_manager_user
""",
	"Check POC Check Rows": """# Validate every row before submit: an action on each row, a destination where one is needed, and the POC present where it will be changed.
DESTINATIONS = {"Operations Site": ["Operations Site"], "Project": ["Project"], "Both": ["Operations Site", "Project"]}

problems = []
for row in doc.mom_poc_table:
    if row.action not in ("Update POC", "Delete POC", "Do Nothing"):
        problems.append(frappe._("Set an action for row {0} in the MOM POC table.").format(row.idx))
        continue
    if row.action == "Do Nothing":
        continue
    targets = DESTINATIONS.get(row.destination)
    if not targets:
        problems.append(frappe._("Set a destination for row {0} in the MOM POC table.").format(row.idx))
        continue
    if row.action == "Update POC" and not row.new_poc_name:
        problems.append(frappe._("Select the new POC contact for row {0} in the MOM POC table.").format(row.idx))
    for parenttype in targets:
        parent = doc.project if parenttype == "Project" else doc.site
        if not frappe.db.exists("POC", {"parenttype": parenttype, "parent": parent, "poc": row.poc_name}):
            problems.append(frappe._("{0} is not set as a POC in {1} {2}.").format(row.poc_name, parenttype, parent))

for row in doc.general_attendees:
    if row.action not in ("Do Nothing", "Add as POC"):
        problems.append(frappe._("Set an action for row {0} in the General Attendees table.").format(row.idx))
    elif row.action == "Add as POC" and not DESTINATIONS.get(row.destination_doctype):
        problems.append(frappe._("Set a destination for row {0} in the General Attendees table.").format(row.idx))

result["mismatch"] = bool(problems)
result["mismatch_message"] = "<br>".join(problems)
""",
	"Show POC Mismatch Message": """# Tell the user what to fix; the Action POC Check task stays open for another try.
frappe.msgprint(task_data.get("mismatch_message") or frappe._("Please review the POC Check rows."), title=frappe._("POC Check cannot be submitted"), indicator="red")
""",
	"Execute POC Changes": """# Apply each row: replace or delete POC rows on the Project and Operations Site, add attendees as POCs, then close the open assignments.
DESTINATIONS = {"Operations Site": ["Operations Site"], "Project": ["Project"], "Both": ["Operations Site", "Project"]}

updated = 0
deleted = 0
added = 0
for row in doc.mom_poc_table:
    if row.action not in ("Update POC", "Delete POC"):
        continue
    for parenttype in DESTINATIONS.get(row.destination, []):
        parent = doc.project if parenttype == "Project" else doc.site
        for name in frappe.get_all("POC", filters={"parenttype": parenttype, "parent": parent, "poc": row.poc_name}, pluck="name"):
            if row.action == "Update POC":
                frappe.db.set_value("POC", name, {"poc": row.new_poc_name, "designation": row.new_poc_designation})
                updated += 1
            else:
                frappe.delete_doc("POC", name)
                deleted += 1

for row in doc.general_attendees:
    if row.action != "Add as POC":
        continue
    contact = frappe.db.get_value("Contact", {"first_name": row.first_name, "last_name": row.last_name}, "name")
    if not contact:
        contact_doc = frappe.get_doc({
            "doctype": "Contact",
            "first_name": row.first_name,
            "last_name": row.last_name,
            "designation": row.designation,
            "gender": row.gender,
            "email_ids": [{"email_id": row.email_address, "is_primary": 1}] if row.email_address else [],
            "phone_nos": [{"phone": row.phone, "is_primary_phone": 1}] if row.phone else [],
        })
        contact_doc.insert()
        contact = contact_doc.name
        frappe.msgprint(frappe._("Contact {0} was not found and has been created.").format(contact), title=frappe._("Contact created"), indicator="blue")
    for parenttype in DESTINATIONS.get(row.destination_doctype, []):
        parent = doc.project if parenttype == "Project" else doc.site
        if frappe.db.exists("POC", {"parenttype": parenttype, "parent": parent, "poc": contact}):
            continue
        frappe.get_doc({"doctype": "POC", "parenttype": parenttype, "parentfield": "poc", "parent": parent, "poc": contact, "designation": row.designation}).insert()
        added += 1

# set_status saves the ToDo, so the assignment also leaves the document's sidebar.
from frappe.desk.form.assign_to import set_status

open_todos = frappe.get_all("ToDo", filters={"reference_type": "POC Check", "reference_name": doc.name, "status": "Open"}, pluck="name")
for todo in open_todos:
    set_status("POC Check", doc.name, todo=todo, status="Closed")

result["pocs_updated"] = updated
result["pocs_deleted"] = deleted
result["pocs_added"] = added
result["assignments_closed"] = len(open_todos)
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
		"context_doctype": "POC Check",
		"context_docname": doc.name,
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


def a_contact(first_name, last_name="Probe"):
	name = frappe.db.get_value("Contact", {"first_name": first_name, "last_name": last_name}, "name")
	if name:
		return name
	return (
		frappe.get_doc({"doctype": "Contact", "first_name": first_name, "last_name": last_name}).insert().name
	)


def reset_site():
	"""Drop the POC rows earlier tests added; inserts are committed by hooks, so rollback leaves them."""
	frappe.db.delete("POC", {"parenttype": "Operations Site", "parent": SITE})


def site_poc(contact, designation="Supervisor"):
	return (
		frappe.get_doc(
			{
				"doctype": "POC",
				"parenttype": "Operations Site",
				"parentfield": "poc",
				"parent": SITE,
				"poc": contact,
				"designation": designation,
			}
		)
		.insert()
		.name
	)


def site_pocs():
	rows = frappe.get_all(
		"POC", filters={"parenttype": "Operations Site", "parent": SITE}, fields=["poc", "designation"]
	)
	return {r.poc: r.designation for r in rows}


def poc_check(rows=(), attendees=()):
	doc = frappe.new_doc("POC Check")
	doc.name = "POC-CHK-PROCESSA-TEST"
	doc.update({"site": SITE, "supervisor_name": "probe"})
	for row in rows:
		doc.append("mom_poc_table", row)
	for row in attendees:
		doc.append("general_attendees", row)
	return doc


class TestSetPOCCheckOperationsManager(FrappeTestCase):
	def test_fills_the_default_manager_and_saves_it(self):
		frappe.db.set_single_value("Operation Settings", "default_operation_manager", "Administrator")
		doc = frappe.get_doc({"doctype": "POC Check", "supervisor_name": "probe"}).insert()
		doc.db_set("operations_manager_user", None)
		doc.reload()

		out = run("Set POC Check Operations Manager", doc)

		self.assertEqual(out["operations_manager_user"], "Administrator")
		self.assertEqual(
			frappe.db.get_value("POC Check", doc.name, "operations_manager_user"), "Administrator"
		)

	def test_keeps_a_manager_already_chosen(self):
		frappe.db.set_single_value("Operation Settings", "default_operation_manager", "Administrator")
		doc = frappe.get_doc(
			{"doctype": "POC Check", "supervisor_name": "probe", "operations_manager_user": "Guest"}
		).insert()

		out = run("Set POC Check Operations Manager", doc)

		self.assertEqual(out["operations_manager_user"], "Guest")


class TestCheckPOCCheckRows(FrappeTestCase):
	def setUp(self):
		reset_site()

	def test_a_row_without_an_action_blocks_the_submit(self):
		out = run("Check POC Check Rows", poc_check(rows=[{"poc_name": "Anyone"}]))

		self.assertTrue(out["mismatch"])
		self.assertIn("Set an action for row 1 in the MOM POC table.", out["mismatch_message"])

	def test_do_nothing_rows_pass(self):
		out = run("Check POC Check Rows", poc_check(rows=[{"poc_name": "Anyone", "action": "Do Nothing"}]))

		self.assertFalse(out["mismatch"])
		self.assertEqual(out["mismatch_message"], "")

	def test_an_update_needs_a_destination_and_the_new_contact(self):
		contact = a_contact("Alpha")
		site_poc(contact)
		no_destination = poc_check(rows=[{"poc_name": contact, "action": "Update POC"}])
		no_contact = poc_check(
			rows=[{"poc_name": contact, "action": "Update POC", "destination": "Operations Site"}]
		)

		self.assertIn(
			"Set a destination for row 1", run("Check POC Check Rows", no_destination)["mismatch_message"]
		)
		self.assertIn(
			"Select the new POC contact for row 1",
			run("Check POC Check Rows", no_contact)["mismatch_message"],
		)

	def test_the_poc_must_already_be_on_the_destination(self):
		contact = a_contact("Beta")
		doc = poc_check(
			rows=[{"poc_name": contact, "action": "Delete POC", "destination": "Operations Site"}]
		)

		out = run("Check POC Check Rows", doc)

		self.assertTrue(out["mismatch"])
		self.assertIn(f"{contact} is not set as a POC in Operations Site {SITE}", out["mismatch_message"])

	def test_an_attendee_added_as_poc_needs_a_destination(self):
		doc = poc_check(attendees=[{"first_name": "Gamma", "last_name": "Probe", "action": "Add as POC"}])

		out = run("Check POC Check Rows", doc)

		self.assertTrue(out["mismatch"])
		self.assertIn("Set a destination for row 1 in the General Attendees table.", out["mismatch_message"])


class TestExecutePOCChanges(FrappeTestCase):
	def setUp(self):
		reset_site()

	def test_an_update_replaces_the_contact_on_the_site(self):
		old, new = a_contact("Old"), a_contact("New")
		site_poc(old, "Supervisor")
		doc = poc_check(
			rows=[
				{
					"poc_name": old,
					"action": "Update POC",
					"destination": "Operations Site",
					"new_poc_name": new,
					"new_poc_designation": "Manager",
				}
			]
		)

		out = run("Execute POC Changes", doc)

		self.assertEqual(out["pocs_updated"], 1)
		self.assertEqual(site_pocs(), {new: "Manager"})

	def test_a_delete_removes_the_site_row(self):
		gone, kept = a_contact("Gone"), a_contact("Kept")
		site_poc(gone)
		site_poc(kept)
		doc = poc_check(rows=[{"poc_name": gone, "action": "Delete POC", "destination": "Operations Site"}])

		out = run("Execute POC Changes", doc)

		self.assertEqual(out["pocs_deleted"], 1)
		self.assertEqual(set(site_pocs()), {kept})

	def test_a_new_attendee_becomes_a_contact_and_a_site_poc(self):
		doc = poc_check(
			attendees=[
				{
					"first_name": "Delta",
					"last_name": "Probe",
					"designation": "Visitor",
					"email_address": "delta.probe@example.com",
					"action": "Add as POC",
					"destination_doctype": "Operations Site",
				}
			]
		)

		out = run("Execute POC Changes", doc)

		contact = frappe.db.get_value("Contact", {"first_name": "Delta", "last_name": "Probe"}, "name")
		self.assertTrue(contact)
		self.assertEqual(frappe.db.get_value("Contact", contact, "email_id"), "delta.probe@example.com")
		self.assertEqual(out["pocs_added"], 1)
		self.assertEqual(site_pocs(), {contact: "Visitor"})

	def test_an_attendee_who_is_already_a_contact_is_reused(self):
		contact = a_contact("Epsilon")
		doc = poc_check(
			attendees=[
				{
					"first_name": "Epsilon",
					"last_name": "Probe",
					"action": "Add as POC",
					"destination_doctype": "Operations Site",
				}
			]
		)

		run("Execute POC Changes", doc)

		self.assertEqual(frappe.db.count("Contact", {"first_name": "Epsilon", "last_name": "Probe"}), 1)
		self.assertEqual(set(site_pocs()), {contact})

	def test_open_assignments_are_closed_and_leave_the_sidebar(self):
		doc = frappe.get_doc(
			{"doctype": "POC Check", "supervisor_name": "probe", "operations_manager_user": "Administrator"}
		).insert()
		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"reference_type": "POC Check",
				"reference_name": doc.name,
				"allocated_to": "Guest",
				"description": "probe",
				"status": "Open",
			}
		).insert()
		self.assertIn("Guest", frappe.db.get_value("POC Check", doc.name, "_assign"))

		out = run("Execute POC Changes", doc)

		self.assertGreaterEqual(out["assignments_closed"], 1)
		self.assertEqual(frappe.db.get_value("ToDo", todo.name, "status"), "Closed")
		self.assertFalse(frappe.db.get_value("POC Check", doc.name, "_assign"))


class TestRetirePOCCheckAssignmentRule(FrappeTestCase):
	def test_the_patch_switches_the_assignment_rule_off(self):
		frappe.db.set_value("Assignment Rule", "Action POC Check", "disabled", 0)

		retire_poc_check()

		self.assertEqual(frappe.db.get_value("Assignment Rule", "Action POC Check", "disabled"), 1)

	def test_the_shipped_rule_file_is_disabled(self):
		path = os.path.join(
			os.path.dirname(one_fm.__file__), "custom", "assignment_rule", "action_poc_check.json"
		)
		with open(path) as handle:
			self.assertEqual(json.load(handle)["disabled"], 1)
