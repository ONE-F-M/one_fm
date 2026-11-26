"""Pending penalty notices on the mobile check-in screen: the get_site_location payload and
acknowledge_penalties. Needs the Penalty Acknowledgement DocType, so runs after migrate."""

from unittest.mock import MagicMock, patch

import frappe

from one_fm.api.v1.face_recognition import acknowledge_penalties, get_site_location
from one_fm.legal.doctype.penalty_acknowledgement.test_penalty_acknowledgement import make_penalty_acknowledgement
from one_fm.tests.test_penalty_hr_enquiry_bpmn_scripts import PenaltyFixtures

NO_EMPLOYEE_USER = "penalty-notice-no-employee@example.com"


class TestPenaltyNoticeCheckinApi(PenaltyFixtures):
	def setUp(self):
		frappe.local.response = frappe._dict()
		self.issuance = self.make_penalty_issuance()
		self.issuance.db_set("docstatus", 1)
		self.own = make_penalty_acknowledgement(self.issuance, self.first)
		self.others = make_penalty_acknowledgement(self.issuance, self.second)

	def tearDown(self):
		frappe.set_user("Administrator")

	def acknowledge_as_first(self, names):
		frappe.local.response = frappe._dict()
		frappe.set_user(self.first.user_id)
		try:
			acknowledge_penalties(names=frappe.as_json(names))
		finally:
			frappe.set_user("Administrator")
		return frappe.local.response

	def test_only_the_callers_named_rows_are_acknowledged(self):
		reply = self.acknowledge_as_first([self.own.name, self.others.name])

		self.assertEqual(reply.status_code, 200)
		self.assertEqual(reply.data, {"acknowledged": 1})
		own = frappe.db.get_value("Penalty Acknowledgement", self.own.name, ["acknowledged", "acknowledged_on"], as_dict=True)
		self.assertEqual(own.acknowledged, 1)
		self.assertTrue(own.acknowledged_on)
		self.assertEqual(frappe.db.get_value("Penalty Acknowledgement", self.others.name, "acknowledged"), 0)

	def test_a_second_call_acknowledges_nothing(self):
		self.acknowledge_as_first([self.own.name])
		self.assertEqual(self.acknowledge_as_first([self.own.name]).data, {"acknowledged": 0})

	def test_a_user_without_an_employee_is_refused(self):
		if not frappe.db.exists("User", NO_EMPLOYEE_USER):
			frappe.get_doc(
				{"doctype": "User", "email": NO_EMPLOYEE_USER, "first_name": "No Employee", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(NO_EMPLOYEE_USER)
		acknowledge_penalties(names=[self.own.name])
		frappe.set_user("Administrator")

		self.assertEqual(frappe.local.response.status_code, 403)
		self.assertEqual(frappe.db.get_value("Penalty Acknowledgement", self.own.name, "acknowledged"), 0)

	def site_location_payload(self):
		employee_id = frappe.db.get_value("Employee", self.first.name, "employee_id")
		shift = MagicMock(is_replaced=0, shift=None)
		shift.get_next_checkin_log_type.return_value = "IN"
		shift.after_4hrs.return_value = False
		shift.as_dict.return_value = {}
		location = frappe._dict(name="Test Site", latitude=29.37, longitude=47.97, geofence_radius=100)
		module = "one_fm.api.v1.face_recognition"
		frappe.local.response = frappe._dict()
		with patch(f"{module}.check_own_employee", return_value=True), patch(
			f"{module}.get_current_shift", return_value={"type": "On Time", "data": shift, "upcoming_shifts": []}
		), patch(f"{module}.is_attendance_request_exists", return_value=False), patch(
			f"{module}.get_shift_site_location", return_value=location
		):
			get_site_location(employee_id=employee_id, latitude=29.37, longitude=47.97)
		self.assertEqual(frappe.local.response.status_code, 200, frappe.local.response.get("error"))
		return frappe.local.response.data

	def test_the_check_in_payload_lists_pending_notices_until_acknowledged(self):
		if not frappe.db.get_value("Employee", self.first.name, "employee_id"):
			self.skipTest("the fixture employee has no employee_id")
		pending = self.site_location_payload()["pending_penalties"]
		self.assertEqual([row.name for row in pending], [self.own.name])
		self.assertEqual(pending[0].penalty_issuance, self.issuance.name)

		self.acknowledge_as_first([self.own.name])
		self.assertEqual(self.site_location_payload()["pending_penalties"], [])
