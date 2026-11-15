# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Residency Lifecycle process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, now_datetime, today

SCRIPTS = {
	"Validate Residency Completion": """# Checks a Residency before the process completes it.
# Sets result["completion_valid"]; on False the process reopens the Pending by GR Operator task.
errors = []

if not doc.invoice_attachment:
	errors.append(frappe._("Upload Payment Invoice"))

# An Onboarding visa extension has no residency to update, only the visa expiry.
if doc.renewal_or_extend == "Visa Extension":
	if not doc.visa_extension_expiry_date:
		errors.append(frappe._("Visa Extension Expiry Date"))
elif not doc.new_residency_expiry_date:
	errors.append(frappe._("Updated Residency Expiry Date"))

if errors:
	frappe.msgprint(
		frappe._("Mandatory fields required in Residency form")
		+ "<ul>" + "".join("<li>{0}</li>".format(e) for e in errors) + "</ul>",
		title=frappe._("Cannot Complete"),
		indicator="red",
	)

# A residency opened by a Preparation completes only after its Medical Insurance.
pending = None
if doc.preparation and doc.employee and doc.category in ("Renewal", "First Time", "Transfer"):
	pending = frappe.db.get_value(
		"Medical Insurance",
		{"preparation": doc.preparation, "employee": doc.employee, "docstatus": ["!=", 2], "workflow_state": ["!=", "Completed"]},
		"name",
	)
	if pending:
		frappe.msgprint(
			frappe._("Medical Insurance {0} has to be completed first.").format(frappe.bold(pending)),
			title=frappe._("Out of Sequence"),
			indicator="red",
		)

result["completion_valid"] = not errors and not pending
""",
	"Complete Residency": """# Runs once the Residency is Completed. Records the new residency on the Employee, applies a
# Damj, and for a Transfer opens the PACI.
# Employee fields are written directly: a full Employee save re-validates unrelated data.
today = frappe.utils.today()
employee_updates = {}

# An Onboarding visa extension has no residency to record, only the visa expiry.
if doc.renewal_or_extend == "Visa Extension":
	employee_updates["custom_visa_extension_expiry_date"] = doc.visa_extension_expiry_date
else:
	if doc.renewal_or_extend == "Renewal Expat":
		employee_updates["custom_visa_extension_expiry_date"] = None
	employee_updates["residency_expiry_date"] = doc.new_residency_expiry_date
	values = {"attach": doc.residency_attachment, "issued_on": today, "valid_till": doc.new_residency_expiry_date}
	row = frappe.db.exists("Employee Document", {"parent": doc.employee, "parenttype": "Employee", "document_name": "Residency Expiry Attachment"})
	if row:
		frappe.db.set_value("Employee Document", row, values)
	else:
		last = frappe.db.get_value("Employee Document", {"parent": doc.employee, "parenttype": "Employee"}, "idx", order_by="idx desc") or 0
		frappe.get_doc({"doctype": "Employee Document", "parent": doc.employee, "parenttype": "Employee",
			"parentfield": "one_fm_employee_documents", "idx": last + 1, "document_name": "Residency Expiry Attachment", **values}).db_insert()

# A Damj merges two civil IDs; the original one survives, on the Employee, on this record
# and on the PACI opened by the same Preparation.
if doc.damj_is_applicable and doc.original_civil_id:
	employee_updates["one_fm_civil_id"] = doc.original_civil_id
	frappe.db.set_value("Residency", doc.name, "one_fm_civil_id", doc.original_civil_id)
	if doc.preparation:
		for name in frappe.get_all("PACI", filters={"preparation": doc.preparation, "employee": doc.employee, "docstatus": ["!=", 2]}, pluck="name"):
			frappe.db.set_value("PACI", name, "civil_id", doc.original_civil_id)

frappe.db.set_value("Employee", doc.employee, employee_updates)
frappe.db.set_value("Residency", doc.name, "completed_on", today)

# A Transfer residency opens the transfer PACI, unless one is already open this year.
if doc.category == "Transfer":
	open_paci = frappe.db.exists("PACI", {
		"employee": doc.employee, "category": "Transfer",
		"date_of_application": [">=", frappe.utils.get_year_start(today)],
		"workflow_state": ["!=", "Cancelled"], "docstatus": ["<", 2],
	})
	if not open_paci:
		paci = frappe.get_doc({"doctype": "PACI", "employee": doc.employee, "category": "Transfer", "date_of_application": today}).insert()
		result["transfer_paci"] = paci.name
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
		"context_doctype": "Residency",
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


def a_residency(**kw):
	doc = frappe.new_doc("Residency")
	doc.name = kw.pop("name", "MOI-PROCESSA-TEST-1")
	doc.update(kw)
	return doc


def an_employee(**filters):
	return frappe.get_all(
		"Employee",
		filters={"status": "Active", "relieving_date": ["is", "not set"], **filters},
		pluck="name", limit=1, order_by="creation desc",
	)[0]


class TestValidateResidencyCompletion(FrappeTestCase):
	def valid(self, doc):
		return run("Validate Residency Completion", doc)["completion_valid"]

	def test_needs_the_invoice_and_the_updated_expiry(self):
		doc = a_residency(renewal_or_extend="Renewal Expat", category="Renewal")
		self.assertFalse(self.valid(doc))
		doc.invoice_attachment = "/files/i.pdf"
		self.assertFalse(self.valid(doc))
		doc.new_residency_expiry_date = today()
		self.assertTrue(self.valid(doc))

	def test_a_visa_extension_completes_with_the_visa_date_alone(self):
		doc = a_residency(renewal_or_extend="Visa Extension", category="Extend", invoice_attachment="/files/i.pdf")
		self.assertFalse(self.valid(doc))
		doc.visa_extension_expiry_date = today()
		self.assertTrue(self.valid(doc))


class TestCompleteResidency(FrappeTestCase):
	def setUp(self):
		self.employee = an_employee()

	def test_a_renewal_records_the_expiry_and_clears_the_visa_date(self):
		frappe.db.set_value("Employee", self.employee, "custom_visa_extension_expiry_date", today())
		run("Complete Residency", a_residency(employee=self.employee, renewal_or_extend="Renewal Expat", category="Renewal", new_residency_expiry_date="2028-02-29"))
		emp = frappe.db.get_value("Employee", self.employee, ["residency_expiry_date", "custom_visa_extension_expiry_date"], as_dict=True)
		self.assertEqual(str(emp.residency_expiry_date), "2028-02-29")
		self.assertIsNone(emp.custom_visa_extension_expiry_date)
		self.assertTrue(frappe.db.exists("Employee Document", {"parent": self.employee, "document_name": "Residency Expiry Attachment"}))

	def test_a_visa_extension_writes_the_visa_date_and_leaves_the_residency_expiry(self):
		before = frappe.db.get_value("Employee", self.employee, "residency_expiry_date")
		run("Complete Residency", a_residency(employee=self.employee, renewal_or_extend="Visa Extension", category="Extend", visa_extension_expiry_date="2027-06-30"))
		emp = frappe.db.get_value("Employee", self.employee, ["residency_expiry_date", "custom_visa_extension_expiry_date"], as_dict=True)
		self.assertEqual(emp.residency_expiry_date, before)
		self.assertEqual(str(emp.custom_visa_extension_expiry_date), "2027-06-30")

	def test_a_damj_writes_the_original_civil_id(self):
		run("Complete Residency", a_residency(employee=self.employee, renewal_or_extend="Renewal Expat", category="Renewal",
			new_residency_expiry_date=today(), damj_is_applicable=1, original_civil_id="299999999999"))
		self.assertEqual(frappe.db.get_value("Employee", self.employee, "one_fm_civil_id"), "299999999999")
