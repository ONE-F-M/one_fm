import os

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.website.path_resolver import resolve_redirect

NEW_POLICY_URL = "https://app.one-fm.com/privacy_policy/"


class TestPrivacyPolicyPage(FrappeTestCase):
	def test_old_url_redirects_to_the_landing_site_policy(self):
		frappe.cache.delete_value("website_redirects")
		with self.assertRaises(frappe.Redirect) as redirect:
			resolve_redirect("privacy_policy")
		self.assertEqual(redirect.exception.http_status_code, 301)
		self.assertEqual(frappe.flags.redirect_location, NEW_POLICY_URL)

	def test_one_fm_no_longer_serves_its_own_policy_page(self):
		self.assertFalse(
			os.path.exists(frappe.get_app_path("one_fm", "templates", "pages", "privacy_policy.html"))
		)
