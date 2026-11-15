# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from one_fm.api.v1 import configuration
from one_fm.api.v2 import penalty_issuance as api

ISSUER = "pi-api-issuer@example.com"
OUTSIDER = "pi-api-outsider@example.com"
PENALTY_TYPE = "PI API Test Violation"
SERVICE = "Penalty Issuance"


def _call(method, *args, **kwargs):
	frappe.local.response = frappe._dict()
	method(*args, **kwargs)
	return frappe.local.response


def _make_user(email, roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"roles": [{"role": role} for role in roles],
			}
		).insert(ignore_permissions=True)
	else:
		frappe.get_doc("User", email).add_roles(*roles)
	return email


def _setup_fixtures(cls):
	# user_app_service commits; keep the fixtures inside the class rollback.
	no_commit = patch("frappe.db.commit")
	no_commit.start()
	cls.addClassCleanup(no_commit.stop)

	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active", "employee_name": ["is", "set"]},
		fields=["name", "employee_id", "employee_name"],
		order_by="creation desc",
		limit=3,
	)
	if len(employees) < 3:
		raise unittest.SkipTest("needs three active employees")
	cls.issuer_employee, cls.outsider_employee, cls.target = employees

	_make_user(ISSUER, ["Employee", "Penalty Issuer"])
	_make_user(OUTSIDER, ["Employee"])
	frappe.db.set_value("Employee", cls.issuer_employee.name, "user_id", ISSUER)
	frappe.db.set_value("Employee", cls.outsider_employee.name, "user_id", OUTSIDER)

	if not frappe.db.exists("Penalty Type", PENALTY_TYPE):
		frappe.get_doc(
			{"doctype": "Penalty Type", "penalty_name": PENALTY_TYPE, "penalty_name_arabic": "test"}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("App Service Group", "Legal"):
		frappe.get_doc(
			{"doctype": "App Service Group", "group_name": "Legal", "icon": "shield-check-outline", "status": "Active"}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("App Service", SERVICE):
		frappe.get_doc(
			{
				"doctype": "App Service",
				"service": SERVICE,
				"service_group": "Legal",
				"icon": "alert-outline",
				"status": "Active",
				"role": "Penalty Issuer",
				"auto_assign": 1,
				"assign_to_timesheet_employees": 1,
				"assign_to_non_timesheet_employees": 1,
			}
		).insert(ignore_permissions=True)


class TestPenaltyIssuanceAPI(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_setup_fixtures(cls)

	def _payload(self, **overrides):
		payload = {
			"penalty_category": "Accommodation",
			"penalty_occurence_time": str(add_to_date(now_datetime(), hours=-1)),
			"penalty_location": "Camp gate",
			"third_party_damage": 0,
			"shift": "should be dropped",
			"employees": [{"employee_id": self.target.name}],
			"penalty_issuance_details": [
				{
					"penalty_type": PENALTY_TYPE,
					"exact_notes": "Late",
					"attachments": {"attachment_name": "../../evil.txt", "attachment": "aGVsbG8="},
				}
			],
		}
		payload.update(overrides)
		return payload

	def test_outsider_is_denied_every_endpoint(self):
		with self.set_user(OUTSIDER):
			calls = [
				(api.search_employees, ("abcd",)),
				(api.get_penalty_types, ()),
				(api.get_shifts, ()),
				(api.get_current_assignment, (self.target.name, str(now_datetime()))),
				(api.submit_penalty_issuance, (self._payload(),)),
			]
			for method, args in calls:
				self.assertEqual(_call(method, *args).status_code, 403, method.__name__)

	def test_search_employees(self):
		with self.set_user(ISSUER):
			found = _call(api.search_employees, self.target.employee_name)
			self.assertEqual(found.status_code, 200)
			self.assertIn(self.target.name, [row["name"] for row in found.data])
			self.assertTrue({"employee_id", "employee_name", "designation"} <= set(found.data[0]))

			self.assertEqual(_call(api.search_employees, "ab").get("data"), None)

	def test_get_penalty_types(self):
		with self.set_user(ISSUER):
			result = _call(api.get_penalty_types)
		self.assertEqual(result.status_code, 200)
		self.assertIn(PENALTY_TYPE, [row["name"] for row in result.data])

	def test_get_shifts(self):
		with self.set_user(ISSUER):
			result = _call(api.get_shifts)
		self.assertEqual(result.status_code, 200)
		for row in result.get("data") or []:
			self.assertTrue({"shift", "site", "project", "site_location"} <= set(row))

	def test_get_current_assignment(self):
		assignment = frappe.get_all(
			"Shift Assignment",
			filters={"docstatus": 1, "status": "Active", "shift": ["is", "set"], "start_datetime": ["is", "set"]},
			fields=["employee", "shift", "start_datetime"],
			limit=1,
		)
		if not assignment:
			self.skipTest("no submitted Shift Assignment")
		with self.set_user(ISSUER):
			result = _call(api.get_current_assignment, assignment[0].employee, str(assignment[0].start_datetime))
		self.assertEqual(result.status_code, 200)
		self.assertTrue(result.data["shift"])

	def test_submit_creates_the_issuance(self):
		with self.set_user(ISSUER):
			result = _call(api.submit_penalty_issuance, frappe.as_json(self._payload()))

		self.assertEqual(result.status_code, 201, result.get("error"))
		doc = frappe.get_doc("Penalty Issuance", result.data["name"])
		self.assertEqual(doc.penalty_category, "Accomodation")
		self.assertFalse(doc.shift)
		self.assertEqual([row.employee_id for row in doc.employees], [self.target.name])
		if result.data["process_status"] != "Errored":
			self.assertEqual(result.data["docstatus"], 1)

		file_url = doc.penalty_issuance_details[0].attachments
		self.assertTrue(file_url.startswith("/private/files/"), file_url)
		# The client file name cannot leave the private files folder.
		self.assertEqual(file_url.count("/"), 3, file_url)

	def test_duplicate_employee_is_rejected(self):
		payload = self._payload(employees=[{"employee_id": self.target.name}, {"employee_id": self.target.name}])
		with self.set_user(ISSUER):
			result = _call(api.submit_penalty_issuance, payload)
		self.assertEqual(result.status_code, 400)
		self.assertIn("Employee already added", result.error)

	def test_unknown_category_and_empty_lists_are_rejected(self):
		with self.set_user(ISSUER):
			for payload in (
				self._payload(penalty_category="Other"),
				self._payload(employees=[]),
				self._payload(penalty_issuance_details=[]),
			):
				self.assertEqual(_call(api.submit_penalty_issuance, payload).status_code, 400)


class TestPenaltyIssuanceTile(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_setup_fixtures(cls)

	def _tiles(self, method):
		data = _call(method).data
		return [row.get("name") or row.get("service") for row in (data["service_detail"] if isinstance(data, dict) else data)]

	def test_outsider_does_not_see_the_tile(self):
		with self.set_user(OUTSIDER):
			self.assertIn(SERVICE, configuration.services_hidden_by_role())
			self.assertNotIn(SERVICE, self._tiles(configuration.app_service))
			self.assertNotIn(SERVICE, self._tiles(configuration.user_app_service))

	def test_issuer_gets_the_tile_and_loses_it_with_the_role(self):
		with self.set_user(ISSUER):
			self.assertIn(SERVICE, self._tiles(configuration.app_service))
			self.assertIn(SERVICE, self._tiles(configuration.user_app_service))

		frappe.get_doc("User", ISSUER).remove_roles("Penalty Issuer")
		with self.set_user(ISSUER):
			self.assertNotIn(SERVICE, self._tiles(configuration.user_app_service))
