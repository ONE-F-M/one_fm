# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestProjectManpowerRequest(FrappeTestCase):
	def setUp(self):
		self.test_email = f"test_recruiter_{frappe.generate_hash(length=8)}@example.com"
		self.recruiter = _make_user(self.test_email, "Recruiter")
		
		# Ensure a project exists to satisfy mandatory validation on New Project reason
		project = frappe.db.get_value("Project", {}, "name")
		if not project:
			project_doc = frappe.get_doc({
				"doctype": "Project",
				"project_name": "Test Project"
			})
			project_doc.insert(ignore_permissions=True)
			project = project_doc.name

		self.pmr = frappe.get_doc({
			"doctype": "Project Manpower Request",
			"title": "Test PMR Recruitment",
			"reason": "New Project",
			"count": 1,
			"recruiter": self.recruiter,
			"project_allocation": project
		})
		self.pmr.flags.ignore_mandatory = True
		self.pmr.insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()

	def test_assign_recruiter_creates_todo_only_once(self):
		# Initially assigned
		self.pmr.assign_recruiter()
		
		todos = frappe.get_all("ToDo", {
			"reference_type": "Project Manpower Request",
			"reference_name": self.pmr.name,
			"allocated_to": self.recruiter,
			"status": "Open"
		})
		
		self.assertEqual(len(todos), 1)
		
		# Second assignment attempt should not create a duplicate
		self.pmr.assign_recruiter()
		
		todos_after = frappe.get_all("ToDo", {
			"reference_type": "Project Manpower Request",
			"reference_name": self.pmr.name,
			"allocated_to": self.recruiter,
			"status": "Open"
		})
		
		self.assertEqual(len(todos_after), 1)

	def test_gender_and_nationality_select_fields(self):
		meta = frappe.get_meta("Project Manpower Request")
		
		# Gender field check
		gender_df = meta.get_field("gender")
		self.assertEqual(gender_df.fieldtype, "Autocomplete")
		gender_opts = gender_df.options.split("\n")
		self.assertIn("Any", gender_opts)
		self.assertIn("Male", gender_opts)
		self.assertIn("Female", gender_opts)
		
		# Nationality field check
		nationality_df = meta.get_field("nationality")
		self.assertEqual(nationality_df.fieldtype, "Autocomplete")
		nationality_opts = nationality_df.options.split("\n")
		self.assertIn("Any", nationality_opts)
		self.assertIn("African", nationality_opts)
		self.assertIn("Asian", nationality_opts)
		
		# Check that custom records do NOT exist universally in the DB
		self.assertFalse(frappe.db.exists("Nationality", "Any"))
		self.assertFalse(frappe.db.exists("Nationality", "African"))
		self.assertFalse(frappe.db.exists("Nationality", "Asian"))
		self.assertFalse(frappe.db.exists("Gender", "Any"))

	def test_get_autocomplete_options(self):
		from one_fm.one_fm.doctype.project_manpower_request.project_manpower_request import get_autocomplete_options
		frappe.set_user("Administrator")
		res = get_autocomplete_options()
		self.assertIn("nationalities", res)
		self.assertIn("genders", res)
		self.assertTrue(len(res["nationalities"]) > 0)
		self.assertTrue(len(res["genders"]) > 0)

	def test_validate_change_request_reason(self):
		# Setup initial workflow state as Awaiting Recruiter Approval
		self.pmr.workflow_state = "Awaiting Recruiter Approval"
		self.pmr.save(ignore_permissions=True)
		
		# Attempt to transition back to Draft without a reason - should raise ValidationError
		self.pmr.workflow_state = "Draft"
		self.pmr.reason_for_rejection = None
		self.assertRaises(frappe.ValidationError, self.pmr.save, ignore_permissions=True)
		
		# Reload to avoid TimestampMismatchError after the failed save
		self.pmr = frappe.get_doc("Project Manpower Request", self.pmr.name)
		self.pmr.flags.ignore_mandatory = True
		
		# Transition back to Draft with a reason - should succeed
		self.pmr.workflow_state = "Draft"
		self.pmr.reason_for_rejection = "Please clarify details"
		self.pmr.save(ignore_permissions=True)
		self.assertEqual(self.pmr.workflow_state, "Draft")
		self.assertEqual(self.pmr.reason_for_rejection, "Please clarify details")

		# Now test for In Process state transition to Draft
		self.pmr = frappe.get_doc("Project Manpower Request", self.pmr.name)
		self.pmr.flags.ignore_mandatory = True
		frappe.db.set_value("Project Manpower Request", self.pmr.name, "workflow_state", "In Process")
		self.pmr.reload()

		# Transition from In Process back to Draft WITHOUT a reason - should succeed
		self.pmr.workflow_state = "Draft"
		self.pmr.reason_for_rejection = None
		self.pmr.save(ignore_permissions=True)
		self.assertEqual(self.pmr.workflow_state, "Draft")

	def test_conditional_project_mandatory(self):
		# Use a designation name from database or create one to avoid mandatory field error
		designation = frappe.db.get_value("Designation", {}, "name")
		if not designation:
			doc = frappe.get_doc({"doctype": "Designation", "designation_name": "Test Designation"})
			doc.insert(ignore_permissions=True)
			designation = doc.name
		self.pmr.designation = designation
		
		# Test success case: project_allocation is optional for exempt reasons
		self.pmr.reason = "Annual Leave Reliever"
		self.pmr.project_allocation = None
		self.pmr.flags.ignore_mandatory = False
		self.pmr.save(ignore_permissions=True)
		self.assertEqual(self.pmr.project_allocation, None)
		
		# Test fail case: project_allocation is mandatory for non-exempt reasons
		self.pmr.reason = "New Project"
		self.pmr.project_allocation = None
		self.assertRaises(frappe.MandatoryError, self.pmr.save, ignore_permissions=True)

def _make_user(email, first_name="Test"):
	if frappe.db.exists("User", email):
		return email
	user = frappe.get_doc({
		"doctype": "User",
		"email": email,
		"first_name": first_name,
		"send_welcome_email": 0
	})
	user.insert(ignore_permissions=True)
	return user.name
