import frappe
from frappe.tests.utils import FrappeTestCase

UNEXPOSED_GUEST_ROUTES = (
	"one_fm.api.v1.authentication.update_password",
	"one_fm.api.v1.authentication.validate_employee_id",
	"one_fm.api.v1.authentication.new_forgot_password",
	"one_fm.api.v1.authentication.get_otp",
	"one_fm.api.v1.authentication.set_password",
	"one_fm.api.v2.authentication.update_password",
	"one_fm.api.v2.authentication.validate_employee_id",
	"one_fm.api.v2.authentication.new_forgot_password",
	"one_fm.api.v2.authentication.get_otp",
	"one_fm.api.v2.authentication.set_password",
	"one_fm.api.v2.authentication.user_login",
	"one_fm.api.v1.flutter.roster.get_staff",
	"one_fm.api.v2.flutter.roster.get_staff",
)

APP_GUEST_ROUTES = (
	"one_fm.api.v1.authentication.user_login",
	"one_fm.api.v1.authentication.refresh_token",
	"one_fm.api.v1.authentication.forgot_password",
	"one_fm.api.v1.authentication.verify_otp",
	"one_fm.api.v1.authentication.change_password",
	"one_fm.api.v1.authentication.enrollment_status",
)


class TestGuestRoutesUnexposed(FrappeTestCase):
	def test_takeover_and_staff_list_routes_are_not_callable(self):
		for path in UNEXPOSED_GUEST_ROUTES:
			with self.subTest(path=path):
				method = frappe.get_attr(path)
				self.assertNotIn(method, frappe.whitelisted)
				self.assertNotIn(method, frappe.guest_methods)

	def test_app_login_and_reset_routes_stay_open_to_guests(self):
		for path in APP_GUEST_ROUTES:
			with self.subTest(path=path):
				self.assertIn(frappe.get_attr(path), frappe.guest_methods)
