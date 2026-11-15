# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Medical Insurance Lifecycle process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, now_datetime, today

SCRIPTS = {
	"Validate Medical Insurance Completion": """# Checks a Medical Insurance before the process completes it.
# Sets result["completion_valid"]; on False the process reopens the Apply Online task.
errors = []

if not doc.upload_medical_insurance:
	errors.append(frappe._("You need to upload the Medical Insurance document before you can mark this record as Done."))

# A policy opened by a Preparation completes only after its Work Permit.
if doc.preparation and doc.employee and doc.insurance_status in ("Renewal", "New", "Local Transfer"):
	pending = frappe.db.get_value(
		"Work Permit",
		{"preparation": doc.preparation, "employee": doc.employee, "docstatus": ["!=", 2], "workflow_state": ["!=", "Completed"]},
		"name",
	)
	if pending:
		errors.append(frappe._("Work Permit {0} has to be completed first.").format(frappe.bold(pending)))

result["completion_valid"] = not errors
for e in errors:
	frappe.msgprint(e, title=frappe._("Cannot Complete"), indicator="red")
""",
	"Complete Medical Insurance": """# Runs once the Medical Insurance is Completed. Records who completed it, and for a Local
# Transfer opens the transfer Residency.
frappe.db.set_value("Medical Insurance", doc.name, {
	"status": "Submitted",
	# modified_by is the user whose Done action completed the record.
	"medical_insurance_submitted_by": doc.modified_by,
	"medical_insurance_submitted_on": frappe.utils.now_datetime(),
})

if doc.insurance_status == "Local Transfer" and doc.employee:
	residency = frappe.get_doc({
		"doctype": "Residency", "employee": doc.employee, "renewal_or_extend": "Transfer",
		"category": "Transfer", "date_of_application": frappe.utils.today(),
	}).insert()
	result["transfer_residency"] = residency.name
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
		"context_doctype": "Medical Insurance",
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


class TestValidateMedicalInsuranceCompletion(FrappeTestCase):
	def policy(self, **kw):
		doc = frappe.new_doc("Medical Insurance")
		doc.name = "MI-PROCESSA-TEST-1"
		doc.update(kw)
		return doc

	def test_the_policy_upload_is_required(self):
		doc = self.policy(insurance_status="Renewal")
		self.assertFalse(run("Validate Medical Insurance Completion", doc)["completion_valid"])
		doc.upload_medical_insurance = "/files/policy.pdf"
		self.assertTrue(run("Validate Medical Insurance Completion", doc)["completion_valid"])

	def test_a_preparation_policy_waits_for_its_work_permit(self):
		pending = frappe.db.get_value("Work Permit", {"docstatus": 0, "preparation": ["is", "set"], "workflow_state": ["!=", "Completed"]}, ["preparation", "employee"], as_dict=True)
		if not pending:
			self.skipTest("No open Work Permit opened by a Preparation on this site")
		doc = self.policy(insurance_status="Renewal", upload_medical_insurance="/files/p.pdf", preparation=pending.preparation, employee=pending.employee)
		self.assertFalse(run("Validate Medical Insurance Completion", doc)["completion_valid"])
		doc.insurance_status = "Cancellation"
		self.assertTrue(run("Validate Medical Insurance Completion", doc)["completion_valid"])


class TestCompleteMedicalInsurance(FrappeTestCase):
	def test_records_who_completed_it(self):
		name = frappe.db.get_value("Medical Insurance", {"docstatus": 0, "insurance_status": ["!=", "Local Transfer"]}, "name")
		doc = frappe.get_doc("Medical Insurance", name)
		doc.modified_by = "Administrator"
		run("Complete Medical Insurance", doc)
		values = frappe.db.get_value("Medical Insurance", name, ["status", "medical_insurance_submitted_by", "medical_insurance_submitted_on"], as_dict=True)
		self.assertEqual(values.status, "Submitted")
		self.assertEqual(values.medical_insurance_submitted_by, "Administrator")
		self.assertTrue(values.medical_insurance_submitted_on)
