# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""v1.configuration.app_version returns the mobile app version policy, open to guests."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.api.v1 import configuration

FIELDS = (
	"android_minimum_version",
	"android_latest_version",
	"play_store_url",
	"ios_minimum_version",
	"ios_latest_version",
	"app_store_url",
)


class TestAppVersion(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(self._clear_cache)

	def _clear_cache(self):
		frappe.clear_document_cache("Mobile App Settings", "Mobile App Settings")

	def _set(self, **values):
		settings = frappe.get_doc("Mobile App Settings")
		for field in FIELDS:
			settings.set(field, values.get(field))
		settings.save(ignore_permissions=True)
		self._clear_cache()

	def _call(self):
		frappe.local.response = frappe._dict()
		configuration.app_version()
		return frappe.local.response

	def test_response_shape_and_mapping(self):
		self._set(
			android_minimum_version="1.2.0",
			android_latest_version="1.4.0",
			play_store_url="https://play.google.com/store/apps/details?id=x",
			ios_minimum_version="1.1.0",
			ios_latest_version="1.3.0",
			app_store_url="https://apps.apple.com/app/id1",
		)
		res = self._call()
		self.assertEqual(res.get("http_status_code"), 200)
		self.assertEqual(
			res.get("data"),
			{
				"android": {
					"minimum_app_version": "1.2.0",
					"latest_app_version": "1.4.0",
					"store_url": "https://play.google.com/store/apps/details?id=x",
				},
				"ios": {
					"minimum_app_version": "1.1.0",
					"latest_app_version": "1.3.0",
					"store_url": "https://apps.apple.com/app/id1",
				},
			},
		)

	def test_empty_settings_return_empty_values(self):
		self._set()
		res = self._call()
		self.assertEqual(res.get("http_status_code"), 200)
		self.assertNotIn("error", res)
		for platform in ("android", "ios"):
			self.assertEqual(
				res.get("data")[platform],
				{"minimum_app_version": "", "latest_app_version": "", "store_url": ""},
			)

	def test_guest_can_call_it(self):
		self._set(android_minimum_version="2.0.0")
		self.assertIn(configuration.app_version, frappe.guest_methods)
		self.assertIn("GET", frappe.allowed_http_methods_for_whitelisted_func[configuration.app_version])
		frappe.set_user("Guest")
		res = self._call()
		self.assertEqual(res.get("http_status_code"), 200)
		self.assertEqual(res.get("data")["android"]["minimum_app_version"], "2.0.0")

	def test_call_changes_no_data(self):
		self._set(ios_latest_version="3.0.0")
		before = frappe.db.get_single_value("Mobile App Settings", "ios_latest_version", cache=False)
		self._call()
		after = frappe.db.get_single_value("Mobile App Settings", "ios_latest_version", cache=False)
		self.assertEqual(before, "3.0.0")
		self.assertEqual(before, after)
