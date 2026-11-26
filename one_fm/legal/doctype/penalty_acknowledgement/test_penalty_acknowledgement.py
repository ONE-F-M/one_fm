# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.utils import add_to_date, now_datetime

from one_fm.legal.doctype.penalty_acknowledgement.penalty_acknowledgement import get_pending_penalty_notices
from one_fm.tests.test_penalty_hr_enquiry_bpmn_scripts import PenaltyFixtures

ISSUER_ONLY_USER = "penalty-ack-issuer@example.com"


def make_penalty_acknowledgement(issuance, employee, **fields):
	return frappe.get_doc(
		{
			"doctype": "Penalty Acknowledgement",
			"penalty_issuance": issuance.name,
			"employee": employee.name,
			"issuing_employee": issuance.issuing_employee,
			"issuer_name": issuance.employee_name,
			"penalty_category": issuance.penalty_category,
			"penalty_occurence_time": issuance.penalty_occurence_time,
			**fields,
		}
	).insert(ignore_permissions=True)


class TestPenaltyAcknowledgement(PenaltyFixtures):
	def submitted_issuance(self, **fields):
		issuance = self.make_penalty_issuance(**fields)
		issuance.db_set("docstatus", 1)
		return issuance

	def pending_names(self, employee):
		return [row.name for row in get_pending_penalty_notices(employee.name)]

	def test_one_record_per_issuance_and_employee(self):
		issuance = self.submitted_issuance()
		make_penalty_acknowledgement(issuance, self.first)

		self.assertRaises(frappe.DuplicateEntryError, make_penalty_acknowledgement, issuance, self.first)

	def test_every_unacknowledged_notice_is_pending_however_old(self):
		old = self.submitted_issuance()
		recent = self.submitted_issuance()
		old_ack = make_penalty_acknowledgement(
			old, self.first, penalty_occurence_time=add_to_date(now_datetime(), days=-400)
		)
		recent_ack = make_penalty_acknowledgement(recent, self.first)

		pending = get_pending_penalty_notices(self.first.name)
		names = [row.name for row in pending]
		self.assertLess(names.index(old_ack.name), names.index(recent_ack.name))
		self.assertEqual(
			set(pending[0].keys()),
			{"name", "penalty_issuance", "issuer_name", "penalty_category", "penalty_occurence_time"},
		)

	def test_acknowledged_cancelled_and_other_employees_rows_are_left_out(self):
		acknowledged = make_penalty_acknowledgement(self.submitted_issuance(), self.first, acknowledged=1)
		cancelled = self.submitted_issuance()
		cancelled_ack = make_penalty_acknowledgement(cancelled, self.first)
		cancelled.db_set("docstatus", 2)
		draft_ack = make_penalty_acknowledgement(self.make_penalty_issuance(), self.first)
		other = make_penalty_acknowledgement(self.submitted_issuance(), self.second)

		pending = self.pending_names(self.first)
		for name in (acknowledged.name, cancelled_ack.name, draft_ack.name, other.name):
			self.assertNotIn(name, pending)
		self.assertIn(other.name, self.pending_names(self.second))

	def test_a_penalty_issuer_can_create_one(self):
		if not frappe.db.exists("User", ISSUER_ONLY_USER):
			frappe.get_doc(
				{"doctype": "User", "email": ISSUER_ONLY_USER, "first_name": "Ack Issuer", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		user = frappe.get_doc("User", ISSUER_ONLY_USER)
		user.add_roles("Penalty Issuer")
		issuance = self.submitted_issuance()

		frappe.set_user(ISSUER_ONLY_USER)
		try:
			ack = frappe.get_doc(
				{"doctype": "Penalty Acknowledgement", "penalty_issuance": issuance.name, "employee": self.first.name}
			).insert()
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(ack.name, f"{issuance.name}-{self.first.name}")
		self.assertEqual(ack.employee_name, self.first.employee_name)
