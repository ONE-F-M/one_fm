# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Onboard Subcontract Employee process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Assign Subcontract Onboarding Officer": """# Onboarding Officers start, retry and complete the onboarding.
result["assigned_user"] = ""
result["assigned_role"] = "Onboarding Officer"
""",
	"Assign Subcontract Accommodation User": """# Accommodation Users check the employee into a bed.
result["assigned_user"] = ""
result["assigned_role"] = "Accommodation User"
""",
	"IT Onboarding of Subcontract Employee": """# Creates the Employee and the draft uniform issue, and links the Employee's user.
# Sets result["it_onboarding_done"] (False reopens the retry task with the reasons shown)
# and result["needs_checkin"] for the Accommodation User step.
problems = []
dob = doc.get("date_of_birth")
if dob and frappe.utils.getdate(dob) > frappe.utils.getdate(frappe.utils.today()):
	problems.append("Date of Birth cannot be in the future.")
for fieldname, label in (("date_of_joining", "Date of Joining"), ("department", "Department")):
	if not doc.get(fieldname):
		problems.append(f"{label} is required.")

subcontract_emp_type = frappe.db.get_single_value("Hiring Settings", "subcontract_employment_type")
civil_id = frappe.db.get_value("Subcontract Staff Shortlist Detail", doc.get("staff_shortlist_detail"), "civil_id_no")

employee_name = doc.get("employee")
if employee_name:
	# An Employee whose first name differs was linked by mistake.
	linked_first_name = frappe.db.get_value("Employee", employee_name, "first_name")
	candidate_first_name = doc.get("first_name")
	if not linked_first_name or (candidate_first_name and linked_first_name.strip().lower() != candidate_first_name.strip().lower()):
		employee_name = None
		doc.db_set("employee", None)

if not employee_name:
	# A retry finds the Employee an earlier attempt created.
	if civil_id:
		employee_name = frappe.db.get_value("Employee", {"one_fm_civil_id": civil_id}, "name")
	if not employee_name:
		employee_name = frappe.db.get_value("Employee", {
			"first_name": doc.get("first_name"),
			"last_name": doc.get("last_name"),
			"date_of_birth": dob,
			"employment_type": subcontract_emp_type,
		}, "name")
	if employee_name:
		doc.db_set("employee", employee_name)

if not employee_name and not frappe.has_permission("Employee", "create"):
	problems.append(f"{frappe.session.user} cannot create an Employee.")
if doc.get("is_uniform_needed_for_this_job") and not doc.get("uniform_issued") and not frappe.has_permission("Employee Uniform", "create"):
	problems.append(f"{frappe.session.user} cannot create an Employee Uniform.")

if not problems and not employee_name:
	emp = frappe.new_doc("Employee")
	emp.update({
		"first_name": doc.get("first_name"),
		"middle_name": doc.get("second_name"),
		"one_fm_third_name": doc.get("third_name"),
		"one_fm_fourth_name": doc.get("fourth_name"),
		"last_name": doc.get("last_name"),
		"one_fm_first_name_in_arabic": doc.get("first_name_in_arabic"),
		"one_fm_second_name_in_arabic": doc.get("second_name_in_arabic"),
		"one_fm_third_name_in_arabic": doc.get("third_name_in_arabic"),
		"one_fm_fourth_name_in_arabic": doc.get("fourth_name_in_arabic"),
		"one_fm_last_name_in_arabic": doc.get("last_name_in_arabic"),
		"date_of_birth": dob,
		"gender": doc.get("gender"),
		"one_fm_nationality": doc.get("nationality"),
		"one_fm_civil_id": civil_id,
		"cell_number": doc.get("contact_number"),
		"status": "Active",
		"date_of_joining": doc.get("date_of_joining"),
		"department": doc.get("department"),
		"designation": doc.get("designation"),
		"employment_type": subcontract_emp_type,
		"one_fm_basic_salary": doc.get("basic_salary") or 0,
		"custom_subcontractor_name": doc.get("subcontractor_name"),
		"shift": doc.get("shift_allocation"),
		"site": doc.get("site_allocation"),
		"project": doc.get("project_allocation"),
		"day_off_category": doc.get("day_off_category"),
		"number_of_days_off": doc.get("number_of_days_off"),
	})
	if not emp.company:
		emp.company = frappe.db.get_single_value("Global Defaults", "default_company")
	emp.insert()
	employee_name = emp.name
	doc.db_set("employee", employee_name)

if employee_name:
	# Employee after_insert creates the user from the employee ID.
	user_id = frappe.db.get_value("Employee", employee_name, "user_id")
	if user_id and doc.get("employee_user") != user_id:
		doc.db_set("employee_user", user_id)

	if doc.get("is_uniform_needed_for_this_job") and not doc.get("uniform_issued"):
		uniform = frappe.new_doc("Employee Uniform")
		uniform.employee = employee_name
		uniform.type = "Issue"
		uniform.flags.ignore_validate = True
		uniform.flags.ignore_mandatory = True
		uniform.insert()
		doc.db_set("uniform_issued", uniform.name)

result["it_onboarding_done"] = not problems
result["needs_checkin"] = bool(doc.get("provide_accommodation_by_company") and not doc.get("accommodation_provided"))
if problems:
	frappe.msgprint("<br>".join(problems), title="IT Onboarding Not Done", indicator="red")
""",
	"Link Subcontract Employee Check-in": """# Links the employee's open bed check-in to the onboarding record.
# Sets result["checkin_linked"]; on False the process reopens the check-in task.
checkin = frappe.db.get_value(
	"Accommodation Checkin Checkout",
	{"employee": doc.get("employee"), "type": "IN", "checked_out": 0},
	"name",
	order_by="creation desc",
) if doc.get("employee") else None
if checkin:
	doc.db_set("accommodation_provided", checkin)
result["checkin_linked"] = bool(checkin)
if not checkin:
	frappe.msgprint(
		f"No open Accommodation Check-in found for employee {doc.get('employee')}. Create it from the Accommodation Check-in button, then click Checked In.",
		title="Check-in Missing",
		indicator="red",
	)
""",
	"Check Subcontract Onboarding Completion": """# Sets result["onboarding_complete"]; on False the process reopens the Complete Onboarding task with the reasons shown.
problems = []
values = frappe.db.get_value(
	doc.doctype, doc.name,
	["employee", "employee_user", "enrolled", "uniform_issued", "accommodation_provided"],
	as_dict=True,
)
employee_status, employee_user = None, values.employee_user
if values.employee:
	employee_status, user_id = frappe.db.get_value("Employee", values.employee, ["status", "user_id"]) or (None, None)
	if not employee_user and user_id:
		employee_user = user_id
		doc.db_set("employee_user", user_id)

if not values.employee:
	problems.append("Employee record has not been created.")
elif employee_status != "Active":
	problems.append(f"Employee {values.employee} must be Active.")
if not employee_user:
	problems.append("User account has not been created.")
elif not frappe.db.get_value("User", employee_user, "enabled"):
	problems.append(f"User account {employee_user} is disabled or missing.")
if not values.enrolled:
	problems.append("Employee must be enrolled in the biometric system.")
if doc.get("is_uniform_needed_for_this_job") and not values.uniform_issued:
	problems.append("Uniform is required for this job but has not been issued.")
if doc.get("provide_accommodation_by_company") and not values.accommodation_provided:
	problems.append("Accommodation is required but no check-in record is linked.")

result["onboarding_complete"] = not problems
if problems:
	frappe.msgprint("<br>".join(problems), title="Cannot Complete Onboarding", indicator="red")
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
		"context_doctype": "Onboard Subcontract Employee",
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


def ose(**kw):
	doc = frappe.new_doc("Onboard Subcontract Employee")
	doc.name = "ONB-SCS-PROCESSA-TEST-1"
	doc.update(kw)
	return doc


class TestAssignScripts(FrappeTestCase):
	def test_role_assignees(self):
		for name, role in (("Assign Subcontract Onboarding Officer", "Onboarding Officer"), ("Assign Subcontract Accommodation User", "Accommodation User")):
			result = run(name, ose())
			self.assertEqual((result["assigned_role"], result["assigned_user"]), (role, ""))


class TestITOnboarding(FrappeTestCase):
	def test_future_date_of_birth_stops_before_creating_anything(self):
		doc = ose(date_of_birth=frappe.utils.add_days(frappe.utils.today(), 5), date_of_joining="2026-01-01", department="Operations")
		with patch("frappe.new_doc") as new_doc, patch.object(doc, "db_set"):
			result = run("IT Onboarding of Subcontract Employee", doc)
		self.assertFalse(result["it_onboarding_done"])
		new_doc.assert_not_called()

	def test_missing_employee_create_permission_is_a_gate_not_an_error(self):
		doc = ose(date_of_birth="1990-01-01", date_of_joining="2026-01-01", department="Operations", first_name="Nobody", last_name="Here")
		with patch("frappe.has_permission", return_value=False), patch("frappe.new_doc") as new_doc, patch.object(doc, "db_set"):
			result = run("IT Onboarding of Subcontract Employee", doc)
		self.assertFalse(result["it_onboarding_done"])
		new_doc.assert_not_called()

	def test_existing_employee_is_reused_and_checkin_is_left_to_accommodation(self):
		doc = ose(date_of_birth="1990-01-01", date_of_joining="2026-01-01", department="Operations", staff_shortlist_detail="ROW-1", provide_accommodation_by_company=1)

		real_get_value = frappe.db.get_value

		def get_value(*args, **kwargs):
			dt, filters, fieldname = (list(args) + [None, None, None])[:3]
			if dt == "Subcontract Staff Shortlist Detail":
				return "CIVIL-1"
			if dt == "Employee" and isinstance(filters, dict) and filters.get("one_fm_civil_id") == "CIVIL-1":
				return "EMP-1"
			if dt == "Employee" and fieldname == "user_id":
				return "user-1@example.com"
			if dt in ("Employee", "Hiring Settings"):
				return None
			return real_get_value(*args, **kwargs)

		with patch("frappe.db.get_value", side_effect=get_value), patch("frappe.new_doc") as new_doc, patch.object(doc, "db_set") as db_set:
			result = run("IT Onboarding of Subcontract Employee", doc)
		self.assertTrue(result["it_onboarding_done"])
		self.assertTrue(result["needs_checkin"])
		new_doc.assert_not_called()
		db_set.assert_any_call("employee", "EMP-1")
		db_set.assert_any_call("employee_user", "user-1@example.com")


class TestLinkCheckin(FrappeTestCase):
	def test_open_checkin_is_linked(self):
		doc = ose(employee="EMP-1")
		with patch("frappe.db.get_value", return_value="CHECKIN-1") as get_value, patch.object(doc, "db_set") as db_set:
			self.assertTrue(run("Link Subcontract Employee Check-in", doc)["checkin_linked"])
		self.assertEqual(get_value.call_args.args[1], {"employee": "EMP-1", "type": "IN", "checked_out": 0})
		db_set.assert_called_once_with("accommodation_provided", "CHECKIN-1")

	def test_no_checkin_reopens_the_task(self):
		doc = ose(employee="EMP-1")
		with patch("frappe.db.get_value", return_value=None), patch.object(doc, "db_set") as db_set:
			self.assertFalse(run("Link Subcontract Employee Check-in", doc)["checkin_linked"])
		db_set.assert_not_called()


class TestCheckCompletion(FrappeTestCase):
	def values(self, **kw):
		v = {"employee": "EMP-1", "employee_user": "user-1@example.com", "enrolled": 1, "uniform_issued": "EUI-1", "accommodation_provided": "CHECKIN-1"}
		v.update(kw)
		return frappe._dict(v)

	def check(self, values, doc=None, employee=("Active", "user-1@example.com"), user_enabled=1):
		doc = doc or ose(is_uniform_needed_for_this_job=1, provide_accommodation_by_company=1)

		def get_value(dt, *args, **kwargs):
			return {"Onboard Subcontract Employee": values, "Employee": employee, "User": user_enabled}[dt]

		with patch("frappe.db.get_value", side_effect=get_value), patch.object(doc, "db_set") as db_set:
			return run("Check Subcontract Onboarding Completion", doc)["onboarding_complete"], db_set

	def test_everything_in_place_completes(self):
		self.assertTrue(self.check(self.values())[0])

	def test_each_missing_piece_blocks(self):
		for kw in ({"employee": None}, {"enrolled": 0}, {"uniform_issued": None}, {"accommodation_provided": None}):
			self.assertFalse(self.check(self.values(**kw))[0], kw)
		self.assertFalse(self.check(self.values(), employee=("Left", "user-1@example.com"))[0])
		self.assertFalse(self.check(self.values(), user_enabled=0)[0])

	def test_user_is_read_from_employee_when_missing(self):
		ok, db_set = self.check(self.values(employee_user=None))
		self.assertTrue(ok)
		db_set.assert_called_once_with("employee_user", "user-1@example.com")

	def test_uniform_and_checkin_only_when_required(self):
		self.assertTrue(self.check(self.values(uniform_issued=None, accommodation_provided=None), doc=ose())[0])
