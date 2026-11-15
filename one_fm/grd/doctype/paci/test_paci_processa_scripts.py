# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the PACI Lifecycle process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, now_datetime, today

SCRIPTS = {
	"Validate PACI Step": """# Checks the action taken on the PACI task before the process moves the record on.
# Sets result["step_valid"]; on False the process reopens the same task.
action = task_data.get("action")
state = doc.workflow_state
errors = []


def require(fieldname, label):
	if not doc.get(fieldname):
		errors.append(frappe._(label))


def check_completion():
	require("new_civil_id_expiry_date", "New Civil ID Expiry Date")
	# A civil ID opened by a Preparation completes only after its Residency.
	if doc.preparation and doc.employee and doc.category in ("Renewal", "New Application", "Transfer"):
		pending = frappe.db.get_value(
			"Residency",
			{"preparation": doc.preparation, "employee": doc.employee, "docstatus": ["!=", 2], "workflow_state": ["!=", "Completed"]},
			"name",
		)
		if pending:
			errors.append(frappe._("Residency {0} has to be completed first.").format(frappe.bold(pending)))


if state == "Draft":
	if action == "Save" and doc.category not in ("Renewal", "Transfer"):
		errors.append(frappe._("Save is for a Renewal or Transfer."))

elif state == "Pending by GR Operator":
	if action == "Done":
		# PACI charges nothing for some transactions; those leave by No Payment Required.
		if not doc.no_payment_required:
			require("upload_civil_id_payment", "Upload Payment Invoice")
		check_completion()
	elif action == "No Payment Required":
		if not doc.no_payment_required:
			errors.append(frappe._("Tick No Payment Required first."))
		check_completion()
	elif action in ("Update Address", "Update Photo") and doc.pro_user:
		errors.append(frappe._("A PRO User is set. Use {0} by PRO.").format(action))
	elif action in ("Update Address By PRO", "Update Photo by PRO") and not doc.pro_user:
		errors.append(frappe._("Set the PRO User first."))

elif state == "Pending by PRO" and action == "Submit":
	require("pro_user", "PRO User")
	require("paci_reference_number", "PACI Reference Number")

elif state == "Pending by PACI":
	if action == "Approve":
		check_completion()
	elif action == "Reject":
		require("paci_rejection_reason", "PACI Rejection Reason")

result["step_valid"] = not errors
if errors:
	frappe.msgprint(
		frappe._("The {0} action cannot be taken yet:").format(frappe.bold(action))
		+ "<ul>" + "".join("<li>{0}</li>".format(e) for e in errors) + "</ul>",
		title=frappe._("Missing Information"),
		indicator="red",
	)
""",
	"Complete PACI": """# Runs once the PACI is Completed. Records the new civil ID on the Employee, applies a Damj
# and opens a Draft salary Bank Account for the employee.
# Employee and Bank Account are written directly: the GR Operator has no access to either.
today = frappe.utils.today()
employee_updates = {"civil_id_expiry_date": doc.new_civil_id_expiry_date}

values = {"attach": doc.upload_civil_id, "issued_on": today, "valid_till": doc.new_civil_id_expiry_date}
row = frappe.db.exists("Employee Document", {"parent": doc.employee, "document_name": "Civil ID"})
if row:
	frappe.db.set_value("Employee Document", row, values)
else:
	last = frappe.db.get_value("Employee Document", {"parent": doc.employee, "parenttype": "Employee"}, "idx", order_by="idx desc") or 0
	frappe.get_doc({"doctype": "Employee Document", "parent": doc.employee, "parenttype": "Employee",
		"parentfield": "one_fm_employee_documents", "idx": last + 1, "document_name": "Civil ID", **values}).db_insert()

record_updates = {"paci_status": "Completed", "completed_on": today}
if doc.damj_is_applicable and doc.original_civil_id:
	employee_updates["one_fm_civil_id"] = doc.original_civil_id
	record_updates["civil_id"] = doc.original_civil_id
frappe.db.set_value("Employee", doc.employee, employee_updates)
frappe.db.set_value("PACI", doc.name, record_updates)

# Draft salary Bank Account, unless the employee already has one.
BANK = "National Bank of Kuwait"
if frappe.db.exists("Bank Account", {"party_type": "Employee", "party": doc.employee}):
	frappe.msgprint(frappe._("Bank account already exists for Employee ID {0}. Skipping duplicate creation.").format(doc.employee), indicator="orange")
else:
	account_name = frappe.db.get_value("Employee", doc.employee, "employee_name")
	name = account_name + " - " + BANK
	if frappe.db.exists("Bank Account", name):
		name = name + " - " + doc.employee
	now = frappe.utils.now_datetime()
	frappe.get_doc({
		"doctype": "Bank Account", "name": name, "account_name": account_name, "bank": BANK,
		"party_type": "Employee", "party": doc.employee,
		"onboard_employee": frappe.db.get_value("Onboard Employee", {"employee": doc.employee, "workflow_state": ["!=", "Cancelled"]}, "name"),
		"owner": frappe.session.user, "modified_by": frappe.session.user, "creation": now, "modified": now, "docstatus": 0,
	}).db_insert()
	result["bank_account"] = name
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
		"context_doctype": "PACI",
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


def a_paci(**kw):
	doc = frappe.new_doc("PACI")
	doc.name = kw.pop("name", "PACI-PROCESSA-TEST-1")
	doc.update(kw)
	return doc


def an_employee(**filters):
	return frappe.get_all(
		"Employee",
		filters={"status": "Active", "relieving_date": ["is", "not set"], **filters},
		pluck="name", limit=1, order_by="creation desc",
	)[0]


class TestValidatePACIStep(FrappeTestCase):
	def valid(self, doc, action):
		return run("Validate PACI Step", doc, action=action)["step_valid"]

	def test_save_is_for_a_renewal_or_transfer(self):
		self.assertTrue(self.valid(a_paci(workflow_state="Draft", category="Renewal"), "Save"))
		self.assertFalse(self.valid(a_paci(workflow_state="Draft", category="New Application"), "Save"))
		self.assertTrue(self.valid(a_paci(workflow_state="Draft", category="New Application"), "Cancel"))

	def test_done_needs_the_invoice_unless_no_payment_is_due(self):
		doc = a_paci(workflow_state="Pending by GR Operator", new_civil_id_expiry_date=today())
		self.assertFalse(self.valid(doc, "Done"))
		doc.upload_civil_id_payment = "/files/i.pdf"
		self.assertTrue(self.valid(doc, "Done"))
		doc.upload_civil_id_payment, doc.no_payment_required = None, 1
		self.assertTrue(self.valid(doc, "Done"))

	def test_no_payment_required_needs_the_tick_and_the_expiry(self):
		doc = a_paci(workflow_state="Pending by GR Operator", new_civil_id_expiry_date=today())
		self.assertFalse(self.valid(doc, "No Payment Required"))
		doc.no_payment_required = 1
		self.assertTrue(self.valid(doc, "No Payment Required"))
		doc.new_civil_id_expiry_date = None
		self.assertFalse(self.valid(doc, "No Payment Required"))

	def test_the_update_actions_follow_the_pro_user(self):
		doc = a_paci(workflow_state="Pending by GR Operator")
		self.assertTrue(self.valid(doc, "Update Address"))
		self.assertFalse(self.valid(doc, "Update Address By PRO"))
		doc.pro_user = "Administrator"
		self.assertFalse(self.valid(doc, "Update Photo"))
		self.assertTrue(self.valid(doc, "Update Photo by PRO"))

	def test_the_pro_files_with_a_reference(self):
		doc = a_paci(workflow_state="Pending by PRO", pro_user="Administrator")
		self.assertFalse(self.valid(doc, "Submit"))
		doc.paci_reference_number = "REF-1"
		self.assertTrue(self.valid(doc, "Submit"))

	def test_a_rejection_needs_its_reason(self):
		doc = a_paci(workflow_state="Pending by PACI")
		self.assertFalse(self.valid(doc, "Reject"))
		doc.paci_rejection_reason = "x"
		self.assertTrue(self.valid(doc, "Reject"))


class TestCompletePACI(FrappeTestCase):
	def setUp(self):
		self.employee = an_employee()

	def test_records_the_civil_id_and_opens_one_bank_account(self):
		frappe.db.delete("Bank Account", {"party_type": "Employee", "party": self.employee})
		doc = a_paci(employee=self.employee, new_civil_id_expiry_date="2028-03-31", upload_civil_id="/files/c.pdf")
		result = run("Complete PACI", doc)
		self.assertEqual(str(frappe.db.get_value("Employee", self.employee, "civil_id_expiry_date")), "2028-03-31")
		self.assertTrue(frappe.db.exists("Employee Document", {"parent": self.employee, "document_name": "Civil ID"}))
		self.assertTrue(frappe.db.exists("Bank Account", result["bank_account"]))
		self.assertNotIn("bank_account", run("Complete PACI", doc))

	def test_a_damj_writes_the_original_civil_id(self):
		run("Complete PACI", a_paci(employee=self.employee, new_civil_id_expiry_date=today(), damj_is_applicable=1, original_civil_id="288888888888"))
		self.assertEqual(frappe.db.get_value("Employee", self.employee, "one_fm_civil_id"), "288888888888")
