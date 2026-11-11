# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the PIFSS Monthly Deduction processes run as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime, today

from one_fm.one_fm import processa_rules

SCRIPTS = {
	"Link PIFSS Monthly Deduction Reports": """# Runs when the deduction is created. Points the File records of the two attached CSV
# reports at this deduction.
if doc.attach_report and doc.additional_attach_report:
	for url in (doc.attach_report, doc.additional_attach_report):
		file_name = frappe.db.get_value("File", {"file_url": url}, "name")
		if file_name:
			frappe.db.set_value("File", file_name, "attached_to_name", doc.name)
""",
	"Assign PIFSS Monthly Deduction Step": """# Opens the next step to every holder of the role the Workflow allowed to act on it.
result["assigned_user"] = ""
result["assigned_role"] = {
	"Draft": "Government Relations Operator",
	"Pending By Supervisor": "GRD Supervisor",
	"Pending By Finance": "Finance User",
}.get(doc.workflow_state, "")
""",
	"Import PIFSS Monthly Deduction Data": """# Runs on Fetch Data. Reads the attached PIFSS CSV into the deductions table, one row per
# line, matched to an Employee by Civil ID. Nothing is written when a matched employee has
# no Salary Structure Assignment.
import csv
import io

errors = []
rows = []
if not doc.attach_report:
	errors.append(frappe._("Attach the Monthly Deduction Report first."))
else:
	content = frappe.get_doc("File", {"file_url": doc.attach_report}).get_content()
	if isinstance(content, bytes):
		content = content.decode("utf-8-sig")
	missing_salary_structure = []
	for line in list(csv.reader(io.StringIO(content)))[1:]:
		if not line or not line[0].strip():
			continue
		civil_id = line[0].strip()
		employee = frappe.db.get_value("Employee", {"one_fm_civil_id": civil_id}, ["name", "pifss_id_no", "one_fm_civil_id"], as_dict=True)
		if employee and not frappe.db.exists("Salary Structure Assignment", {"employee": employee.name}):
			missing_salary_structure.append(employee.name)
		rows.append({
			"employee": employee.name if employee else "", "pifss_id_no": employee.pifss_id_no if employee else "",
			"civil_id": employee.one_fm_civil_id if employee else civil_id, "employee_name_in_arabic": line[1],
			"actual_salary": frappe.utils.flt(line[2]), "social_security_salary": frappe.utils.flt(line[3]),
			"employee_contribution": frappe.utils.flt(line[4]), "company_contribution": frappe.utils.flt(line[5]),
			"total_contribution": frappe.utils.flt(line[6]),
		})
	if missing_salary_structure:
		errors.append(frappe._("There is no Salary Structure assigned to the following employees:") + "<br><br>"
			+ "".join("<ul><li>{0}</li></ul>".format(e) for e in missing_salary_structure))

if not errors:
	frappe.db.delete("PIFSS Monthly Deduction Employees", {"parent": doc.name, "parenttype": "PIFSS Monthly Deduction"})
	now = frappe.utils.now_datetime()
	for idx, values in enumerate(rows, 1):
		row = frappe.get_doc({
			"doctype": "PIFSS Monthly Deduction Employees", "parent": doc.name, "parenttype": "PIFSS Monthly Deduction",
			"parentfield": "deductions", "idx": idx, "name": frappe.generate_hash(length=10), "owner": frappe.session.user,
			"modified_by": frappe.session.user, "creation": now, "modified": now, **values,
		})
		row.db_insert()
	frappe.msgprint(frappe._("{0} rows fetched.").format(len(rows)), indicator="green")

result["import_valid"] = not errors
for e in errors:
	frappe.msgprint(e, title=frappe._("Cannot Fetch Data"), indicator="red")
""",
	"Calculate PIFSS Monthly Deduction Totals": """# The deduction's totals. Every save runs recount() through the controller; in the map it
# runs after Fetch Data.
CSV_FIELDS = ("total_sub", "total_additional_deduction", "basic_insurance_in_csv", "supplementary_insurance_in_csv",
	"fund_increase_in_csv", "unemployment_insurance_in_csv", "compensation_in_csv")
TOTAL_FIELDS = ("total_contribution", "company_contribution", "employee_contribution")


def recount(doc):
	# Clears the imported rows once the report is removed, and sums the contributions.
	if not doc.attach_report:
		doc.set("deductions", [])
		for field in CSV_FIELDS:
			if doc.meta.has_field(field):
				doc.set(field, 0)
	for field in TOTAL_FIELDS:
		doc.set(field, sum(frappe.utils.flt(row.get(field)) for row in doc.deductions))


if bpmn_id:
	recount(doc)
	frappe.db.set_value("PIFSS Monthly Deduction", doc.name, {field: doc.get(field) for field in TOTAL_FIELDS})
""",
	"Validate PIFSS Monthly Deduction Step": """# Checks the deduction before the process moves it on. Submitting to the supervisor needs
# the report; Done needs an employee on every row and no Additional Salary already made
# from this deduction. Sets result["step_valid"]; on False the process reopens the same task.
errors = []
if doc.workflow_state == "Draft" and not doc.attach_report:
	errors.append(frappe._(
		"<b>First, Scan the Manual Report and Download csv files from <a href=\\"{0}\\" target=\\"_blank\\">PIFSS Website</a></b>"
		"<br>Mandatory fields required in PIFSS Monthly Deduction <br><br><ul><li>Attach Monthly Deduction Report</li></ul>"
	).format(doc.pifss_website or ""))

if doc.workflow_state == "Pending By Finance":
	for row in doc.deductions:
		if not row.employee:
			errors.append(frappe._("No employee found for Civil ID {0} in deductions row {1}").format(row.civil_id, row.idx))
		elif frappe.db.exists("Additional Salary", {"pifss_monthly_deduction": doc.name, "employee": row.employee, "docstatus": ["<", 2]}):
			errors.append(frappe._("Row {0}, {1} already has an Additional Salary from this deduction.").format(row.idx, row.employee_name or row.employee))

result["step_valid"] = not errors
for e in errors:
	frappe.msgprint(e, title=frappe._("Cannot Continue"), indicator="red")
""",
	"Notify GRD Supervisor of PIFSS Monthly Deduction": """# Runs when the deduction reaches the GRD Supervisor. Carries the Total into Total Payment
# Required for finance and tells the Default GRD Supervisor in HR Settings.
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

if doc.total:
	frappe.db.set_value("PIFSS Monthly Deduction", doc.name, "total_payment_required", doc.total)

supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
if supervisor:
	enqueue_create_notification(supervisor, {
		"subject": frappe._("Attention: PIFSS Monthly Deduction Is Ready to Be Reviewed"),
		"email_content": "<p>You are requested to review PIFSS Monthly Deduction</p><br>",
		"document_type": doc.doctype, "document_name": doc.name, "from_user": doc.modified_by,
	})
""",
	"Notify Finance of PIFSS Monthly Deduction": """# Runs when the deduction reaches finance. Asks every Finance User, once, to transfer the
# Total Payment Required to the GRD account.
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.utils.user import get_users_with_role

subject = frappe._("PIFSS Monthly Deduction Payments for {0}").format(doc.name)
users = get_users_with_role("Finance User")
if users and not frappe.db.exists("Notification Log", {"subject": subject}):
	payment_request = frappe.db.get_value("Payment Request", {"reference_doctype": doc.doctype, "reference_name": doc.name}, "name")
	enqueue_create_notification(users, {
		"subject": subject,
		"email_content": frappe._("Kindly, prepare Total Payment Required Amount and transfer it to GRD account.<br>Please transfer it within 2 days."),
		"document_type": "Payment Request" if payment_request else doc.doctype,
		"document_name": payment_request or doc.name, "from_user": doc.modified_by,
	})
""",
	"Create PIFSS Additional Salaries": """# Runs when the deduction is Completed. Makes a submitted Social Security Additional Salary
# for each row's Employee Contribution. The payroll date is the deduction month, moved
# inside the employee's joining and relieving dates.
# Written directly: the GR Operator who created the deduction cannot create Additional Salary.
company = frappe.defaults.get_global_default("company")
currency = frappe.get_cached_value("Company", company, "default_currency")
component_type = frappe.db.get_value("Salary Component", "Social Security", "type")
now = frappe.utils.now_datetime()
created = []
for row in doc.deductions:
	if not row.employee or frappe.db.exists("Additional Salary", {"pifss_monthly_deduction": doc.name, "employee": row.employee, "docstatus": ["<", 2]}):
		continue
	employee = frappe.db.get_value("Employee", row.employee, ["employee_name", "department", "date_of_joining", "relieving_date"], as_dict=True)
	payroll_date = frappe.utils.getdate(doc.deduction_month)
	if employee.date_of_joining and frappe.utils.getdate(employee.date_of_joining) > payroll_date:
		payroll_date = employee.date_of_joining
	if employee.relieving_date and frappe.utils.getdate(employee.relieving_date) < payroll_date:
		payroll_date = employee.relieving_date
	additional_salary = frappe.get_doc({
		"doctype": "Additional Salary", "naming_series": "HR-ADS-.YY.-.MM.-", "employee": row.employee,
		"employee_name": employee.employee_name, "department": employee.department, "company": company,
		"currency": currency, "salary_component": "Social Security", "type": component_type,
		"amount": row.employee_contribution, "overwrite_salary_structure_amount": 1, "notes": "Social Security Deduction",
		"pifss_monthly_deduction": doc.name, "payroll_date": payroll_date, "docstatus": 1,
		"owner": frappe.session.user, "modified_by": frappe.session.user, "creation": now, "modified": now,
	})
	additional_salary.set_new_name()
	additional_salary.db_insert()
	created.append(additional_salary.name)

result["additional_salaries"] = created
frappe.msgprint(frappe._("Additional Salaries have been created."))
""",
	"Create PIFSS Monthly Deduction": """# On the 1st of each month at 04:15. Creates this month's deduction and tells the Default
# GRD Operator PIFSS in HR Settings. Skips a month that already has one.
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

month = frappe.utils.get_first_day(frappe.utils.nowdate())
if not frappe.db.exists("PIFSS Monthly Deduction", {"deduction_month": month}):
	deduction = frappe.new_doc("PIFSS Monthly Deduction")
	deduction.deduction_month = month
	deduction.insert()
	result["pifss_monthly_deduction"] = deduction.name
	operator = frappe.db.get_single_value("HR Settings", "default_grd_operator_pifss")
	if operator:
		enqueue_create_notification(operator, {
			"subject": frappe._("PIFSS Monthly Deduction record is created"),
			"email_content": frappe._("PIFSS Monthly Deduction record is created: {0}").format(frappe.utils.get_url(deduction.get_url())),
			"document_type": deduction.doctype, "document_name": deduction.name,
		})
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
		"context_doctype": "PIFSS Monthly Deduction",
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


def deduction(**kw):
	doc = frappe.new_doc("PIFSS Monthly Deduction")
	doc.name = kw.pop("name", "PMD-PROCESSA-TEST-1")
	doc.update(kw)
	return doc


class TestValidatePIFSSMonthlyDeductionStep(FrappeTestCase):
	def valid(self, doc):
		return run("Validate PIFSS Monthly Deduction Step", doc)["step_valid"]

	def test_leaving_draft_needs_the_report(self):
		self.assertFalse(self.valid(deduction(workflow_state="Draft")))
		self.assertTrue(self.valid(deduction(workflow_state="Draft", attach_report="/files/pifss.csv")))

	def test_done_needs_an_employee_on_every_row(self):
		doc = deduction(workflow_state="Pending By Finance")
		doc.append("deductions", {"civil_id": "000000000000"})
		self.assertFalse(self.valid(doc))
		doc.deductions[0].employee = frappe.db.get_value("Employee", {}, "name")
		self.assertTrue(self.valid(doc))


class TestPIFSSMonthlyDeductionTotals(FrappeTestCase):
	def test_recount_sums_the_rows(self):
		doc = deduction(attach_report="/files/pifss.csv")
		doc.append("deductions", {"employee_contribution": 10.5, "company_contribution": 11.5, "total_contribution": 22})
		doc.append("deductions", {"employee_contribution": 1, "company_contribution": 2, "total_contribution": 3})
		processa_rules.run_rule("Calculate PIFSS Monthly Deduction Totals", "recount", doc)
		self.assertEqual((doc.employee_contribution, doc.company_contribution, doc.total_contribution), (11.5, 13.5, 25))

	def test_removing_the_report_clears_the_rows(self):
		doc = deduction()
		doc.append("deductions", {"employee_contribution": 10})
		processa_rules.run_rule("Calculate PIFSS Monthly Deduction Totals", "recount", doc)
		self.assertEqual((len(doc.deductions), doc.employee_contribution), (0, 0))
