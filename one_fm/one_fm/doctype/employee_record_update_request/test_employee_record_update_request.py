# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import re
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate, getdate

from one_fm.patches.v15_0 import create_employee_record_update_request_workflow_states as states_patch

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
}

NO_HR_USER = "erur_no_hr_role@example.com"


def get_test_employee():
	"""An active employee, preferring one that has a line manager with a user."""
	rows = frappe.db.sql(
		"""
		select e.name
		from `tabEmployee` e
		inner join `tabEmployee` m on m.name = e.reports_to
		where e.status = 'Active' and ifnull(m.user_id, '') != ''
		limit 1
		""",
		as_dict=True,
	)
	if rows:
		return rows[0].name
	return frappe.db.get_value("Employee", {"status": "Active"}, "name")


def make_request(employee, **kwargs):
	values = {
		"doctype": DOCTYPE,
		"employee": employee,
		"effective_date_of_change": nowdate(),
	}
	values.update(kwargs)
	return frappe.get_doc(values)


class TestEmployeeRecordUpdateRequest(FrappeTestCase):
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
		for fieldname in ("line_manager", "line_manager_user"):
			self.assertEqual(meta.get_field(fieldname).ignore_user_permissions, 1)

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
		for label in ("Salary Update", "Changes to Update", "Benefits", "Reason for Changes"):
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
