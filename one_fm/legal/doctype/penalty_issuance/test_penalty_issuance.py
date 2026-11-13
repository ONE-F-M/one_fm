# Copyright (c) 2020, ONE FM and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, get_datetime, now_datetime

from one_fm.legal.doctype.penalty_issuance.penalty_issuance import PenaltyIssuance, submit_through_process
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
	def test_submitting_no_longer_routes_in_the_controller(self):
		for method in ("on_submit", "issue_penalty", "open_legal_investigation"):
			self.assertFalse(hasattr(PenaltyIssuance, method), msg=method)

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


ISSUER_USER = "penalty-issuance-issuer@example.com"


class TestPenaltyIssuanceValidations(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		try:
			make_penalty_issuance()
		except frappe.DoesNotExistError as error:
			raise unittest.SkipTest(str(error))

	def tearDown(self):
		frappe.set_user("Administrator")

	def assert_refused(self, issuance, message):
		with self.assertRaises(frappe.ValidationError) as caught:
			issuance.validate()
		self.assertIn(message, str(caught.exception))

	def test_a_complete_issuance_passes(self):
		make_penalty_issuance(issuing_time=now_datetime()).validate()

	def test_at_least_one_employee(self):
		self.assert_refused(make_penalty_issuance(employees=[]), "at least one employee")

	def test_an_employee_may_be_added_only_once(self):
		issuance = make_penalty_issuance()
		issuance.append("employees", {"employee_id": issuance.employees[0].employee_id})
		self.assert_refused(issuance, "Employee already added")

	def test_at_least_one_violation(self):
		self.assert_refused(make_penalty_issuance(penalty_issuance_details=[]), "at least one violation")

	def test_the_occurrence_cannot_be_in_the_future(self):
		issuance = make_penalty_issuance(
			issuing_time=now_datetime(), penalty_occurence_time=add_to_date(now_datetime(), hours=1)
		)
		self.assert_refused(issuance, "future")

	def test_the_occurrence_must_be_within_ten_days_of_issuing(self):
		issued = now_datetime()
		self.assert_refused(
			make_penalty_issuance(issuing_time=issued, penalty_occurence_time=add_to_date(issued, days=-11)),
			"previous 10 days",
		)
		make_penalty_issuance(issuing_time=issued, penalty_occurence_time=add_to_date(issued, days=-9)).validate()

	def test_the_window_is_measured_from_issuing_not_from_submitting(self):
		issued = add_to_date(now_datetime(), days=-30)
		make_penalty_issuance(issuing_time=issued, penalty_occurence_time=add_to_date(issued, days=-2)).validate()

	def test_performance_needs_a_shift(self):
		self.assert_refused(make_penalty_issuance(penalty_category="Performance"), "Shift and Site are required")

	def test_performance_takes_site_project_and_location_from_the_shift(self):
		shift = frappe.db.get_value("Operations Shift", {"site": ["is", "set"]}, ["name", "site", "project"])
		if not shift:
			self.skipTest("No Operations Shift with a site")
		issuance = make_penalty_issuance(penalty_category="Performance", shift=shift[0], site="Wrong", project=None)
		issuance.validate()

		self.assertEqual((issuance.site, issuance.project), (shift[1], shift[2]))
		self.assertEqual(issuance.site_location, frappe.db.get_value("Operations Site", shift[1], "site_location"))

	def test_other_categories_carry_no_site_assignment(self):
		issuance = make_penalty_issuance(shift="Any", site="Any", project="Any", site_location="Any")
		issuance.validate()
		for fieldname in ("shift", "site", "project", "site_location"):
			self.assertFalse(issuance.get(fieldname), msg=fieldname)

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
