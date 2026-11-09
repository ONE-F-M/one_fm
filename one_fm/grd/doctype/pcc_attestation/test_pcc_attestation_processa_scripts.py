# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the PCC Attestation Lifecycle process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, now_datetime, today

SCRIPTS = {
	"Validate PCC Attestation Step": """# Checks the action taken on the PCC Attestation task before the process moves the record on.
# Sets result["step_valid"] and result["next_state"]; on False the process reopens the same task.
action = task_data.get("action")
state = doc.workflow_state
errors = []
next_state = None

RECEIPTS = {
	"Pending Embassy": ("upload_embassy_payment_receipt", "Upload Embassy Payment Receipt"),
	"Pending MOFA": ("upload_mofa_payment_receipt", "Upload MOFA Payment Receipt"),
	"Pending Translation": ("upload_translation_payment_receipt", "Upload Translation Payment Receipt"),
}

if state == "Draft" and action == "Assign PRO":
	if doc.type == "Attestation" and doc.embassy_attestation_required:
		next_state = "Pending Embassy"
	elif doc.type == "Attestation" and doc.mofa_attestation_required:
		next_state = "Pending MOFA"
	elif doc.type == "Translation" or doc.translation_required:
		next_state = "Pending Translation"
	else:
		# Nothing to attest or translate: straight to the GR Operator, no PRO needed.
		next_state = "Pending GR Operator"
	if next_state != "Pending GR Operator" and not doc.pro_user:
		errors.append(frappe._("Please select a PRO User before proceeding."))

elif state in RECEIPTS:
	fieldname, label = RECEIPTS[state]
	if not doc.get(fieldname):
		errors.append(
			frappe._("{0} is required before this record can be submitted to the Government Relations Operator.").format(
				frappe.bold(frappe._(label))
			)
		)
	if state == "Pending Embassy" and action == "Submit MOFA Receipt" and not doc.mofa_attestation_required:
		errors.append(frappe._("This nationality needs no MOFA attestation. Use Submit."))
	if state == "Pending Embassy" and action == "Submit" and doc.mofa_attestation_required:
		errors.append(frappe._("This nationality needs MOFA attestation. Use Submit MOFA Receipt."))

result["step_valid"] = not errors
result["next_state"] = next_state or ""
for e in errors:
	frappe.msgprint(e, title=frappe._("Cannot Continue"), indicator="red")
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
		"context_doctype": "PCC Attestation",
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


def pcc(**kw):
	doc = frappe.new_doc("PCC Attestation")
	doc.name = "PCC-PROCESSA-TEST-1"
	doc.update({"type": "Attestation", **kw})
	return doc


class TestValidatePCCAttestationStep(FrappeTestCase):
	def step(self, doc, action):
		return run("Validate PCC Attestation Step", doc, action=action)

	def test_assign_pro_routes_by_the_nationality_rule(self):
		cases = [
			(dict(embassy_attestation_required=1, mofa_attestation_required=1), "Pending Embassy"),
			(dict(mofa_attestation_required=1), "Pending MOFA"),
			(dict(translation_required=1), "Pending Translation"),
			(dict(type="Translation"), "Pending Translation"),
			({}, "Pending GR Operator"),
		]
		for flags, expected in cases:
			r = self.step(pcc(workflow_state="Draft", pro_user="Administrator", **flags), "Assign PRO")
			self.assertEqual(r["next_state"], expected, flags)
			self.assertTrue(r["step_valid"])

	def test_a_pro_step_needs_a_pro_user(self):
		self.assertFalse(self.step(pcc(workflow_state="Draft", mofa_attestation_required=1), "Assign PRO")["step_valid"])
		self.assertTrue(self.step(pcc(workflow_state="Draft"), "Assign PRO")["step_valid"])

	def test_each_state_needs_its_own_receipt(self):
		for state, field in (("Pending Embassy", "upload_embassy_payment_receipt"), ("Pending MOFA", "upload_mofa_payment_receipt"),
				("Pending Translation", "upload_translation_payment_receipt")):
			doc = pcc(workflow_state=state)
			self.assertFalse(self.step(doc, "Submit")["step_valid"], state)
			doc.upload_mofa_payment_receipt = "/files/wrong.pdf" if field != "upload_mofa_payment_receipt" else None
			doc.set(field, "/files/r.pdf")
			self.assertTrue(self.step(doc, "Submit")["step_valid"], state)

	def test_the_embassy_action_follows_the_mofa_rule(self):
		doc = pcc(workflow_state="Pending Embassy", upload_embassy_payment_receipt="/files/r.pdf", mofa_attestation_required=1)
		self.assertFalse(self.step(doc, "Submit")["step_valid"])
		self.assertTrue(self.step(doc, "Submit MOFA Receipt")["step_valid"])
