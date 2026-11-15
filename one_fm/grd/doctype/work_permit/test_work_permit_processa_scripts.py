# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Work Permit Lifecycle process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, now_datetime, today

SCRIPTS = {
	"Validate Work Permit Step": """# Checks the action taken on the Work Permit task before the process moves the permit on.
# Sets result["step_valid"]; on False the process reopens the same task.
action = task_data.get("action")
state = doc.workflow_state
errors = []

PAM_REGISTRATION_TYPES = ("New Kuwaiti", "Local Transfer", "Renewal Kuwaiti", "Renewal Expat")


def require(fieldname, label):
	if not doc.get(fieldname):
		errors.append(frappe._(label))


def check_entering_gr_manager():
	if doc.work_permit_type == "Cancellation":
		require("reference_number_on_pam", "PAM Reference Number")
	elif doc.work_permit_type in PAM_REGISTRATION_TYPES:
		require("reference_number_on_pam_registration", "PAM Reference Number")


def check_completion():
	if doc.work_permit_type == "Cancellation":
		require("work_permit_cancellation", "Work Permit Cancellation")
	elif doc.work_permit_type == "New Kuwaiti":
		require("work_permit_registration", "Work Permit Registration")
	elif doc.work_permit_type == "Local Transfer":
		require("new_work_permit_expiry_date", "Updated Work Permit Expiry Date")


if state == "Apply Online by GR Operator" and action == "Apply":
	check_entering_gr_manager()

elif state == "Pending GR Manager" and action in ("Accept", "Reject"):
	# An amended permit has to say which PAM designation it is now for.
	if frappe.utils.cint(doc.amendment_no):
		require("pam_designation", "PAM Designation")

elif state == "Pending By PAM" and action == "Accept":
	# An amended permit is fee-exempt, so it owes no second invoice.
	if not frappe.utils.cint(doc.amendment_no):
		require("attach_invoice", "Upload Payment Invoice")
	require("new_work_permit_expiry_date", "Updated Work Permit Expiry Date")
	if doc.work_permit_type != "Local Transfer":
		check_completion()

elif state == "Pending By PAM" and action == "Amend":
	check_entering_gr_manager()

elif state == "Pending By PAM" and action == "Reject":
	require("pam_rejection_reason", "PAM Rejection Reason")
	if not errors:
		frappe.db.set_value("Work Permit", doc.name, "reason_of_rejection", "Rejected by PAM")

elif state == "Pending By Previous Company" and action == "Reject":
	require("previous_company_rejection_reason", "Previous Company Rejection Reason")
	if not errors:
		frappe.db.set_value("Work Permit", doc.name, "reason_of_rejection", "Rejected by previous company")

elif state == "Pending by GR Operator" and action == "Done":
	check_completion()

result["step_valid"] = not errors
if errors:
	frappe.msgprint(
		frappe._("Fill in these fields before you take the {0} action:").format(frappe.bold(action))
		+ "<ul>" + "".join("<li>{0}</li>".format(e) for e in errors) + "</ul>",
		title=frappe._("Missing Information"),
		indicator="red",
	)
""",
	"Count Work Permit Amendment": """# PAM handed the permit back to be amended. The permit stays the same record; Amendment No
# says how many times it has been through.
frappe.db.set_value("Work Permit", doc.name, "amendment_no", frappe.utils.cint(doc.amendment_no) + 1)
""",
	"Complete Work Permit": """# Runs once the Work Permit is Completed. Records the permit on the Employee and on the
# documents opened beside it, and for a Local Transfer closes the Transfer Paper and opens
# the transfer Medical Insurance.
# Employee fields are written directly: a full Employee save re-validates unrelated data,
# and the GR Operator has no write access to Employee.
cint = frappe.utils.cint
today = frappe.utils.today()
emp = frappe.db.get_value(
	"Employee", doc.employee,
	["one_fm_pam_designation", "pam_file", "work_permit_salary", "under_company_residency", "employee_id", "employment_type"],
	as_dict=True,
)
updates = {}

# New PAM details
if doc.new_pam_designation and doc.new_pam_designation != emp.one_fm_pam_designation:
	updates["one_fm_pam_designation"] = doc.new_pam_designation
if doc.new_pam_file and doc.new_pam_file != emp.pam_file:
	updates["pam_file"] = doc.new_pam_file
if doc.new_work_permit_salary_ and doc.new_work_permit_salary_ != emp.work_permit_salary:
	updates["work_permit_salary"] = doc.new_work_permit_salary_

# Under company residency: on for a completed permit, off for a Cancellation, untouched for
# a Kuwaiti. The third-last character of the Employee ID carries the flag.
residency = None
if doc.work_permit_type == "Cancellation":
	residency = 0
elif doc.work_permit_type not in ("Renewal Kuwaiti", "New Kuwaiti"):
	residency = 1
if residency is not None and cint(emp.under_company_residency) != residency:
	updates["under_company_residency"] = residency
	if emp.employee_id:
		subcontract = frappe.db.exists("Onboard Subcontract Employee", {"employee": doc.employee}) or (
			emp.employment_type and emp.employment_type == frappe.db.get_single_value("Hiring Settings", "subcontract_employment_type")
		)
		digit = "S" if subcontract else str(residency)
		updates["employee_id"] = emp.employee_id[:-3] + digit + emp.employee_id[-2:]

# Passport details recorded on the permit
for source, target in (
	("new_passport_type", "one_fm_passport_type"),
	("new_passport_number", "passport_number"),
	("new_passport_expiry_date", "valid_upto"),
	("new_passport_issuance_date", "date_of_issue"),
):
	if doc.get(source):
		updates[target] = doc.get(source)

expiry = doc.new_work_permit_expiry_date
if expiry and doc.work_permit_type not in ("Cancellation", "New Kuwaiti"):
	updates["work_permit_expiry_date"] = expiry

if updates:
	frappe.db.set_value("Employee", doc.employee, updates)

# Carry a new PAM designation and salary onto the forms still open for this employee.
open_updates = {
	"Work Permit": {"pam_designation": updates.get("one_fm_pam_designation"), "work_permit_salary": updates.get("work_permit_salary")},
	"Residency": {"pam_designation": updates.get("one_fm_pam_designation")},
	"PACI": {"pam_designation": updates.get("one_fm_pam_designation")},
}
for doctype, values in open_updates.items():
	values = {k: v for k, v in values.items() if v}
	if not values:
		continue
	for name in frappe.get_all(doctype, filters=[["employee", "=", doc.employee], ["docstatus", "=", 0], ["workflow_state", "!=", "Cancelled"]], pluck="name"):
		frappe.db.set_value(doctype, name, values, update_modified=False)

# The Residency and PACI opened by the same Preparation run with the permit's expiry.
if expiry and doc.preparation and doc.work_permit_type not in ("Cancellation", "New Kuwaiti"):
	for doctype, fieldname in (("Residency", "new_residency_expiry_date"), ("PACI", "new_civil_id_expiry_date")):
		for name in frappe.get_all(doctype, filters={"preparation": doc.preparation, "employee": doc.employee, "docstatus": ["!=", 2]}, pluck="name"):
			frappe.db.set_value(doctype, name, fieldname, expiry)

if doc.work_permit_type == "Local Transfer":
	# The Work Permit scan, when the operator has it, goes on the Employee's documents.
	if doc.attach_work_permit:
		if not frappe.db.exists("Recruitment Document Required", "Work Permit"):
			frappe.get_doc({"doctype": "Recruitment Document Required", "recruitment_document": "Work Permit"}).insert()
		values = {"attach": doc.attach_work_permit, "issued_on": today, "valid_till": expiry}
		row = frappe.db.exists("Employee Document", {"parent": doc.employee, "parenttype": "Employee", "document_name": "Work Permit"})
		if row:
			frappe.db.set_value("Employee Document", row, values)
		else:
			last = frappe.db.get_value("Employee Document", {"parent": doc.employee, "parenttype": "Employee"}, "idx", order_by="idx desc") or 0
			frappe.get_doc({"doctype": "Employee Document", "parent": doc.employee, "parenttype": "Employee",
				"parentfield": "one_fm_employee_documents", "idx": last + 1, "document_name": "Work Permit", **values}).db_insert()

	# List the permit in the Transfer Paper it came from, and close the Transfer Paper.
	if doc.transfer_paper:
		if not frappe.db.exists("Transfer Work Permit", {"parent": doc.transfer_paper, "work_permit_reference": doc.name}):
			last = frappe.db.get_value("Transfer Work Permit", {"parent": doc.transfer_paper}, "idx", order_by="idx desc") or 0
			frappe.get_doc({
				"doctype": "Transfer Work Permit", "parent": doc.transfer_paper, "parenttype": "Transfer Paper",
				"parentfield": "work_permit_records", "idx": last + 1, "work_permit_reference": doc.name,
			}).db_insert()
		frappe.db.set_value("Transfer Paper", doc.transfer_paper, "workflow_state", "Completed")

	# Open the transfer Medical Insurance, unless one is already open this year.
	open_policy = frappe.db.exists("Medical Insurance", {
		"employee": doc.employee, "insurance_status": "Local Transfer",
		"date_of_application": [">=", frappe.utils.get_year_start(today)],
		"workflow_state": ["!=", "Cancelled"], "docstatus": ["<", 2],
	})
	if not open_policy:
		policy = frappe.get_doc({
			"doctype": "Medical Insurance", "insurance_status": "Local Transfer", "date_of_application": today,
			"work_permit": doc.name, "preparation": doc.preparation, "passport_expiry_date": doc.passport_expiry_date,
			"employee_id": doc.employee_id, "employee": doc.employee,
		}).insert()
		result["transfer_medical_insurance"] = policy.name
""",
	"Record Work Permit Rejection": """# Runs once the Work Permit is Rejected. A rejected Local Transfer is listed, with its reason,
# in the Work Permit table of the Transfer Paper it came from.
if doc.work_permit_type == "Local Transfer" and doc.transfer_paper:
	row = frappe.db.get_value("Transfer Work Permit", {"parent": doc.transfer_paper, "work_permit_reference": doc.name}, "name")
	if row:
		frappe.db.set_value("Transfer Work Permit", row, "reason_of_rejection", doc.reason_of_rejection)
	else:
		last = frappe.db.get_value("Transfer Work Permit", {"parent": doc.transfer_paper}, "idx", order_by="idx desc") or 0
		frappe.get_doc({
			"doctype": "Transfer Work Permit", "parent": doc.transfer_paper, "parenttype": "Transfer Paper",
			"parentfield": "work_permit_records", "idx": last + 1,
			"work_permit_reference": doc.name, "reason_of_rejection": doc.reason_of_rejection,
		}).db_insert()
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
		"context_doctype": "Work Permit",
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


def permit(**kw):
	doc = frappe.new_doc("Work Permit")
	doc.name = kw.pop("name", "WP-PROCESSA-TEST-1")
	doc.update({"work_permit_type": "Renewal Expat", "amendment_no": 0, **kw})
	return doc


def an_employee(**filters):
	return frappe.get_all(
		"Employee",
		filters={"status": "Active", "relieving_date": ["is", "not set"], "employee_id": ["is", "set"], **filters},
		pluck="name", limit=1, order_by="creation desc",
	)[0]


class TestValidateWorkPermitStep(FrappeTestCase):
	def valid(self, doc, action):
		return run("Validate Work Permit Step", doc, action=action)["step_valid"]

	def test_apply_needs_the_pam_reference_for_the_permit_type(self):
		doc = permit(workflow_state="Apply Online by GR Operator")
		self.assertFalse(self.valid(doc, "Apply"))
		doc.reference_number_on_pam_registration = "PAM-1"
		self.assertTrue(self.valid(doc, "Apply"))

	def test_a_cancellation_needs_the_cancellation_reference(self):
		doc = permit(workflow_state="Apply Online by GR Operator", work_permit_type="Cancellation", reference_number_on_pam_registration="PAM-1")
		self.assertFalse(self.valid(doc, "Apply"))
		doc.reference_number_on_pam = "PAM-2"
		self.assertTrue(self.valid(doc, "Apply"))

	def test_an_amended_permit_needs_a_pam_designation(self):
		doc = permit(workflow_state="Pending GR Manager")
		self.assertTrue(self.valid(doc, "Accept"))
		doc.amendment_no = 1
		self.assertFalse(self.valid(doc, "Accept"))
		self.assertFalse(self.valid(doc, "Reject"))

	def test_pam_accept_needs_the_invoice_and_the_expiry(self):
		doc = permit(workflow_state="Pending By PAM", new_work_permit_expiry_date=today())
		self.assertFalse(self.valid(doc, "Accept"))
		doc.attach_invoice = "/files/invoice.pdf"
		self.assertTrue(self.valid(doc, "Accept"))
		doc.new_work_permit_expiry_date = None
		self.assertFalse(self.valid(doc, "Accept"))

	def test_an_amended_permit_owes_no_invoice(self):
		doc = permit(workflow_state="Pending By PAM", new_work_permit_expiry_date=today(), amendment_no=2)
		self.assertTrue(self.valid(doc, "Accept"))

	def test_completing_a_new_kuwaiti_needs_the_registration(self):
		doc = permit(workflow_state="Pending By PAM", work_permit_type="New Kuwaiti", attach_invoice="/files/i.pdf", new_work_permit_expiry_date=today())
		self.assertFalse(self.valid(doc, "Accept"))
		doc.work_permit_registration = "/files/r.pdf"
		self.assertTrue(self.valid(doc, "Accept"))

	def test_amend_needs_nothing_paid(self):
		doc = permit(workflow_state="Pending By PAM", reference_number_on_pam_registration="PAM-1")
		self.assertTrue(self.valid(doc, "Amend"))

	def test_a_rejection_needs_its_reason(self):
		doc = permit(workflow_state="Pending By PAM")
		self.assertFalse(self.valid(doc, "Reject"))
		doc.pam_rejection_reason = "Gender"
		self.assertTrue(self.valid(doc, "Reject"))
		doc = permit(workflow_state="Pending By Previous Company", work_permit_type="Local Transfer")
		self.assertFalse(self.valid(doc, "Reject"))
		doc.previous_company_rejection_reason = "Previous Sponsor Rejected"
		self.assertTrue(self.valid(doc, "Reject"))

	def test_a_local_transfer_completes_with_the_updated_expiry(self):
		doc = permit(workflow_state="Pending by GR Operator", work_permit_type="Local Transfer")
		self.assertFalse(self.valid(doc, "Done"))
		doc.new_work_permit_expiry_date = today()
		self.assertTrue(self.valid(doc, "Done"))


class TestCompleteWorkPermit(FrappeTestCase):
	def setUp(self):
		self.employee = an_employee()

	def complete(self, **kw):
		doc = permit(employee=self.employee, workflow_state="Completed", **kw)
		run("Complete Work Permit", doc)
		return frappe.db.get_value("Employee", self.employee, ["under_company_residency", "employee_id", "work_permit_expiry_date", "passport_number"], as_dict=True)

	def test_a_renewal_puts_the_employee_under_residency_and_records_the_expiry(self):
		frappe.db.set_value("Employee", self.employee, "under_company_residency", 0)
		emp = self.complete(new_work_permit_expiry_date="2028-01-31", new_passport_number="P123")
		self.assertEqual(emp.under_company_residency, 1)
		self.assertIn(emp.employee_id[-3], ("1", "S"))
		self.assertEqual(str(emp.work_permit_expiry_date), "2028-01-31")
		self.assertEqual(emp.passport_number, "P123")

	def test_a_cancellation_takes_the_employee_out_of_residency(self):
		frappe.db.set_value("Employee", self.employee, "under_company_residency", 1)
		before = frappe.db.get_value("Employee", self.employee, "work_permit_expiry_date")
		emp = self.complete(work_permit_type="Cancellation", new_work_permit_expiry_date="2028-01-31")
		self.assertEqual(emp.under_company_residency, 0)
		self.assertEqual(emp.work_permit_expiry_date, before)

	def test_a_kuwaiti_permit_leaves_the_flag_alone(self):
		frappe.db.set_value("Employee", self.employee, "under_company_residency", 0)
		emp = self.complete(work_permit_type="Renewal Kuwaiti")
		self.assertEqual(emp.under_company_residency, 0)


class TestCountWorkPermitAmendment(FrappeTestCase):
	def test_each_amendment_adds_one(self):
		name = frappe.db.get_value("Work Permit", {"docstatus": 0}, "name")
		frappe.db.set_value("Work Permit", name, "amendment_no", 1)
		run("Count Work Permit Amendment", frappe.get_doc("Work Permit", name))
		self.assertEqual(frappe.db.get_value("Work Permit", name, "amendment_no"), 2)
