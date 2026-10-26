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
from one_fm.api.v2 import user as user_v2
from one_fm.one_fm.doctype.employee_resignation.test_employee_resignation_api import (
	_make_employee,
	_make_user,
)


def status_code():
	return frappe.local.response.get("http_status_code")


def enforced():
	return patch.dict(frappe.local.conf, {"enforce_own_employee_api": 1})


def mismatch_logs():
	return frappe.db.count("Error Log", {"method": ["like", "Own employee check:%"]})


class TestOwnEmployeeApi(FrappeTestCase):
	def setUp(self):
		frappe.local.response = frappe._dict()
		frappe.cache.delete_keys("own_employee_check:")
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

	def test_watch_mode_allows_another_employee_and_logs_it_once(self):
		before = mismatch_logs()
		self.assertNotEqual(self.call_as_a(leave_application.get_leave_balance, employee_id=self.id_b), 403)
		self.assertNotEqual(self.call_as_a(leave_application.get_leave_balance, employee_id=self.id_b), 403)
		self.assertEqual(mismatch_logs(), before + 1)

	def test_own_employee_is_not_logged(self):
		before = mismatch_logs()
		self.call_as_a(notification.get_notification_list, employee_id=self.id_a)
		self.assertEqual(mismatch_logs(), before)

	def test_enforced_read_endpoints_refuse_another_employee(self):
		with enforced():
			self.assertEqual(self.call_as_a(leave_application.get_leave_balance, employee_id=self.id_b), 403)
			self.assertEqual(self.call_as_a(leave_application.get_leave_types, employee_id=self.id_b), 403)
			self.assertEqual(self.call_as_a(leave_application.leave_application_list, employee_id=self.id_b), 403)
			self.assertEqual(self.call_as_a(notification.get_notification_list, employee_id=self.id_b), 403)
			self.assertEqual(
				self.call_as_a(face_recognition.checkin_list, self.id_b, frappe.utils.today(), frappe.utils.today()),
				403,
			)

	def test_enforced_read_endpoints_allow_own_employee(self):
		with enforced():
			self.assertNotEqual(self.call_as_a(leave_application.get_leave_balance, employee_id=self.id_a), 403)
			self.assertNotEqual(self.call_as_a(notification.get_notification_list, employee_id=self.id_a), 403)

	def test_enforced_checkin_for_another_employee_is_refused_and_not_recorded(self):
		with enforced():
			code = self.call_as_a(
				face_recognition.verify_checkin_checkout,
				employee_id=self.id_b, log_type="IN", latitude="29.37", longitude="47.97",
			)
		self.assertEqual(code, 403)
		self.assertFalse(frappe.db.exists("Employee Checkin", {"employee": self.employee_b}))

	def test_enforced_shift_request_for_another_employee_is_refused_and_not_created(self):
		today = frappe.utils.today()
		with enforced():
			code = self.call_as_a(shift_request.create_shift_request, self.id_b, "Assign Unassigned Shift", today, today)
		self.assertEqual(code, 403)
		self.assertFalse(frappe.db.exists("Shift Request", {"employee": self.employee_b}))

	def test_enforced_profile_image_for_another_employee_writes_no_file(self):
		image = base64.b64encode(b"not really a png").decode()
		with enforced():
			code = self.call_as_a(user.change_user_profile_image, employee_id=self.id_b, image=image)
		self.assertEqual(code, 403)
		folder = Path(frappe.utils.cstr(frappe.local.site)) / "public" / "files" / "profile_image" / self.id_b
		self.assertFalse(folder.exists())

	def test_enforced_resignation_endpoints_refuse_another_employee(self):
		with self.set_user(self.user_a), enforced():
			with self.assertRaises(frappe.PermissionError):
				resignation.get_my_active_resignation(employee_id=self.id_b)
			with self.assertRaises(frappe.PermissionError):
				resignation.get_all_my_resignations(employee_id=self.id_b)
			with self.assertRaises(frappe.PermissionError):
				resignation.get_employee_supervisor(employee_id=self.id_b)

	def test_update_employee_without_a_supervisor_role(self):
		before = mismatch_logs()
		with self.set_user(self.user_a):
			utils.update_employee(self.id_b, "enrolled", "0")
		self.assertEqual(mismatch_logs(), before + 1)
		with self.set_user(self.user_a), enforced(), self.assertRaises(frappe.PermissionError):
			utils.update_employee(self.id_b, "cell_number", "96500000000")
		self.assertNotEqual(frappe.db.get_value("Employee", self.employee_b, "cell_number"), "96500000000")

	def test_enforced_update_employee_changes_only_allowed_fields(self):
		supervisor = _make_user("test-own-employee-supervisor@example.com", "Own Supervisor")
		frappe.get_doc("User", supervisor).add_roles("Shift Supervisor")
		with self.set_user(supervisor), enforced():
			with self.assertRaises(frappe.PermissionError):
				utils.update_employee(self.id_b, "status", "Left")
			utils.update_employee(self.id_b, "enrolled", "0")
		self.assertEqual(frappe.db.get_value("Employee", self.employee_b, "status"), "Active")
		self.assertEqual(frappe.db.get_value("Employee", self.employee_b, "enrolled"), 0)

	def test_user_details_of_another_employee(self):
		for method in (user.get_user_details, user_v2.get_user_details):
			with self.subTest(method=method.__module__):
				frappe.cache.delete_keys("own_employee_check:")
				before = mismatch_logs()
				self.assertEqual(self.call_as_a(method, employee_id=self.id_b), 200)
				self.assertEqual(mismatch_logs(), before + 1)
				with enforced():
					self.assertEqual(self.call_as_a(method, employee_id=self.id_b), 403)
					self.assertEqual(self.call_as_a(method, employee_id=self.id_a), 200)
