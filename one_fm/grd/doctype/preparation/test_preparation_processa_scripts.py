# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Preparation Lifecycle process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, now_datetime, today

SCRIPTS = {
	"Validate Preparation Submission": """# Checks every row of a Preparation before the process submits it.
# Sets result["submission_valid"]; on False the process reopens the Submit task.
errors = []
active = set(frappe.get_all("Employee", filters={"status": "Active", "name": ["in", [r.employee for r in doc.preparation_record if r.employee]]}, pluck="name"))

for row in doc.preparation_record:
	if not row.renewal_or_extend:
		errors.append(frappe._("Fill the Renewal or Extend field for row number {0}").format(row.idx))
	if row.employee not in active:
		errors.append(frappe._("The Employee in row {0} {1} is not Active at the moment").format(row.idx, frappe.bold(row.full_name or row.employee)))

result["submission_valid"] = not errors
if errors:
	frappe.msgprint(
		frappe._("Mandatory fields required in Preparation to Submit")
		+ "<ul>" + "".join("<li>{0}</li>".format(e) for e in errors) + "</ul>",
		title=frappe._("Cannot Submit"),
		indicator="red",
	)
""",
	"Create Preparation Documents": """# Runs once the Preparation is Submitted. Opens the legal documents each row's Action calls
# for, then tells the GRD Operator and sends the costing to HR.
# One row's failure does not stop the rest: the rows that failed are listed to the submitter.
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

add_days = frappe.utils.add_days
today = frappe.utils.today()

# What each first-application Action opens, and under which classification.
NEW_ACTION_DOCUMENTS = {
	"New Kuwaiti": {"work_permit": "New Kuwaiti"},
	"Overseas": {"work_permit": "Overseas", "medical_insurance": "New", "residency": "First Time",
		"paci": "New Application", "medical_appointment": "First Time", "pcc_attestation": "Overseas"},
	"Overseas (Government)": {"work_permit": "Overseas (Government)", "medical_insurance": "New", "residency": "First Time",
		"paci": "New Application", "medical_appointment": "First Time", "pcc_attestation": "Overseas (Government)"},
	"Local Transfer": {"work_permit": "Local Transfer", "medical_insurance": "Local Transfer", "residency": "Transfer", "paci": "Transfer"},
}
# The Residency category an Action opens, and how many days before the residency expires it
# is applied for. Anything not listed is an extension, applied for a week ahead.
RESIDENCY_BY_ACTION = {
	"Renewal Expat": ("Renewal", -14), "Transfer": ("Transfer", None), "Local Transfer": ("Transfer", None),
	"Overseas": ("First Time", None), "Overseas (Government)": ("First Time", None), "Visa Extension": ("Extend", None),
}
# Actions whose Residency is opened by the renewal or first-application branches below.
HANDLED_ACTIONS = ("Renewal Expat", "New Kuwaiti", "Overseas", "Overseas (Government)", "Local Transfer")
RENEWAL_ACTIONS = ("Renewal Expat", "Renewal (Kuwaiti)")


failures = []


# Insert one document. A failure is logged and listed, and the row's other documents still open.
def insert(values, **kwargs):
	try:
		return frappe.get_doc(values).insert(**kwargs)
	except Exception as e:
		frappe.log_error(title="Preparation {0}: {1} not created for {2}".format(doc.name, values["doctype"], values.get("employee")))
		failures.append((values.get("employee"), CURRENT_ROW["name"], values["doctype"], frappe.utils.strip_html(str(e))))


def open_residency(employee, action, category=None):
	mapped, days = RESIDENCY_BY_ACTION.get(action, ("Extend", -7))
	return insert({
		"doctype": "Residency", "employee": employee.name, "preparation": doc.name, "renewal_or_extend": action,
		"category": category or mapped,
		"date_of_application": add_days(employee.residency_expiry_date, days) if days else today,
	})


def open_paci(employee, category):
	return insert({
		"doctype": "PACI", "employee": employee.name, "category": category, "preparation": doc.name,
		"date_of_application": add_days(employee.residency_expiry_date, -14) if category == "Renewal" else today,
	})


def open_medical_insurance(permit, status):
	return insert({
		"doctype": "Medical Insurance", "insurance_status": status, "work_permit": permit.name, "preparation": doc.name,
		"date_of_application": today if status == "Local Transfer" else permit.date_of_application,
		"passport_expiry_date": permit.passport_expiry_date, "employee_id": permit.employee_id, "employee": permit.employee,
	})


def open_documents(row, employee):
	action = row.renewal_or_extend
	expat = row.nationality != "Kuwaiti"

	if action in RENEWAL_ACTIONS:
		values = {
			"employee": employee.name, "preparation": doc.name, "ref_doctype": "Preparation", "ref_name": doc.name,
			"work_permit_type": "Renewal Kuwaiti" if employee.one_fm_nationality == "Kuwaiti" else "Renewal Expat",
			"date_of_application": add_days(employee.residency_expiry_date, -14), "transfer_paper": None,
		}
		if employee.work_permit:
			# A renewal carries forward the employee's current permit.
			previous = frappe.copy_doc(frappe.get_doc("Work Permit", employee.work_permit)).as_dict()
			permit = insert({**previous, **values, "doctype": "Work Permit"})
		else:
			permit = insert({"doctype": "Work Permit", **values})
		if action == "Renewal Expat" and expat:
			if permit:
				open_medical_insurance(permit, "Renewal")
			open_residency(employee, action)
			open_paci(employee, "Renewal")

	# An extension opens a Residency and nothing else.
	if action not in HANDLED_ACTIONS and expat:
		open_residency(employee, action)

	if action in NEW_ACTION_DOCUMENTS:
		plan = NEW_ACTION_DOCUMENTS[action]
		# The Work Permit first: the Medical Insurance is opened against it.
		permit = insert({"doctype": "Work Permit", "employee": employee.name, "work_permit_type": plan["work_permit"],
			"date_of_application": today, "preparation": doc.name, "ref_doctype": "Preparation", "ref_name": doc.name})
		if "medical_insurance" in plan and permit:
			open_medical_insurance(permit, plan["medical_insurance"])
		if "residency" in plan:
			open_residency(employee, action, plan["residency"])
		if "paci" in plan:
			open_paci(employee, plan["paci"])
		if "medical_appointment" in plan:
			# Opened without its mandatory fields: the appointment date, transport and PRO are not known yet.
			insert({"doctype": "Medical Appointment", "employee": employee.name, "medical_appointment_type": plan["medical_appointment"],
				"preparation": doc.name, "date_of_application": today}, ignore_mandatory=True)
		if "pcc_attestation" in plan:
			rule = None
			for r in frappe.get_cached_doc("HR Settings").get("nationality_attestation_rules") or []:
				if r.nationality == employee.one_fm_nationality:
					rule = r
			kinds = ["Attestation"] + (["Translation"] if rule and rule.translation_required else [])
			for kind in kinds:
				insert({"doctype": "PCC Attestation", "employee": employee.name, "type": kind, "category": plan["pcc_attestation"], "preparation": doc.name})


frappe.db.set_value("Preparation", doc.name, {"submitted_by": doc.modified_by, "submitted_on": frappe.utils.now_datetime()})

CURRENT_ROW = {}
for row in doc.preparation_record:
	CURRENT_ROW["name"] = row.full_name
	try:
		open_documents(row, frappe.get_doc("Employee", row.employee))
	except Exception as e:
		frappe.log_error(title="Preparation {0}: documents not created for {1}".format(doc.name, row.employee))
		failures.append((row.employee, row.full_name, row.renewal_or_extend, frappe.utils.strip_html(str(e))))

if failures:
	esc = frappe.utils.escape_html
	frappe.msgprint(
		"<p>" + frappe._("This Preparation was submitted, but the following documents could not be created. "
			"Correct the cause and open them from the employee's record, or amend the row's Action.") + "</p>"
		+ "<table class='table table-bordered table-sm small'><thead><tr><th>" + frappe._("Employee") + "</th><th>" + frappe._("Name")
		+ "</th><th>" + frappe._("Document") + "</th><th>" + frappe._("Reason") + "</th></tr></thead><tbody>"
		+ "".join("<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td></tr>".format(*[esc(frappe.utils.cstr(v)) for v in f]) for f in failures)
		+ "</tbody></table>",
		title=frappe._("Documents Not Created"), indicator="red", wide=True,
	)
result["documents_not_created"] = len(failures)

if doc.grd_operator:
	enqueue_create_notification(doc.grd_operator, {
		"subject": frappe._("Records are created for WP, MI, MOI, PACI, and FP"),
		"email_content": "<p>" + frappe._("Records are created") + " <a href='{0}'>{1}</a>.</p>".format(frappe.utils.get_url_to_form("Preparation", doc.name), doc.name),
		"document_type": "Preparation", "document_name": doc.name, "from_user": doc.modified_by, "type": "Alert",
	})

# The costing mail renders a PDF; it is queued after the commit so a broken PDF cannot undo the submit.
frappe.enqueue("one_fm.grd.doctype.preparation.preparation.send_costing_notification", queue="short", enqueue_after_commit=True, preparation=doc.name)
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
		"context_doctype": "Preparation",
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


class TestValidatePreparationSubmission(FrappeTestCase):
	def test_every_row_needs_its_action_and_an_active_employee(self):
		active = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		left = frappe.db.get_value("Employee", {"status": "Left"}, "name")
		doc = frappe.new_doc("Preparation")
		doc.name = "PRE-PROCESSA-TEST-1"
		doc.append("preparation_record", {"employee": active})
		self.assertFalse(run("Validate Preparation Submission", doc)["submission_valid"])
		doc.preparation_record[0].renewal_or_extend = "Renewal Expat"
		self.assertTrue(run("Validate Preparation Submission", doc)["submission_valid"])
		if left:
			doc.append("preparation_record", {"employee": left, "renewal_or_extend": "Renewal Expat"})
			self.assertFalse(run("Validate Preparation Submission", doc)["submission_valid"])


class TestCreatePreparationDocuments(FrappeTestCase):
	def employee(self):
		return frappe.get_all(
			"Employee",
			filters={"status": "Active", "relieving_date": ["is", "not set"], "one_fm_nationality": ["!=", "Kuwaiti"],
				"residency_expiry_date": ["is", "set"], "work_permit": ["is", "not set"]},
			fields=["name", "one_fm_nationality"], limit=1, order_by="creation desc",
		)[0]

	def batch(self, action, employee):
		doc = frappe.new_doc("Preparation")
		# FrappeTestCase rolls back per class, so each batch needs its own name.
		self.batch_name = "PRE-PROCESSA-TEST-" + frappe.generate_hash(length=6)
		doc.update({"category": "Renewal", "name": self.batch_name, "modified_by": "Administrator"})
		doc.append("preparation_record", {"employee": employee.name, "renewal_or_extend": action, "nationality": employee.one_fm_nationality, "full_name": "X"})
		# The documents link to the batch, so it has to exist.
		doc.db_insert()
		doc.preparation_record[0].db_insert()
		return doc

	def opened(self, employee):
		return {dt: frappe.db.count(dt, {"preparation": self.batch_name, "employee": employee.name})
			for dt in ("Work Permit", "Medical Insurance", "Residency", "PACI")}

	def test_an_expat_renewal_opens_all_four(self):
		employee = self.employee()
		with patch("frappe.enqueue"), patch("frappe.desk.doctype.notification_log.notification_log.enqueue_create_notification"):
			result = run("Create Preparation Documents", self.batch("Renewal Expat", employee))
		self.assertEqual(result["documents_not_created"], 0)
		self.assertEqual(self.opened(employee), {"Work Permit": 1, "Medical Insurance": 1, "Residency": 1, "PACI": 1})

	def test_an_extension_opens_only_a_residency(self):
		employee = self.employee()
		with patch("frappe.enqueue"), patch("frappe.desk.doctype.notification_log.notification_log.enqueue_create_notification"):
			run("Create Preparation Documents", self.batch("Extension", employee))
		self.assertEqual(self.opened(employee), {"Work Permit": 0, "Medical Insurance": 0, "Residency": 1, "PACI": 0})

	def test_a_document_that_cannot_open_is_listed_and_the_rest_still_open(self):
		employee = self.employee()
		real_insert = frappe.model.document.Document.insert

		def refuse_work_permits(self, *args, **kwargs):
			if self.doctype == "Work Permit":
				raise frappe.ValidationError("no permit")
			return real_insert(self, *args, **kwargs)

		with patch("frappe.enqueue"), patch("frappe.desk.doctype.notification_log.notification_log.enqueue_create_notification"), \
				patch.object(frappe.model.document.Document, "insert", refuse_work_permits), patch("frappe.log_error"):
			result = run("Create Preparation Documents", self.batch("Renewal Expat", employee))
		self.assertEqual(result["documents_not_created"], 1)
		self.assertEqual(self.opened(employee)["Residency"], 1)
