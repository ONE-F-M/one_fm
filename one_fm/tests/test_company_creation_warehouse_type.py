# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Placeholder while diagnosing sandbox test-bootstrap failure (WI-000446)."""

from frappe.tests.utils import FrappeTestCase


class TestPlaceholder(FrappeTestCase):
	def test_noop(self):
		self.assertTrue(True)
