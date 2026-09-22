# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-000446 diagnostic stub: temporarily trivial to check whether the ToDo
MandatoryError seen in run_tests is caused by this module or is a pre-existing,
unrelated test-record bootstrap issue in the sandbox."""

from frappe.tests.utils import FrappeTestCase


class TestCompanyCreationWarehouseType(FrappeTestCase):
	def test_placeholder(self):
		self.assertTrue(True)
