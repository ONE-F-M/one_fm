# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Placeholder v2 while diagnosing sandbox test-bootstrap failure (WI-000446)."""

from frappe.tests.utils import FrappeTestCase


class TestPlaceholderV2(FrappeTestCase):
	def test_noop_v2(self):
		self.assertEqual(1, 1)
