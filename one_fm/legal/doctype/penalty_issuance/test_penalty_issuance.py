# Copyright (c) 2020, ONE FM and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, get_datetime, now_datetime

from one_fm.legal.doctype.penalty_issuance.penalty_issuance import (
	PenaltyIssuance,
	filter_employees,
	get_filtered_employees,
	submit_through_process,
)
from one_fm.patches.v15_0.move_penalty_issuance_to_processa import ISSUER_ROLES, allow_issuers_to_create
from one_fm.patches.v15_0.move_legal_investigation_lifecycle_to_processa import set_third_party_damage


def make_penalty_issuance(**fields):
	employee = frappe.db.get_value("Employee", {"status": "Active"}, ["name", "employee_name", "designation"])
	penalty_type = frappe.db.get_value("Penalty Type", {})
	if not employee or not penalty_type:
		raise frappe.DoesNotExistError("An active Employee and a Penalty Type are needed")

	fields.setdefault("employees", [{"employee_id": employee[0], "employee_name": employee[1], "designation": employee[2]}])
	fields.setdefault("penalty_issuance_details", [{"penalty_type": penalty_type}])
	return frappe.get_doc(
		{
			"doctype": "Penalty Issuance",
			"penalty_category": "Accomodation",
			"penalty_location": "Camp",
			"penalty_occurence_time": add_to_date(now_datetime(), hours=-1),
			**fields,
		}
	)


class TestPenaltyIssuance(FrappeTestCase):
	def test_the_lifecycle_lives_in_the_process(self):
		for method in (
			"validate",
			"after_insert",
			"on_submit",
			"issue_penalty",
			"open_legal_investigation",
			"validate_location",
			"set_site_assignment",
		):
			self.assertNotIn(method, vars(PenaltyIssuance))

	def test_an_issuance_the_process_refused_is_reported(self):
		try:
			issuance = make_penalty_issuance().insert(ignore_permissions=True)
		except frappe.DoesNotExistError as error:
			self.skipTest(str(error))
		with patch("one_fm.grd.processa.complete_action", return_value=True):
			self.assertRaises(frappe.ValidationError, submit_through_process, issuance)

	def test_submit_through_process_submits(self):
		try:
			issuance = make_penalty_issuance().insert(ignore_permissions=True)
		except frappe.DoesNotExistError as error:
			self.skipTest(str(error))

		submit_through_process(issuance)

		self.assertEqual(frappe.db.get_value("Penalty Issuance", issuance.name, "docstatus"), 1)
		self.assertFalse(frappe.db.exists("Penalty", {"penalty_issuance": issuance.name}))

	def test_legacy_damage_flags_become_third_party_damage(self):
		if not frappe.db.has_column("Penalty Issuance", "company_damage"):
			self.skipTest("Legacy damage columns are not on this site")
		try:
			flagged = make_penalty_issuance().insert(ignore_permissions=True)
			clean = make_penalty_issuance().insert(ignore_permissions=True)
		except frappe.DoesNotExistError as error:
			self.skipTest(str(error))
		table = frappe.qb.DocType("Penalty Issuance")
		frappe.qb.update(table).set(table.company_damage, 1).where(table.name == flagged.name).run()

		set_third_party_damage("Penalty Issuance")

		self.assertEqual(frappe.db.get_value("Penalty Issuance", flagged.name, "third_party_damage"), 1)
		self.assertEqual(frappe.db.get_value("Penalty Issuance", clean.name, "third_party_damage"), 0)

	def test_issuers_may_create_what_the_process_creates(self):
		allow_issuers_to_create("Legal Investigation", "Penalty")
		for doctype in ("Legal Investigation", "Penalty"):
			for role in ISSUER_ROLES:
				with self.subTest(doctype=doctype, role=role):
					self.assertEqual(
						frappe.db.get_value(
							"Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}, "create"
						),
						1,
					)

	def test_employee_filter_lists_the_shift_on_the_occurrence_date(self):
		assignment = frappe.db.get_value(
			"Shift Assignment", {"shift": ["is", "set"]}, ["employee", "shift", "start_date"], as_dict=True
		)
		if not assignment:
			self.skipTest("No Shift Assignment on this site")
		designation = frappe.db.get_value("Employee", assignment.employee, "designation")
		occurrence = f"{assignment.start_date} 10:00:00"

		rows = get_filtered_employees(assignment.shift, occurrence, as_dict=1)
		self.assertIn(assignment.employee, [row["employee"] for row in rows])
		self.assertEqual(next(r for r in rows if r["employee"] == assignment.employee)["designation"], designation)

		filters = {"shift": assignment.shift, "penalty_occurence_time": occurrence}
		searched = filter_employees("Employee", assignment.employee, "name", 0, 20, filters)
		self.assertIn(assignment.employee, [row[0] for row in searched])
		self.assertEqual(filter_employees("Employee", "no-such-employee-xyz", "name", 0, 20, filters), [])


ISSUER_USER = "penalty-issuance-issuer@example.com"


class TestPenaltyIssuer(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		try:
			make_penalty_issuance()
		except frappe.DoesNotExistError as error:
			raise unittest.SkipTest(str(error))

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_the_issuer_is_the_session_user_s_employee(self):
		employee = frappe.db.get_value("Employee", {"status": "Active"}, ["name", "employee_name"])
		if not frappe.db.exists("User", ISSUER_USER):
			frappe.get_doc(
				{"doctype": "User", "email": ISSUER_USER, "first_name": "Issuer", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.db.set_value("Employee", employee[0], "user_id", ISSUER_USER)

		issuance = make_penalty_issuance(
			issuing_employee="HR-EMP-SPOOFED", issuing_time="2020-01-01 00:00:00", location=None
		)
		frappe.set_user(ISSUER_USER)
		issuance.run_method("before_insert")

		self.assertEqual(issuance.issuing_employee, employee[0])
		self.assertEqual(issuance.employee_name, employee[1])
		self.assertGreater(get_datetime(issuance.issuing_time), add_to_date(now_datetime(), minutes=-1))
		self.assertEqual(issuance.location, issuance.penalty_location)

	def test_a_caller_without_an_employee_keeps_the_issuer_it_set(self):
		if frappe.db.exists("Employee", {"user_id": "Administrator"}):
			self.skipTest("Administrator is linked to an Employee here")
		employee = frappe.db.get_value("Employee", {"status": "Active"})
		issuance = make_penalty_issuance(issuing_employee=employee)
		issuance.run_method("before_insert")
		self.assertEqual(issuance.issuing_employee, employee)
