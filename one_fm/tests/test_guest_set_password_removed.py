import frappe
from frappe.tests.utils import FrappeTestCase

GUEST_SET_PASSWORD_PATHS = (
	"one_fm.api.v1.authentication.set_password",
	"one_fm.api.v2.authentication.set_password",
)


class TestGuestSetPasswordRemoved(FrappeTestCase):
	def test_set_password_cannot_be_called(self):
		for path in GUEST_SET_PASSWORD_PATHS:
			with self.subTest(path=path), self.assertRaises(AttributeError):
				frappe.get_attr(path)

	def test_otp_reset_endpoints_stay_available_to_guests(self):
		for path in (
			"one_fm.api.v1.authentication.forgot_password",
			"one_fm.api.v1.authentication.change_password",
		):
			with self.subTest(path=path):
				self.assertIn(frappe.get_attr(path), frappe.guest_methods)
