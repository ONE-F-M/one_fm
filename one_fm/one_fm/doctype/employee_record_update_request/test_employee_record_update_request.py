# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import re
import unittest
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate, getdate

from one_fm.patches.v15_0 import create_employee_record_update_request_workflow_states as states_patch
from one_fm.tests.utils import make_employee

DOCTYPE = "Employee Record Update Request"

# (fieldname, fieldtype, options, reqd, read_only, depends_on, fetch_from) in BA order.
# Layout fields (Section/Column Breaks) are checked separately.
EXPECTED_FIELDS = [
	("employee", "Link", "Employee", 1, 0, "", ""),
	("employee_name", "Data", "", 0, 1, "", "employee.employee_name"),
	("designation", "Link", "Designation", 0, 1, "", "employee.designation"),
	("department", "Link", "Department", 0, 1, "", "employee.department"),
	("project_allocation", "Link", "Project", 0, 0, "", "employee.project"),
	("workflow_state", "Link", "Workflow State", 0, 1, "", ""),
	("effective_date_of_change", "Date", "", 1, 0, "", ""),
	("line_manager", "Link", "Employee", 0, 1, "", "employee.reports_to"),
	("line_manager_user", "Link", "User", 0, 1, "", "line_manager.user_id"),
	("salary_update_required", "Check", "", 0, 0, "", ""),
	(
		"current_salary_structure", "Link", "Salary Structure Assignment", 0, 0,
		"eval:doc.salary_update_required", "current_base_salary.salary_structure",
	),
	("salary_new_value", "Link", "Salary Structure", 0, 0, "eval:doc.salary_update_required", ""),
	("employee_appraisal_required", "Check", "", 0, 0, "eval:doc.salary_update_required", ""),
	(
		"current_base_salary", "Data", "Salary Structure Assignment", 0, 0,
		"eval:doc.salary_update_required", "current_salary_structure.base",
	),
	("base_new_value", "Currency", "", 0, 0, "eval:doc.salary_update_required", ""),
	("employee_appraisal_form", "Attach", "", 0, 0, "eval:doc.employee_appraisal_required==1", ""),
	(
		"salary_structure_components", "Table",
		"Employee Record Update Request Salary Structure Compone Item", 0, 0,
		"eval:doc.salary_update_required", "",
	),
	("properties_changes_required", "Check", "", 0, 0, "", ""),
	(
		"properties", "Table", "Employee Record Update Request Properties Item", 0, 0,
		"eval:doc.properties_changes_required==1", "",
	),
	("benefits_changes_required", "Check", "", 0, 0, "", ""),
	(
		"benefit", "Table", "Employee Record Update Request Benefits Item", 0, 0,
		"eval:doc.benefits_changes_required==1", "",
	),
	("reason", "Small Text", "", 1, 0, "", ""),
	("amended_from", "Link", DOCTYPE, 0, 1, "", ""),
]

LAYOUT_TYPES = ("Section Break", "Column Break", "Tab Break")

PERMISSION_FLAGS = (
	"read", "write", "create", "delete", "submit", "cancel", "amend",
	"report", "export", "print", "email", "share",
)
_HR_MANAGER = {"read", "write", "create", "delete", "submit", "report", "export", "print", "email", "share"}
EXPECTED_PERMISSIONS = {
	"HR User": _HR_MANAGER | {"amend"},
	"HR Manager": _HR_MANAGER,
	"System Manager": _HR_MANAGER - {"submit"},
	"Employee": {"read", "write", "create", "print", "email", "share"},
}

NO_HR_USER = "erur_no_hr_role@example.com"


DOCTYPES = (
	"employee_record_update_request_properties_item",
	"employee_record_update_request_benefits_item",
	"employee_record_update_request_salary_structure_compone_item",
	"employee_record_update_request",
)


def reload_doctypes():
	for name in DOCTYPES:
		frappe.reload_doc("one_fm", "doctype", name)


def get_test_employee():
	"""An active employee, preferring one that has a line manager with a user."""
	Employee = frappe.qb.DocType("Employee")
	Manager = frappe.qb.DocType("Employee").as_("m")
	rows = (
		frappe.qb.from_(Employee)
		.join(Manager)
		.on(Manager.name == Employee.reports_to)
		.select(Employee.name)
		.where((Employee.status == "Active") & (Manager.user_id.isnotnull()) & (Manager.user_id != ""))
		.limit(1)
	).run(as_dict=True)
	if rows:
		return rows[0].name
	return frappe.db.get_value("Employee", {"status": "Active"}, "name")


def make_request(employee, **kwargs):
	values = {
		"doctype": DOCTYPE,
		"employee": employee,
		"effective_date_of_change": nowdate(),
		"reason": "Test",
	}
	values.update(kwargs)
	return frappe.get_doc(values)


class TestEmployeeRecordUpdateRequest(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		reload_doctypes()

	# ---- meta ----

	def test_meta_matches_spec_field_by_field(self):
		meta = frappe.get_meta(DOCTYPE)
		data_fields = [f for f in meta.fields if f.fieldtype not in LAYOUT_TYPES]
		self.assertEqual([f.fieldname for f in data_fields], [e[0] for e in EXPECTED_FIELDS])

		for fieldname, fieldtype, options, reqd, read_only, depends_on, fetch_from in EXPECTED_FIELDS:
			field = meta.get_field(fieldname)
			with self.subTest(fieldname=fieldname):
				self.assertEqual(field.fieldtype, fieldtype)
				self.assertEqual(field.options or "", options)
				self.assertEqual(int(field.reqd or 0), reqd)
				self.assertEqual(int(field.read_only or 0), read_only)
				self.assertEqual(field.depends_on or "", depends_on)
				self.assertEqual(field.fetch_from or "", fetch_from)

	def test_field_flags(self):
		meta = frappe.get_meta(DOCTYPE)
		self.assertEqual(meta.get_field("employee").in_list_view, 1)
		self.assertEqual(meta.get_field("employee").in_standard_filter, 1)
		self.assertEqual(meta.get_field("employee_name").in_list_view, 1)
		for fieldname in ("employee", "line_manager", "line_manager_user"):
			self.assertEqual(meta.get_field(fieldname).ignore_user_permissions, 1)
		self.assertEqual(meta.get_field("current_salary_structure").label, "Salary Structure - Current Details")
		self.assertEqual(meta.get_field("salary_new_value").label, "Salary Structure - New Details")
		self.assertEqual(meta.get_field("current_base_salary").label, "Base Salary - Current Details")
		self.assertEqual(meta.get_field("base_new_value").label, "Base Salary - New Details")

	def test_salary_structure_components_section_depends_on_salary_update(self):
		meta = frappe.get_meta(DOCTYPE)
		fields = meta.fields
		index = [f.fieldname for f in fields].index("salary_structure_components")
		section = fields[index - 1]
		self.assertEqual(section.fieldtype, "Section Break")
		self.assertEqual(section.depends_on, "eval:doc.salary_update_required")

	def test_section_titles(self):
		meta = frappe.get_meta(DOCTYPE)
		labels = [f.label for f in meta.fields if f.fieldtype == "Section Break"]
		for label in ("Employee", "Salary Update", "Salary Structure Components", "Changes to Update", "Benefits", "Reason for Changes"):
			self.assertIn(label, labels)

	def test_submittable_naming_and_doctype_properties(self):
		meta = frappe.get_meta(DOCTYPE)
		self.assertEqual(meta.is_submittable, 1)
		self.assertEqual(meta.autoname, "HR-EMP-UPD-.YYYY.-.#####")
		self.assertEqual(meta.track_changes, 1)
		self.assertEqual(meta.quick_entry, 0)
		self.assertEqual(meta.custom, 0)
		self.assertEqual(meta.module, "One Fm")

	def test_permissions_per_role(self):
		meta = frappe.get_meta(DOCTYPE)
		actual = {}
		for perm in meta.permissions:
			self.assertEqual(perm.permlevel or 0, 0)
			actual[perm.role] = {flag for flag in PERMISSION_FLAGS if perm.get(flag)}
			self.assertEqual(perm.if_owner or 0, 1 if perm.role == "Employee" else 0)
		self.assertEqual(set(actual), set(EXPECTED_PERMISSIONS))
		for role, flags in EXPECTED_PERMISSIONS.items():
			with self.subTest(role=role):
				self.assertEqual(actual[role], flags)
		for role, flags in actual.items():
			self.assertNotIn("cancel", flags, f"{role} must not be able to cancel")

	# ---- behaviour ----

	def test_insert_names_and_fetches_employee_details(self):
		employee = get_test_employee()
		if not employee:
			self.skipTest("Need at least 1 active employee for this test.")

		doc = make_request(employee)
		doc.insert(ignore_permissions=True)

		year = getdate(nowdate()).year
		self.assertTrue(
			re.match(rf"^HR-EMP-UPD-{year}-\d{{5}}$", doc.name), f"unexpected name {doc.name}"
		)

		values = frappe.db.get_value(
			"Employee", employee, ["employee_name", "designation", "department", "reports_to"], as_dict=True
		)
		self.assertEqual(doc.employee_name, values.employee_name)
		self.assertEqual(doc.designation, values.designation)
		self.assertEqual(doc.department, values.department)
		self.assertEqual(doc.line_manager, values.reports_to)
		expected_manager_user = (
			frappe.db.get_value("Employee", values.reports_to, "user_id") if values.reports_to else None
		)
		self.assertEqual(doc.line_manager_user, expected_manager_user)

	def test_missing_effective_date_raises_mandatory_error(self):
		employee = get_test_employee()
		if not employee:
			self.skipTest("Need at least 1 active employee for this test.")

		doc = make_request(employee, effective_date_of_change=None)
		self.assertRaises(frappe.MandatoryError, doc.insert, ignore_permissions=True)

	def test_user_without_hr_roles_cannot_create(self):
		employee = get_test_employee()
		if not employee:
			self.skipTest("Need at least 1 active employee for this test.")

		if not frappe.db.exists("User", NO_HR_USER):
			frappe.get_doc({
				"doctype": "User",
				"email": NO_HR_USER,
				"first_name": "ERUR No HR",
				"send_welcome_email": 0,
			}).insert(ignore_permissions=True)

		doc = make_request(employee)
		original_user = frappe.session.user
		frappe.set_user(NO_HR_USER)
		try:
			self.assertRaises(frappe.PermissionError, doc.insert)
		finally:
			frappe.set_user(original_user)


class TestWorkflowStatesPatch(FrappeTestCase):
	EXPECTED_STATES = {
		"Draft": "Danger",
		"Pending Line Manager": "Danger",
		"Pending Finance Manager": "Warning",
		"Pending General Manager": "Warning",
		"Pending Record Update": "Primary",
		"Pending HR Action": "Inverse",
		"Completed": "Success",
		"Rejected by Line Manager": "Danger",
		"Rejected by Finance Manager": "Danger",
		"Rejected by General Manager": "Danger",
	}

	def test_patch_covers_the_ten_states_with_their_styles(self):
		self.assertEqual(states_patch.WORKFLOW_STATES, self.EXPECTED_STATES)

	def test_patch_creates_missing_states_and_is_idempotent(self):
		existing_before = {
			name: frappe.db.get_value("Workflow State", name, "style")
			for name in self.EXPECTED_STATES
			if frappe.db.exists("Workflow State", name)
		}

		states_patch.execute()
		states_patch.execute()

		for name, style in self.EXPECTED_STATES.items():
			with self.subTest(state=name):
				self.assertEqual(frappe.db.count("Workflow State", {"name": name}), 1)
				actual = frappe.db.get_value("Workflow State", name, "style")
				if name in existing_before:
					self.assertEqual(actual, existing_before[name])
				else:
					self.assertEqual(actual, style)

	def test_patch_creates_every_missing_state_with_its_style(self):
		fake = {"ERUR Test State A": "Danger", "ERUR Test State B": "Primary", "ERUR Test State C": "Inverse"}
		for name in fake:
			frappe.db.delete("Workflow State", {"name": name})

		with mock.patch.object(states_patch, "WORKFLOW_STATES", fake):
			states_patch.execute()

		for name, style in fake.items():
			self.assertEqual(frappe.db.get_value("Workflow State", name, "style"), style)

	def test_patch_does_not_restyle_existing_states(self):
		name = "ERUR Test Existing State"
		frappe.db.delete("Workflow State", {"name": name})
		frappe.get_doc({
			"doctype": "Workflow State", "workflow_state_name": name, "style": "Success",
		}).insert(ignore_permissions=True)

		with mock.patch.object(states_patch, "WORKFLOW_STATES", {name: "Danger"}):
			states_patch.execute()

		self.assertEqual(frappe.db.get_value("Workflow State", name, "style"), "Success")


DIFFERENT_DEPARTMENT_MESSAGE = (
	"You are not allowed to create an Employee Record Update Request for an employee from a different "
	"department. The HR User role is required."
)


class TestDepartmentAccess(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		reload_doctypes()
		company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
		departments = frappe.get_all(
			"Department", filters={"is_group": 0, "company": company}, pluck="name", limit=2
		)
		if len(departments) < 2:
			raise unittest.SkipTest("Need 2 leaf Departments for the default company.")
		cls.it_department, cls.hr_department = departments

		cls.it_a = make_employee("erur_it_a@example.com", company=company, department=cls.it_department)
		cls.it_b = make_employee("erur_it_b@example.com", company=company, department=cls.it_department)
		cls.hr_x = make_employee("erur_hr_x@example.com", company=company, department=cls.hr_department)
		cls.no_dept = make_employee("erur_no_dept@example.com", company=company)
		frappe.db.set_value("Employee", cls.no_dept.name, "department", None)
		cls.hr_user = cls.make_user("erur_hr_user@example.com", "HR User")
		cls.hr_manager = cls.make_user("erur_hr_manager@example.com", "HR Manager")
		cls.system_manager = cls.make_user("erur_sys_manager@example.com", "System Manager")
		# Employee role but no Active Employee record.
		cls.no_emp = make_employee("erur_no_emp@example.com", company=company, department=cls.it_department)
		frappe.db.set_value("Employee", cls.no_emp.name, "status", "Left")

	@staticmethod
	def make_user(email, role):
		if not frappe.db.exists("User", email):
			frappe.get_doc({
				"doctype": "User",
				"email": email,
				"first_name": email,
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}).insert(ignore_permissions=True)
		return email

	def create(self, user, employee):
		with self.set_user(user):
			return make_request(employee).insert()

	def assert_blocked(self, user, employee, message=None):
		before = frappe.db.count(DOCTYPE)
		with self.assertRaises(frappe.ValidationError) as cm:
			self.create(user, employee)
		if message:
			self.assertEqual(str(cm.exception), message)
		self.assertEqual(frappe.db.count(DOCTYPE), before)
		return cm.exception

	def test_hr_user_creates_for_any_department(self):
		self.assertTrue(self.create(self.hr_user, self.hr_x.name).name)
		self.assertTrue(self.create(self.hr_user, self.it_b.name).name)

	def test_hr_manager_and_system_manager_are_exempt(self):
		for user in (self.hr_manager, self.system_manager):
			with self.subTest(user=user):
				self.assertTrue(self.create(user, self.hr_x.name).name)

	def test_same_department_user_can_create_read_and_write_but_not_submit(self):
		doc = self.create(self.it_a.user_id, self.it_b.name)
		for ptype, expected in (("read", True), ("write", True), ("submit", False)):
			with self.subTest(ptype=ptype):
				self.assertEqual(
					bool(frappe.has_permission(DOCTYPE, ptype, doc, user=self.it_a.user_id)), expected
				)

	def test_different_department_is_blocked_with_the_ac_message(self):
		self.assert_blocked(self.it_a.user_id, self.hr_x.name, DIFFERENT_DEPARTMENT_MESSAGE)

	def test_target_without_department_is_blocked(self):
		exc = self.assert_blocked(self.it_a.user_id, self.no_dept.name)
		self.assertIn("has no Department", str(exc))

	def test_requester_without_employee_is_blocked(self):
		exc = self.assert_blocked(self.no_emp.user_id, self.it_b.name)
		self.assertIn("not linked to an active Employee", str(exc))

	def test_requester_without_department_is_blocked(self):
		exc = self.assert_blocked(self.no_dept.user_id, self.it_b.name)
		self.assertIn("Your Employee record has no Department", str(exc))

	def test_changing_employee_on_a_draft_is_rechecked(self):
		doc = self.create(self.it_a.user_id, self.it_b.name)
		with self.set_user(self.it_a.user_id):
			doc.employee = self.hr_x.name
			with self.assertRaises(frappe.ValidationError) as cm:
				doc.save()
		self.assertEqual(str(cm.exception), DIFFERENT_DEPARTMENT_MESSAGE)

	def test_saving_without_employee_change_is_not_rechecked(self):
		doc = self.create(self.it_a.user_id, self.it_b.name)
		frappe.share.add(DOCTYPE, doc.name, self.hr_x.user_id, write=1)
		with self.set_user(self.hr_x.user_id):
			doc = frappe.get_doc(DOCTYPE, doc.name)
			doc.reason = "Updated by another department"
			doc.save()
		self.assertEqual(frappe.db.get_value(DOCTYPE, doc.name, "reason"), "Updated by another department")

	def test_other_employee_cannot_read_a_request_they_do_not_own(self):
		doc = self.create(self.it_a.user_id, self.it_b.name)
		self.assertFalse(frappe.has_permission(DOCTYPE, "read", doc, user=self.it_b.user_id))
