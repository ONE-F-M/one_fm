import frappe
from frappe.tests.utils import FrappeTestCase


class TestExposeDiscoverySource(FrappeTestCase):
	def test_app_lets_mcp_discovery_show_method_source(self):
		self.assertTrue(any(frappe.get_hooks("expose_discovery_source", app_name="one_fm")))
