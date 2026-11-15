"""
The Server Scripts behind the penalty processes: Initiate Penalty Issuance, HR Enquiry
Lifecycle and Initiate Legal Investigation.

They are authored in the Processa editor and moved between sites by export/import, so the
site's Server Script records are what runs. The reviewed bodies are mirrored here;
TestTheSiteMatchesTheReviewedBodies fails when the two drift apart. The behaviour tests run
the literals below the way FrappeScriptEngine does (one namespace, ``doc`` loaded,
``result`` pre-set), so they give the same answer before the import has run.
"""

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from one_bpmn.security.script_validator import deep_inspect_script

PENALTY_ISSUANCE_PROCESS = "Initiate Penalty Issuance - v1"
HR_ENQUIRY_PROCESS = "HR Enquiry Lifecycle - v1"
LEGAL_INVESTIGATION_PROCESS = "Initiate Legal Investigation - v1"

QUERY_EMPLOYEE_SALARY = '''# Routes on the highest basic salary among the employees on the issuance, so a
# multi-employee issuance is not decided by whoever was added first.
salaries = [
    frappe.utils.flt(frappe.db.get_value("Employee", row.get("employee_id"), "one_fm_basic_salary"))
    for row in doc.get("employees") or []
]
result["salary_amount"] = max(salaries, default=0)
'''

CREATE_HR_ENQUIRY = '''# One HR Enquiry per employee on the issuance, carrying the incident, the issuer and
# every violation with its notes and attachment.
for emp_row in doc.get("employees") or []:
    employee_id = emp_row.get("employee_id")
    if frappe.db.exists("HR Enquiry", {"penalty_issuance": doc.name, "employee": employee_id}):
        continue

    he = frappe.new_doc("HR Enquiry")
    he.penalty_issuance = doc.name
    he.employee = employee_id
    he.employee_name = emp_row.get("employee_name")
    he.designation = emp_row.get("designation")
    he.employee_user = frappe.db.get_value("Employee", employee_id, "user_id")
    he.penalty_occurence_time = doc.penalty_occurence_time
    he.penalty_location = doc.penalty_location
    he.operations_shift = doc.shift
    he.operations_site = doc.site
    he.site_location = doc.site_location
    he.project = doc.project
    he.third_party_damage = doc.third_party_damage
    he.issuing_employee = doc.issuing_employee
    he.issuer_name = doc.employee_name
    he.issuer_designation = doc.designation
    he.response_required = 1

    for detail in doc.get("penalty_issuance_details") or []:
        he.append("hr_enquiry_detail", {
            "penalty_type": detail.get("penalty_type"),
            "penalty_type_arabic": detail.get("penalty_type_arabic"),
            "exact_notes": detail.get("exact_notes"),
            "attachments": detail.get("attachments"),
        })

    he.insert()
'''

CREATE_LEGAL_INVESTIGATION = '''# Opens one Legal Investigation for the issuance, with a penalty row for every
# violation of every employee on it.
from frappe.utils import add_to_date, getdate

if not frappe.db.exists("Legal Investigation", {"reference_doctype": doc.doctype, "reference_docname": doc.name}):
    li = frappe.new_doc("Legal Investigation")
    li.investigation_subject = "Penalty Issued with damages" if doc.third_party_damage else "Penalty Issued - High Salary Review"
    li.reference_doctype = "Penalty Issuance"
    li.reference_docname = doc.name
    li.penalty_issuance = doc.name
    li.third_party_damage = doc.third_party_damage
    li.start_date = add_to_date(getdate(), days=2)

    li.append("legal_investigation_employees", {
        "employee_id": doc.issuing_employee,
        "employee_name": doc.employee_name,
        "designation": doc.designation,
        "party": "Plaintiff"
    })
    for emp_row in doc.get("employees") or []:
        li.append("legal_investigation_employees", {
            "employee_id": emp_row.get("employee_id"),
            "employee_name": emp_row.get("employee_name"),
            "designation": emp_row.get("designation"),
            "party": "Defendant"
        })

        for detail in doc.get("penalty_issuance_details") or []:
            li.append("legal_investigation_penalty", {
                "employee_id": emp_row.get("employee_id"),
                "employee_name": emp_row.get("employee_name"),
                "designation": emp_row.get("designation"),
                "penalty_type": detail.get("penalty_type"),
                "investigation_results": detail.get("exact_notes"),
                "penalty_location": doc.penalty_location,
                "penalty_occurence_time": doc.penalty_occurence_time,
                "shift": doc.shift,
                "site": doc.site,
                "project": doc.project,
                "site_location": doc.site_location,
                "third_party_damage": doc.third_party_damage
            })

    li.insert()
'''

CONFIRM_PENALTY_LINKED = '''# Uphold Penalty: issue the employee's Penalty from the enquiry. Occurrence, levy,
# deduction and period are set by Penalty.before_insert, not here.
from frappe.utils import now_datetime

duplicate_filters = {"recipient_employee": doc.employee, "docstatus": ["!=", 2]}
if doc.penalty_issuance:
    duplicate_filters["penalty_issuance"] = doc.penalty_issuance
else:
    duplicate_filters["hr_enquiry"] = doc.name

existing = frappe.db.get_value("Penalty", duplicate_filters, "name")
if existing:
    doc.db_set("penalty", existing, update_modified=False)
else:
    penalty_doc = frappe.new_doc("Penalty")
    penalty_doc.penalty_issuance = doc.penalty_issuance
    penalty_doc.hr_enquiry = doc.name
    penalty_doc.source_process = "HR Enquiry"
    penalty_doc.penalty_issuance_time = (
        frappe.db.get_value("Penalty Issuance", doc.penalty_issuance, "issuing_time") if doc.penalty_issuance else None
    ) or now_datetime()
    penalty_doc.penalty_occurence_time = doc.penalty_occurence_time
    penalty_doc.penalty_location = doc.penalty_location
    penalty_doc.shift = doc.operations_shift
    penalty_doc.site = doc.operations_site
    penalty_doc.site_location = doc.site_location
    penalty_doc.project = doc.project
    penalty_doc.issuer_employee = doc.issuing_employee
    penalty_doc.issuer_name = doc.issuer_name
    penalty_doc.issuer_designation = doc.issuer_designation
    penalty_doc.recipient_employee = doc.employee
    penalty_doc.recipient_name = doc.employee_name
    penalty_doc.recipient_designation = doc.designation
    penalty_doc.recipient_user = frappe.db.get_value("Employee", doc.employee, "user_id")
    penalty_doc.third_party_damage = doc.third_party_damage
    penalty_doc.damage_amount = doc.damage_amount

    for detail in doc.get("hr_enquiry_detail") or []:
        penalty_doc.append("penalty_details", {
            "penalty_type": detail.get("penalty_type"),
            "penalty_type_arabic": detail.get("penalty_type_arabic"),
            "exact_notes": detail.get("exact_notes"),
            "attachments": detail.get("attachments")
        })

    penalty_doc.insert()
    doc.db_set("penalty", penalty_doc.name, update_modified=False)
'''

CONFIRM_LEGAL_INVESTIGATION_LINKED = '''# Escalate to Legal: open a Legal Investigation on the enquiry, keeping the link back to
# the original Penalty Issuance and the incident on every penalty row.
from frappe.utils import add_to_date, getdate

existing = frappe.db.get_value("Legal Investigation", {"reference_doctype": "HR Enquiry", "reference_docname": doc.name}, "name")
if existing:
    doc.db_set("legal_investigation", existing, update_modified=False)
else:
    li = frappe.new_doc("Legal Investigation")
    li.investigation_subject = "Escalated from HR Enquiry: " + doc.name
    li.reference_doctype = "HR Enquiry"
    li.reference_docname = doc.name
    li.hr_enquiry = doc.name
    li.penalty_issuance = doc.penalty_issuance
    li.third_party_damage = doc.third_party_damage
    li.start_date = add_to_date(getdate(), days=2)

    li.append("legal_investigation_employees", {
        "employee_id": doc.issuing_employee,
        "employee_name": doc.issuer_name,
        "designation": doc.issuer_designation,
        "party": "Plaintiff"
    })
    li.append("legal_investigation_employees", {
        "employee_id": doc.employee,
        "employee_name": doc.employee_name,
        "designation": doc.designation,
        "party": "Defendant"
    })

    for detail in doc.get("hr_enquiry_detail") or []:
        li.append("legal_investigation_penalty", {
            "employee_id": doc.employee,
            "employee_name": doc.employee_name,
            "designation": doc.designation,
            "penalty_type": detail.get("penalty_type"),
            "investigation_results": detail.get("exact_notes"),
            "penalty_location": doc.penalty_location,
            "penalty_occurence_time": doc.penalty_occurence_time,
            "shift": doc.operations_shift,
            "site": doc.operations_site,
            "project": doc.project,
            "site_location": doc.site_location,
            "third_party_damage": doc.third_party_damage,
            "damage_amount": doc.damage_amount
        })

    li.insert()
    doc.db_set("legal_investigation", li.name, update_modified=False)
'''

RECORD_OVERTURN_AND_NOTIFY = '''import frappe
from frappe.utils import get_link_to_form
from one_fm.api.notification import create_notification_log

issuer_user = frappe.db.get_value("Employee", doc.issuing_employee, "user_id")
subject = frappe._("{0}: Penalty Overturned by HR").format(doc.name)
link = get_link_to_form("HR Enquiry", doc.name)
message = frappe._("The penalty from PI {0} for employee {1} has been overturned by HR review.<br>Link: {2}").format(
    doc.penalty_issuance, doc.employee_name, link
)
if issuer_user:
    create_notification_log(subject, message, [issuer_user], doc)
'''

FETCH_SOURCE_DETAILS_INTO_INVESTIGATION = '''import frappe

if doc.reference_doctype and doc.reference_docname:
    source = frappe.get_doc(doc.reference_doctype, doc.reference_docname)
    result = {
        "source_type": doc.reference_doctype,
        "source_name": doc.reference_docname
    }
    if doc.reference_doctype == "Penalty Issuance":
        result["issuing_employee"] = source.issuing_employee
        result["employee_name"] = source.employee_name
    elif doc.reference_doctype == "HR Enquiry":
        result["issuing_employee"] = source.issuing_employee
        result["employee_name"] = source.employee_name
        result["hr_decision"] = source.hr_decision
'''

NOTIFY_ISSUING_SUPERVISOR = '''import frappe
from frappe.utils import get_link_to_form
from one_fm.processor import sendemail

if doc.reference_doctype == "Penalty Issuance":
    supervisor = frappe.db.get_value("Penalty Issuance", doc.reference_docname, "issuing_employee")
elif doc.reference_doctype == "HR Enquiry":
    supervisor = frappe.db.get_value("HR Enquiry", doc.reference_docname, "issuing_employee")
else:
    supervisor = None

if supervisor:
    supervisor_user = frappe.db.get_value("Employee", supervisor, "user_id")
    if supervisor_user:
        link = get_link_to_form("Legal Investigation", doc.name)
        subject = frappe._("Legal Investigation opened: {0}").format(doc.name)
        message = frappe._("A Legal Investigation has been opened. Please review.<br>Link: {0}").format(link)
        sendemail([supervisor_user], subject=subject, message=message, reference_doctype=doc.doctype, reference_name=doc.name)
'''

VERIFY_SESSION_SUBMITTED = '''import frappe

sessions = frappe.get_all(
    "Legal Investigation Session",
    filters={"legal_investigation_code": doc.name, "docstatus": 1},
    fields=["name"]
)

if len(sessions) > 0:
    doc.db_set("session_verified", 1, update_modified=False)
    result = True
else:
    if not doc.get("investigation_results"):
        frappe.throw(
            frappe._("Cannot complete investigation {0}. No submitted session found and no investigation results recorded.").format(doc.name)
        )
    doc.db_set("session_verified", 0, update_modified=False)
    result = False
'''

CREATE_PENALTY_ON_PENALTY_APPLIED = '''import frappe
from frappe.utils import now_datetime

reference = frappe.get_doc(doc.reference_doctype, doc.reference_docname) if doc.reference_doctype and doc.reference_docname else None

for penalty_row in doc.get("legal_investigation_penalty", []):
    employee_id = penalty_row.get("employee_id")
    pi_name = None
    hr_enquiry_name = None
    
    if doc.reference_doctype == "Penalty Issuance":
        pi_name = doc.reference_docname
    elif doc.reference_doctype == "HR Enquiry":
        hr_enquiry_name = doc.reference_docname
        pi_name = frappe.db.get_value("HR Enquiry", doc.reference_docname, "penalty_issuance")
    
    if pi_name and frappe.db.exists("Penalty", {"recipient_employee": employee_id, "penalty_issuance": pi_name}):
        continue
    
    user_id = frappe.db.get_value("Employee", employee_id, "user_id")
    
    penalty_doc = frappe.new_doc("Penalty")
    penalty_doc.penalty_issuance = pi_name
    penalty_doc.legal_investigation_code = doc.name
    penalty_doc.hr_enquiry = hr_enquiry_name
    penalty_doc.source_process = "Legal Investigation"
    penalty_doc.penalty_issuance_time = now_datetime()
    
    if reference and doc.reference_doctype == "Penalty Issuance":
        penalty_doc.issuer_employee = reference.issuing_employee
        penalty_doc.issuer_name = reference.employee_name
        penalty_doc.issuer_designation = reference.designation
    elif reference and doc.reference_doctype == "HR Enquiry":
        penalty_doc.issuer_employee = reference.issuing_employee
        penalty_doc.issuer_name = reference.issuer_name
        penalty_doc.issuer_designation = reference.issuer_designation
    else:
        penalty_doc.issuer_employee = doc.investigation_lead
        penalty_doc.issuer_name = doc.lead_name
    
    penalty_doc.recipient_employee = employee_id
    penalty_doc.recipient_name = penalty_row.get("employee_name")
    penalty_doc.recipient_designation = penalty_row.get("designation")
    penalty_doc.recipient_user = user_id
    penalty_doc.penalty_occurence_time = penalty_row.get("penalty_occurence_time")
    penalty_doc.penalty_location = penalty_row.get("penalty_location")
    penalty_doc.shift = penalty_row.get("shift")
    penalty_doc.site = penalty_row.get("site")
    penalty_doc.site_location = penalty_row.get("site_location")
    penalty_doc.project = penalty_row.get("project")
    penalty_doc.third_party_damage = penalty_row.get("third_party_damage")
    penalty_doc.damage_amount = penalty_row.get("damage_amount")
    
    penalty_doc.append("penalty_details", {
        "penalty_type": penalty_row.get("penalty_type"),
        "exact_notes": penalty_row.get("investigation_results")
    })
    
    penalty_doc.insert()
'''

RECORD_NOT_APPLICABLE_AND_NOTIFY = '''import frappe
from frappe.utils import get_link_to_form
from one_fm.api.notification import create_notification_log

if doc.reference_doctype and doc.reference_docname:
    if doc.reference_doctype == "Penalty Issuance":
        supervisor = frappe.db.get_value("Penalty Issuance", doc.reference_docname, "issuing_employee")
    elif doc.reference_doctype == "HR Enquiry":
        supervisor = frappe.db.get_value("HR Enquiry", doc.reference_docname, "issuing_employee")
    else:
        supervisor = None
    
    if supervisor:
        supervisor_user = frappe.db.get_value("Employee", supervisor, "user_id")
        if supervisor_user:
            subject = frappe._("Legal Investigation {0}: Penalty Not Applicable").format(doc.name)
            link = get_link_to_form("Legal Investigation", doc.name)
            message = frappe._("The Legal Investigation concluded that penalty is not applicable.<br>Link: {0}").format(link)
            create_notification_log(subject, message, [supervisor_user], doc)
'''

# (Server Script, process, script task id, reviewed body)
SCRIPTS = (
	("Query Employee Salary", PENALTY_ISSUANCE_PROCESS, "Activity_1nwkxsy", QUERY_EMPLOYEE_SALARY),
	("Create HR Enquiry", PENALTY_ISSUANCE_PROCESS, "Activity_1ksq2wv", CREATE_HR_ENQUIRY),
	("Create Legal Investigation", PENALTY_ISSUANCE_PROCESS, "Activity_0jv6zqu", CREATE_LEGAL_INVESTIGATION),
	("Confirm Penalty Linked", HR_ENQUIRY_PROCESS, "script_confirm_penalty_linked", CONFIRM_PENALTY_LINKED),
	(
		"Confirm Legal Investigation Linked",
		HR_ENQUIRY_PROCESS,
		"script_confirm_legal_investigation_linked",
		CONFIRM_LEGAL_INVESTIGATION_LINKED,
	),
	("Record Overturn and Notify", HR_ENQUIRY_PROCESS, "script_record_overturn_and_notify", RECORD_OVERTURN_AND_NOTIFY),
	(
		"Fetch Source Details Into Investigation",
		LEGAL_INVESTIGATION_PROCESS,
		"task_fetch_source",
		FETCH_SOURCE_DETAILS_INTO_INVESTIGATION,
	),
	("Notify Issuing Supervisor", LEGAL_INVESTIGATION_PROCESS, "task_notify_supervisor", NOTIFY_ISSUING_SUPERVISOR),
	("Verify Session Submitted", LEGAL_INVESTIGATION_PROCESS, "task_verify_session", VERIFY_SESSION_SUBMITTED),
	(
		"Create Penalty on Penalty Applied",
		LEGAL_INVESTIGATION_PROCESS,
		"task_create_penalty",
		CREATE_PENALTY_ON_PENALTY_APPLIED,
	),
	(
		"Record Not Applicable and Notify",
		LEGAL_INVESTIGATION_PROCESS,
		"task_record_not_applicable",
		RECORD_NOT_APPLICABLE_AND_NOTIFY,
	),
)

BPMN = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
SPIFF = "{http://spiffworkflow.org/bpmn/schema/1.0/core}"
ISSUER_USER = "penalty-issuer-bpmn@example.com"


def run_script(body: str, doc) -> dict:
	"""Execute a body the way FrappeScriptEngine._run_frappe_server_script does."""
	result = {}
	exec(  # noqa: S102
		body,
		{
			"frappe": frappe,
			"__builtins__": __builtins__,
			"doc": doc,
			"result": result,
			"task_data": {},
			"context_doctype": doc.get("doctype") or "",
			"context_docname": doc.get("name") or "",
		},
	)
	return result


def diagram(title: str):
	import xml.etree.ElementTree as ET

	xml = frappe.db.get_value("BPMN Process Model", title, "bpmn_xml")
	return ET.fromstring(xml.strip().encode("utf-8")) if xml else None


class TestTheScriptsPassTheSecurityGate(FrappeTestCase):
	def test_no_violations_in_any_body(self):
		for name, _process, _task, body in SCRIPTS:
			with self.subTest(script=name):
				self.assertEqual(deep_inspect_script(body), [], msg=name)

	def test_each_body_compiles_in_the_restricted_context(self):
		from RestrictedPython import compile_restricted

		from frappe.utils.safe_exec import FrappeTransformer

		for name, _process, _task, body in SCRIPTS:
			with self.subTest(script=name):
				compile_restricted(body, policy=FrappeTransformer)


class TestTheSiteMatchesTheReviewedBodies(FrappeTestCase):
	"""Fails until the fixed maps and their config are imported, by design."""

	def test_every_script_exists_on_this_site(self):
		absent = [name for name, _p, _t, _b in SCRIPTS if not frappe.db.exists("Server Script", name)]
		self.assertEqual(absent, [], msg="Import the three penalty maps with their config files.")

	def test_no_script_has_drifted_from_the_body_reviewed_here(self):
		for name, _process, _task, body in SCRIPTS:
			if not frappe.db.exists("Server Script", name):
				continue
			with self.subTest(script=name):
				on_site = frappe.db.get_value("Server Script", name, "script") or ""
				self.assertEqual(on_site.strip(), body.strip(), msg=name)

	def test_none_of_them_is_disabled(self):
		for name, _process, _task, _body in SCRIPTS:
			if frappe.db.exists("Server Script", name):
				with self.subTest(script=name):
					self.assertFalse(frappe.db.get_value("Server Script", name, "disabled"))


class TestTheDiagrams(FrappeTestCase):
	def root(self, title):
		root = diagram(title)
		if root is None:
			self.skipTest(f"{title} is not on this site")
		return root

	def test_every_script_is_bound_to_its_task(self):
		for name, process, task_id, _body in SCRIPTS:
			with self.subTest(script=name):
				bound = {e.get("id"): e.get(SPIFF + "serverScript") for e in self.root(process).iter(BPMN + "scriptTask")}
				self.assertEqual(bound.get(task_id), name)

	def test_an_escalated_enquiry_is_set_to_escalated_to_legal(self):
		root = self.root(HR_ENQUIRY_PROCESS)
		flows = {f.get("sourceRef"): f.get("targetRef") for f in root.iter(BPMN + "sequenceFlow")}
		step = flows["script_confirm_legal_investigation_linked"]
		task = next(e for e in root.iter(BPMN + "serviceTask") if e.get("id") == step)

		self.assertEqual(task.get(SPIFF + "serviceType"), "apply_workflow")
		self.assertEqual(task.get(SPIFF + "workflowState"), "Escalated to Legal")
		self.assertEqual(flows[step], "end_escalated_to_legal")
		self.assertTrue(frappe.db.exists("Workflow State", "Escalated to Legal"))

	def test_no_step_is_guarded_to_a_role_the_starter_may_lack(self):
		for title in (PENALTY_ISSUANCE_PROCESS, LEGAL_INVESTIGATION_PROCESS):
			with self.subTest(process=title):
				guarded = [e.get("id") for e in self.root(title).iter() if e.get(SPIFF + "onlyAllowEdit")]
				self.assertEqual(guarded, [])

	def test_investigation_tasks_go_to_the_lead_user(self):
		fields = {
			e.get(SPIFF + "assigneeDocfield") for e in self.root(LEGAL_INVESTIGATION_PROCESS).iter(BPMN + "userTask")
		}
		self.assertEqual(fields, {"lead_user"})


class PenaltyFixtures(FrappeTestCase):
	"""An issuer and two employees with users, a shift with a site and a penalty type."""

	@classmethod
	def setUpClass(cls):
		employees = frappe.get_all(
			"Employee",
			filters={"status": "Active", "user_id": ["is", "set"], "designation": ["is", "set"]},
			fields=["name", "employee_name", "designation", "user_id"],
			limit=3,
		)
		shift = frappe.db.get_value(
			"Operations Shift", {"site": ["is", "set"], "project": ["is", "set"]}, ["name", "site", "project"]
		)
		penalty_type = frappe.db.get_value("Penalty Type", {}, "name")
		if len(employees) < 3 or not shift or not penalty_type:
			raise unittest.SkipTest("Needs three active Employees with users, a staffed Operations Shift and a Penalty Type")

		super().setUpClass()
		# The code under test commits; without this the fixtures, and the user_id the
		# issuer test gives a real Employee, would survive the class rollback.
		no_commit = patch("frappe.db.commit")
		no_commit.start()
		cls.addClassCleanup(no_commit.stop)
		cls.issuer, cls.first, cls.second = employees
		cls.shift, cls.site, cls.project = shift
		cls.site_location = frappe.db.get_value("Operations Site", cls.site, "site_location")
		cls.penalty_type = penalty_type

	def make_penalty_issuance(self, employees=None, **fields):
		issuance = frappe.get_doc(
			{
				"doctype": "Penalty Issuance",
				"penalty_category": "Performance",
				"penalty_location": "Gate 3",
				"penalty_occurence_time": add_to_date(now_datetime(), hours=-2),
				"shift": self.shift,
				"site": self.site,
				"project": self.project,
				"site_location": self.site_location,
				"issuing_employee": self.issuer.name,
				"employee_name": self.issuer.employee_name,
				"designation": self.issuer.designation,
				"employees": [
					{"employee_id": e.name, "employee_name": e.employee_name, "designation": e.designation}
					for e in (employees or [self.first, self.second])
				],
				"penalty_issuance_details": [
					{
						"penalty_type": self.penalty_type,
						"exact_notes": "<p>Asleep on post</p>",
						"attachments": "/private/files/asleep.jpg",
					}
				],
				**fields,
			}
		)
		return issuance.insert(ignore_permissions=True)

	def make_hr_enquiry(self, **fields):
		issuance = self.make_penalty_issuance(employees=[self.first], **fields)
		run_script(CREATE_HR_ENQUIRY, issuance)
		return issuance, frappe.get_doc("HR Enquiry", {"penalty_issuance": issuance.name})


class TestQueryEmployeeSalary(PenaltyFixtures):
	def test_routes_on_the_highest_salary(self):
		frappe.db.set_value("Employee", self.first.name, "one_fm_basic_salary", 200)
		frappe.db.set_value("Employee", self.second.name, "one_fm_basic_salary", 400)
		doc = frappe._dict(employees=[frappe._dict(employee_id=e.name) for e in (self.first, self.second)])

		self.assertEqual(run_script(QUERY_EMPLOYEE_SALARY, doc), {"salary_amount": 400})

	def test_no_employees_routes_as_zero(self):
		self.assertEqual(run_script(QUERY_EMPLOYEE_SALARY, frappe._dict(employees=[])), {"salary_amount": 0})


class TestPenaltyIssuanceToHREnquiry(PenaltyFixtures):
	def test_every_field_the_issuance_has_reaches_the_enquiry(self):
		issuance = self.make_penalty_issuance()
		run_script(CREATE_HR_ENQUIRY, issuance)

		enquiries = frappe.get_all("HR Enquiry", filters={"penalty_issuance": issuance.name}, pluck="name")
		self.assertEqual(len(enquiries), 2)

		enquiry = frappe.get_doc("HR Enquiry", {"penalty_issuance": issuance.name, "employee": self.first.name})
		expected = {
			"employee": self.first.name,
			"employee_name": self.first.employee_name,
			"designation": self.first.designation,
			"employee_user": self.first.user_id,
			"penalty_location": issuance.penalty_location,
			"operations_shift": issuance.shift,
			"operations_site": issuance.site,
			"site_location": issuance.site_location,
			"project": issuance.project,
			"issuing_employee": issuance.issuing_employee,
			"issuer_name": issuance.employee_name,
			"issuer_designation": issuance.designation,
			"third_party_damage": 0,
		}
		for fieldname, value in expected.items():
			with self.subTest(field=fieldname):
				self.assertEqual(enquiry.get(fieldname), value)
		self.assertEqual(str(enquiry.penalty_occurence_time), str(issuance.penalty_occurence_time))

		detail = enquiry.hr_enquiry_detail[0]
		self.assertEqual(detail.penalty_type, self.penalty_type)
		self.assertEqual(detail.exact_notes, "<p>Asleep on post</p>")
		self.assertEqual(detail.attachments, "/private/files/asleep.jpg")

	def test_a_second_run_creates_nothing(self):
		issuance = self.make_penalty_issuance()
		run_script(CREATE_HR_ENQUIRY, issuance)
		run_script(CREATE_HR_ENQUIRY, issuance)

		self.assertEqual(frappe.db.count("HR Enquiry", {"penalty_issuance": issuance.name}), 2)


class TestPenaltyIssuanceToLegalInvestigation(PenaltyFixtures):
	def test_one_penalty_row_per_employee(self):
		issuance = self.make_penalty_issuance(third_party_damage=1)
		run_script(CREATE_LEGAL_INVESTIGATION, issuance)

		investigation = frappe.get_doc(
			"Legal Investigation", {"reference_doctype": "Penalty Issuance", "reference_docname": issuance.name}
		)
		self.assertEqual(investigation.penalty_issuance, issuance.name)
		self.assertEqual(
			sorted(row.employee_id for row in investigation.legal_investigation_penalty),
			sorted([self.first.name, self.second.name]),
		)
		for row in investigation.legal_investigation_penalty:
			self.assertEqual(row.third_party_damage, 1)
			self.assertEqual(row.site_location, issuance.site_location)


class TestHREnquiryToPenalty(PenaltyFixtures):
	def test_uphold_issues_a_traceable_penalty(self):
		issuance, enquiry = self.make_hr_enquiry(third_party_damage=1)
		enquiry.db_set("damage_amount", 75)
		enquiry.reload()

		run_script(CONFIRM_PENALTY_LINKED, enquiry)

		penalty = frappe.get_doc("Penalty", frappe.db.get_value("HR Enquiry", enquiry.name, "penalty"))
		expected = {
			"penalty_issuance": issuance.name,
			"hr_enquiry": enquiry.name,
			"source_process": "HR Enquiry",
			"issuer_employee": self.issuer.name,
			"issuer_name": enquiry.issuer_name,
			"recipient_employee": self.first.name,
			"recipient_name": self.first.employee_name,
			"recipient_user": self.first.user_id,
			"third_party_damage": 1,
			"damage_amount": 75,
		}
		for fieldname, value in expected.items():
			with self.subTest(field=fieldname):
				self.assertEqual(penalty.get(fieldname), value)
		self.assertEqual(
			str(penalty.penalty_issuance_time), str(frappe.db.get_value("Penalty Issuance", issuance.name, "issuing_time"))
		)

		detail = penalty.penalty_details[0]
		self.assertEqual(detail.penalty_type, self.penalty_type)
		self.assertEqual(detail.exact_notes, "<p>Asleep on post</p>")
		self.assertEqual(detail.attachments, "/private/files/asleep.jpg")
		# Numbered by Penalty.before_insert, not by the script.
		self.assertGreaterEqual(detail.occurence_number, 1)
		self.assertTrue(detail.period_start_date)

	def test_a_second_run_creates_no_duplicate(self):
		_issuance, enquiry = self.make_hr_enquiry()
		run_script(CONFIRM_PENALTY_LINKED, enquiry)
		run_script(CONFIRM_PENALTY_LINKED, enquiry)

		self.assertEqual(frappe.db.count("Penalty", {"hr_enquiry": enquiry.name}), 1)

	def test_a_cancelled_penalty_does_not_block_a_new_one(self):
		_issuance, enquiry = self.make_hr_enquiry()
		run_script(CONFIRM_PENALTY_LINKED, enquiry)
		frappe.db.set_value("Penalty", {"hr_enquiry": enquiry.name}, "docstatus", 2)

		run_script(CONFIRM_PENALTY_LINKED, enquiry)

		self.assertEqual(frappe.db.count("Penalty", {"hr_enquiry": enquiry.name, "docstatus": ["!=", 2]}), 1)


class TestHREnquiryToLegalInvestigation(PenaltyFixtures):
	def escalate(self):
		issuance, enquiry = self.make_hr_enquiry(third_party_damage=1)
		enquiry.db_set("damage_amount", 120)
		enquiry.reload()
		with patch("one_fm.legal.doctype.legal_investigation.legal_investigation.sendemail"):
			run_script(CONFIRM_LEGAL_INVESTIGATION_LINKED, enquiry)
		return issuance, enquiry, frappe.db.get_value("HR Enquiry", enquiry.name, "legal_investigation")

	def test_escalation_carries_the_whole_chain(self):
		issuance, enquiry, investigation_name = self.escalate()
		investigation = frappe.get_doc("Legal Investigation", investigation_name)

		self.assertEqual(investigation.reference_doctype, "HR Enquiry")
		self.assertEqual(investigation.reference_docname, enquiry.name)
		self.assertEqual(investigation.hr_enquiry, enquiry.name)
		self.assertEqual(investigation.penalty_issuance, issuance.name)

		row = investigation.legal_investigation_penalty[0]
		expected = {
			"employee_id": self.first.name,
			"employee_name": self.first.employee_name,
			"designation": self.first.designation,
			"penalty_location": enquiry.penalty_location,
			"shift": enquiry.operations_shift,
			"site": enquiry.operations_site,
			"project": enquiry.project,
			"site_location": enquiry.site_location,
			"third_party_damage": 1,
			"damage_amount": 120,
		}
		for fieldname, value in expected.items():
			with self.subTest(field=fieldname):
				self.assertEqual(row.get(fieldname), value)

	def test_a_second_run_opens_no_second_investigation(self):
		_issuance, enquiry, investigation_name = self.escalate()
		run_script(CONFIRM_LEGAL_INVESTIGATION_LINKED, frappe.get_doc("HR Enquiry", enquiry.name))

		self.assertEqual(
			frappe.db.count("Legal Investigation", {"reference_doctype": "HR Enquiry", "reference_docname": enquiry.name}),
			1,
		)
		self.assertEqual(frappe.db.get_value("HR Enquiry", enquiry.name, "legal_investigation"), investigation_name)

	def test_penalty_applied_links_all_three_sources(self):
		issuance, enquiry, investigation_name = self.escalate()

		run_script(CREATE_PENALTY_ON_PENALTY_APPLIED, frappe.get_doc("Legal Investigation", investigation_name))

		penalty = frappe.get_doc("Penalty", {"legal_investigation_code": investigation_name})
		self.assertEqual(penalty.penalty_issuance, issuance.name)
		self.assertEqual(penalty.hr_enquiry, enquiry.name)
		self.assertEqual(penalty.source_process, "Legal Investigation")


class TestTheScriptsRunAsAnIssuer(PenaltyFixtures):
	"""Scripts run as the instance's initiator, the issuer, and may not bypass permissions."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from one_fm.patches.v15_0.move_penalty_issuance_to_processa import allow_issuers_to_create

		if not frappe.db.exists("User", ISSUER_USER):
			frappe.get_doc(
				{"doctype": "User", "email": ISSUER_USER, "first_name": "Issuer", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", ISSUER_USER).add_roles("Employee", "Shift Supervisor")
		frappe.db.set_value("Employee", cls.issuer.name, "user_id", ISSUER_USER)
		allow_issuers_to_create("Legal Investigation", "Penalty")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_a_shift_supervisor_runs_both_routes_and_the_uphold(self):
		self.assertNotIn("System Manager", frappe.get_roles(ISSUER_USER))
		issuance = self.make_penalty_issuance()
		frappe.set_user(ISSUER_USER)

		run_script(CREATE_HR_ENQUIRY, issuance)
		with patch("one_fm.legal.doctype.legal_investigation.legal_investigation.sendemail"):
			run_script(CREATE_LEGAL_INVESTIGATION, issuance)
		enquiry = frappe.get_doc("HR Enquiry", {"penalty_issuance": issuance.name, "employee": self.first.name})
		run_script(CONFIRM_PENALTY_LINKED, enquiry)

		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count("HR Enquiry", {"penalty_issuance": issuance.name}), 2)
		self.assertTrue(frappe.db.exists("Legal Investigation", {"penalty_issuance": issuance.name}))
		self.assertTrue(frappe.db.exists("Penalty", {"hr_enquiry": enquiry.name}))
