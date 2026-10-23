import base64
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.api.v1 import (
	face_recognition,
	leave_application,
	notification,
	resignation,
	shift_request,
	user,
	utils,
)
from one_fm.one_fm.doctype.employee_resignation.test_employee_resignation_api import (
	_make_employee,
	_make_user,
)

UNEXPOSED_ENDPOINTS = (
	"one_fm.api.v1.authentication.update_password",
	"one_fm.api.v1.authentication.set_password",
	"one_fm.api.v1.authentication.get_otp",
	"one_fm.api.v1.authentication.new_forgot_password",
	"one_fm.api.v1.authentication.validate_employee_id",
	"one_fm.api.v1.flutter.roster.get_staff",
	"one_fm.api.v1.salary_slip.salary_slip_details",
	"one_fm.api.v1.web.forced_checkin",
	"one_fm.api.v1.user.get_user_details",
	"one_fm.api.v2.authentication.update_password",
	"one_fm.api.v2.authentication.set_password",
	"one_fm.api.v2.authentication.user_login",
	"one_fm.api.v2.flutter.roster.get_staff",
	"one_fm.api.v2.flutter.roster.change_employee_detail",
	"one_fm.api.v2.salary_slip.salary_slip_details",
	"one_fm.api.v2.utils.update_employee",
	"one_fm.api.v2.web.forced_checkin",
)


def status_code():
	return frappe.local.response.get("http_status_code")


class TestOwnEmployeeApi(FrappeTestCase):
	def setUp(self):
		frappe.local.response = frappe._dict()
		self.user_a = _make_user("test-own-employee-a@example.com", "Own A")
		self.user_b = _make_user("test-own-employee-b@example.com", "Own B")
		for name in (self.user_a, self.user_b):
			frappe.get_doc("User", name).add_roles("Employee")
		self.employee_a = _make_employee("OwnA", self.user_a)
		self.employee_b = _make_employee("OwnB", self.user_b)
		self.id_a = frappe.db.get_value("Employee", self.employee_a, "employee_id") or self.employee_a
		self.id_b = frappe.db.get_value("Employee", self.employee_b, "employee_id") or self.employee_b

	def call_as_a(self, method, *args, **kwargs):
		frappe.local.response = frappe._dict()
		with self.set_user(self.user_a):
			method(*args, **kwargs)
		return status_code()

	def test_get_own_employee_accepts_own_id_and_refuses_another(self):
		with self.set_user(self.user_a):
			self.assertEqual(utils.get_own_employee(self.id_a).name, self.employee_a)
			self.assertEqual(utils.get_own_employee(self.employee_a).name, self.employee_a)
			self.assertEqual(utils.get_own_employee().name, self.employee_a)
			self.assertIsNone(utils.get_own_employee(self.id_b))

	def test_get_own_employee_is_none_without_an_employee(self):
		no_employee = _make_user("test-own-employee-none@example.com", "Own None")
		with self.set_user(no_employee):
			self.assertIsNone(utils.get_own_employee())

	def test_read_endpoints_refuse_another_employee(self):
		self.assertEqual(self.call_as_a(leave_application.get_leave_balance, employee_id=self.id_b), 403)
		self.assertEqual(self.call_as_a(leave_application.get_leave_types, employee_id=self.id_b), 403)
		self.assertEqual(self.call_as_a(leave_application.leave_application_list, employee_id=self.id_b), 403)
		self.assertEqual(self.call_as_a(notification.get_notification_list, employee_id=self.id_b), 403)
		self.assertEqual(
			self.call_as_a(face_recognition.checkin_list, self.id_b, frappe.utils.today(), frappe.utils.today()), 403
		)

	def test_read_endpoints_allow_own_employee(self):
		self.assertNotEqual(self.call_as_a(leave_application.get_leave_balance, employee_id=self.id_a), 403)
		self.assertNotEqual(self.call_as_a(notification.get_notification_list, employee_id=self.id_a), 403)

	def test_checkin_for_another_employee_is_refused_and_not_recorded(self):
		code = self.call_as_a(
			face_recognition.verify_checkin_checkout,
			employee_id=self.id_b, log_type="IN", latitude="29.37", longitude="47.97",
		)
		self.assertEqual(code, 403)
		self.assertFalse(frappe.db.exists("Employee Checkin", {"employee": self.employee_b}))

	def test_shift_request_for_another_employee_is_refused_and_not_created(self):
		today = frappe.utils.today()
		code = self.call_as_a(shift_request.create_shift_request, self.id_b, "Assign Unassigned Shift", today, today)
		self.assertEqual(code, 403)
		self.assertFalse(frappe.db.exists("Shift Request", {"employee": self.employee_b}))

	def test_profile_image_for_another_employee_writes_no_file(self):
		image = base64.b64encode(b"not really a png").decode()
		code = self.call_as_a(user.change_user_profile_image, employee_id=self.id_b, image=image)
		self.assertEqual(code, 403)
		folder = Path(frappe.utils.cstr(frappe.local.site)) / "public" / "files" / "profile_image" / self.id_b
		self.assertFalse(folder.exists())

	def test_resignation_endpoints_refuse_another_employee(self):
		with self.set_user(self.user_a):
			with self.assertRaises(frappe.PermissionError):
				resignation.get_my_active_resignation(employee_id=self.id_b)
			with self.assertRaises(frappe.PermissionError):
				resignation.get_all_my_resignations(employee_id=self.id_b)
			with self.assertRaises(frappe.PermissionError):
				resignation.get_employee_supervisor(employee_id=self.id_b)

	def test_update_employee_needs_a_supervisor_role(self):
		# frappe.only_for skips its role check while in_test is set
		with self.set_user(self.user_a), patch.dict(frappe.local.flags, {"in_test": False}):
			with self.assertRaises(frappe.PermissionError):
				utils.update_employee(self.id_b, "cell_number", "96500000000")
		self.assertNotEqual(frappe.db.get_value("Employee", self.employee_b, "cell_number"), "96500000000")

	def test_update_employee_changes_only_allowed_fields(self):
		supervisor = _make_user("test-own-employee-supervisor@example.com", "Own Supervisor")
		frappe.get_doc("User", supervisor).add_roles("Shift Supervisor")
		with self.set_user(supervisor), self.assertRaises(frappe.PermissionError):
			utils.update_employee(self.id_b, "status", "Left")
		self.assertEqual(frappe.db.get_value("Employee", self.employee_b, "status"), "Active")
		with self.set_user(supervisor):
			utils.update_employee(self.id_b, "enrolled", "0")
		self.assertEqual(frappe.db.get_value("Employee", self.employee_b, "enrolled"), 0)

	def test_unused_endpoints_are_not_callable_over_http(self):
		for path in UNEXPOSED_ENDPOINTS:
			with self.subTest(path=path):
				method = frappe.get_attr(path)
				self.assertNotIn(method, frappe.whitelisted)
				self.assertNotIn(method, frappe.guest_methods)
