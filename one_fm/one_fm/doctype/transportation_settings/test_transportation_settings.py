import frappe
from frappe.tests.utils import FrappeTestCase

DOCTYPE = "Transportation Settings"
FIELD = "restrict_reliever_search_to_rambo_employees_only"
SUPERVISOR_EMAIL = "ts_supervisor_test@example.com"


class TestTransportationSettings(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_the_field_is_a_check_with_the_agreed_label_defaulting_to_unchecked(self):
		meta = frappe.get_meta(DOCTYPE)
		self.assertTrue(meta.issingle)
		field = meta.get_field(FIELD)
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Check")
		self.assertEqual(field.label, "Restrict Reliever Search to Rambo Employees Only")
		self.assertEqual(str(field.default), "0")
		self.assertEqual(len(meta.get("fields", {"fieldtype": "Check"})), 1)

	def test_only_system_manager_and_transportation_manager_can_write(self):
		meta = frappe.get_meta(DOCTYPE)
		writers = {p.role for p in meta.permissions if p.write}
		self.assertEqual(writers, {"System Manager", "Transportation Manager"})
		self.assertEqual({p.role for p in meta.permissions}, writers)
		for p in meta.permissions:
			self.assertTrue(p.read)
			self.assertTrue(p.create)
			self.assertEqual(p.permlevel, 0)

	def test_a_transportation_supervisor_cannot_save_the_settings(self):
		if not frappe.db.exists("Role", "Transportation Supervisor"):
			frappe.get_doc({"doctype": "Role", "role_name": "Transportation Supervisor"}).insert(
				ignore_permissions=True
			)
		if not frappe.db.exists("User", SUPERVISOR_EMAIL):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": SUPERVISOR_EMAIL,
					"first_name": "TS Supervisor",
					"send_welcome_email": 0,
					"roles": [{"role": "Transportation Supervisor"}],
				}
			).insert(ignore_permissions=True)

		settings = frappe.get_doc(DOCTYPE)
		settings.set(FIELD, 1)
		frappe.set_user(SUPERVISOR_EMAIL)
		with self.assertRaises(frappe.PermissionError):
			settings.save()
