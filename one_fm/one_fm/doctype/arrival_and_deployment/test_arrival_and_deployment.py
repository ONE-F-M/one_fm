# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestArrivalandDeployment(FrappeTestCase):
	def test_arrival_date_mandatory_for_onboarding(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_name = "Test Candidate"
		doc.onboarding_officer = "Administrator"
		doc.general_services = "Administrator"
		doc.warehouse = "Administrator"
		doc.workflow_state = "Pending Onboarding"
		
		# Should throw exception because arrival_date is missing
		self.assertRaises(frappe.ValidationError, doc.validate)
		
		# Once arrival_date is set, it should pass (for local hire since no CCP)
		doc.arrival_date = frappe.utils.today()
		doc.validate() # Should not raise exception
		
	def test_overseas_flight_details_mandatory(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_name = "Overseas Candidate"
		doc.candidate_country_process = "CCP-TEST-001"
		doc.onboarding_officer = "Administrator"
		doc.transportation_manager = "Administrator"
		doc.finance = "Administrator"
		doc.general_services = "Administrator"
		doc.warehouse = "Administrator"
		doc.workflow_state = "Pending Onboarding"
		doc.arrival_date = frappe.utils.today()
		
		# Should throw exception because flight details are missing for overseas
		self.assertRaises(frappe.ValidationError, doc.validate)


DEPARTMENT_USERS = {
	"recruiter": "test_ad_recruiter@example.com",
	"onboarding_officer": "test_ad_onboarding@example.com",
	"warehouse": "test_ad_warehouse@example.com",
	"general_services": "test_ad_general_services@example.com",
	"operations_admin": "test_ad_operations@example.com",
}


class TestArrivalWorkflowAssignments(FrappeTestCase):
	def setUp(self):
		for email in DEPARTMENT_USERS.values():
			_make_user(email)
		self.ard = frappe.get_doc({
			"doctype": "Arrival and Deployment",
			"candidate_name": "Test Local Arrival",
			"arrival_date": frappe.utils.add_days(frappe.utils.today(), 3),
			**DEPARTMENT_USERS,
		}).insert()

	def test_draft_is_assigned_to_the_recruiter(self):
		self.assertEqual(self.ard.workflow_state, "Draft")
		self.assertEqual(_open_assignees(self.ard.doctype, self.ard.name), {DEPARTMENT_USERS["recruiter"]})

	def test_pending_onboarding_moves_the_task_to_the_onboarding_officer(self):
		self.ard.workflow_state = "Pending Onboarding"
		self.ard.save()

		self.assertEqual(_open_assignees(self.ard.doctype, self.ard.name), {DEPARTMENT_USERS["onboarding_officer"]})

	def test_submit_to_support_departments_needs_every_department_user(self):
		self.ard.workflow_state = "Pending Onboarding"
		self.ard.save()
		self.ard.warehouse = None
		self.ard.workflow_state = "Pending Support Departments"

		with self.assertRaises(frappe.ValidationError) as context:
			self.ard.save()
		self.assertIn("Warehouse", str(context.exception))
		self.assertFalse(frappe.db.exists("Arrival Acknowledgement", {"arrival_and_deployment": self.ard.name}))

	def test_each_department_acknowledgement_is_assigned_and_closed_on_acknowledge(self):
		from frappe.model.workflow import apply_workflow

		self.ard.workflow_state = "Pending Onboarding"
		self.ard.save()
		self.ard.workflow_state = "Pending Support Departments"
		self.ard.save()

		acks = frappe.get_all("Arrival Acknowledgement", filters={"arrival_and_deployment": self.ard.name}, fields=["name", "department", "assigned_to"])
		self.assertEqual({a.department for a in acks}, {"Warehouse", "General Services", "Operations"})
		for ack in acks:
			self.assertEqual(_open_assignees("Arrival Acknowledgement", ack.name), {ack.assigned_to})

		warehouse = next(a for a in acks if a.department == "Warehouse")
		ack = apply_workflow(frappe.get_doc("Arrival Acknowledgement", warehouse.name), "Acknowledge")

		self.assertEqual(ack.status, "Acknowledged")
		self.assertEqual(ack.acknowledged_by, frappe.session.user)
		self.assertEqual(_open_assignees("Arrival Acknowledgement", ack.name), set())

	def test_transportation_keeps_its_task_until_arrival_is_confirmed(self):
		ack = frappe.get_doc({
			"doctype": "Arrival Acknowledgement",
			"arrival_and_deployment": self.ard.name,
			"department": "Transportation",
			"assigned_to": DEPARTMENT_USERS["warehouse"],
		}).insert()
		ack.reload()
		ack.status = "Acknowledged"
		ack.save()
		self.assertEqual(_open_assignees(ack.doctype, ack.name), {DEPARTMENT_USERS["warehouse"]})

		ack.reload()
		ack.arrival_confirmation = "Arrived"
		ack.save()
		self.assertEqual(_open_assignees(ack.doctype, ack.name), set())


def _make_user(email):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}).insert()
	return email


def _open_assignees(doctype, name):
	return set(frappe.get_all("ToDo", filters={"reference_type": doctype, "reference_name": name, "status": "Open"}, pluck="allocated_to"))
