# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Legal Investigation Session process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Record Session on Investigation": """# Adds the submitted session to the Session Summary table of its Legal Investigation.
attendees = ", ".join(row.employee_name for row in doc.session_parties if row.attended == "Yes" and row.employee_name)
investigation = doc.legal_investigation_code
already = frappe.db.exists("Legal Investigation Sessions", {
	"parent": investigation, "parenttype": "Legal Investigation",
	"session_datetime": doc.session_datetime, "subject": doc.subject,
})
if investigation and not already:
	now = frappe.utils.now()
	idx = frappe.db.count("Legal Investigation Sessions", {"parent": investigation, "parenttype": "Legal Investigation"}) + 1
	row = frappe.get_doc({
		"doctype": "Legal Investigation Sessions",
		"name": frappe.generate_hash(length=10),
		"parent": investigation,
		"parenttype": "Legal Investigation",
		"parentfield": "session_summary",
		"idx": idx,
		"owner": frappe.session.user,
		"modified_by": frappe.session.user,
		"creation": now,
		"modified": now,
		"session_datetime": doc.session_datetime,
		"subject": doc.subject,
		"conducted_by": doc.conductor_name,
		"attendees": attendees,
		"issues": doc.notes,
		"attachment": "<a href='{0}' target='_blank'>Session Attachment (Click here)</a>".format(doc.attachment) if doc.attachment else "",
	})
	row.db_insert()
	frappe.db.set_value("Legal Investigation", investigation, "modified", now)
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
		"context_doctype": "Legal Investigation Session",
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


def session(investigation, subject, **kw):
	doc = frappe.new_doc("Legal Investigation Session")
	doc.name = "LIS-PROCESSA-TEST-1"
	doc.update({
		"legal_investigation_code": investigation,
		"session_datetime": "2026-11-16 10:00:00",
		"subject": subject,
		"conductor_name": "Test Conductor",
		"notes": "Issues raised",
		**kw,
	})
	doc.append("session_parties", {"employee_name": "Present Person", "attended": "Yes"})
	doc.append("session_parties", {"employee_name": "Absent Person", "attended": "No"})
	return doc


def summary_rows(investigation, subject):
	return frappe.get_all(
		"Legal Investigation Sessions",
		filters={"parent": investigation, "parenttype": "Legal Investigation", "subject": subject},
		fields=["attendees", "issues", "conducted_by", "attachment", "parentfield"],
	)


class TestRecordSessionOnInvestigation(FrappeTestCase):
	def setUp(self):
		self.investigation = frappe.get_all("Legal Investigation", pluck="name", limit=1)
		if not self.investigation:
			self.skipTest("No Legal Investigation on this site")
		self.investigation = self.investigation[0]

	def test_adds_the_session_with_attendees_only(self):
		run("Record Session on Investigation", session(self.investigation, "Processa test 1", attachment="/files/s.pdf"))
		rows = summary_rows(self.investigation, "Processa test 1")
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].attendees, "Present Person")
		self.assertEqual(rows[0].parentfield, "session_summary")
		self.assertIn("/files/s.pdf", rows[0].attachment)

	def test_running_twice_adds_one_row(self):
		doc = session(self.investigation, "Processa test 2")
		run("Record Session on Investigation", doc)
		run("Record Session on Investigation", doc)
		self.assertEqual(len(summary_rows(self.investigation, "Processa test 2")), 1)

	def test_session_without_attachment_leaves_it_blank(self):
		run("Record Session on Investigation", session(self.investigation, "Processa test 3"))
		self.assertFalse(summary_rows(self.investigation, "Processa test 3")[0].attachment)


class TestControllerLeavesSubmitToTheMap(FrappeTestCase):
	def test_no_on_submit_hook(self):
		from one_fm.legal.doctype.legal_investigation_session.legal_investigation_session import LegalInvestigationSession
		self.assertFalse(hasattr(LegalInvestigationSession, "on_submit"))

	def test_workflow_state_field_exists(self):
		self.assertTrue(frappe.get_meta("Legal Investigation Session").has_field("workflow_state"))
