"""Test that ToDo records can be created without mandatory field errors during install."""

import frappe
import unittest


class TestToDoDuringInstall(unittest.TestCase):
	"""Test that ToDo test records can be created without allocation errors."""

	def setUp(self):
		"""Clear any test records before running tests."""
		# Ensure we have a clean state for each test
		self.test_name = None
		# Clear the DocType cache to ensure property setters are applied
		frappe.clear_cache(doctype="ToDo")

	def test_todo_can_be_created_without_allocated_to(self):
		"""Test that frappe can create a test ToDo record without a pre-supplied allocated_to value.
		
		This simulates what frappe's test_runner.make_test_objects does when it tries to auto-create
		test data for test runs. The frappe.get_doc() will not populate mandatory fields, so the
		"allocated_to" field must have a default value set via property setter.
		"""
		# This simulates what frappe's test runner does
		doc = frappe.get_doc({
			"doctype": "ToDo",
			"description": "Test ToDo for install validation",
			# Note: Not providing allocated_to - it should come from the default
		})
		
		# This should not raise MandatoryError: [ToDo, ...]: allocated_to
		doc.insert(ignore_permissions=True)
		
		# Verify the record was created with a value for allocated_to
		self.assertIsNotNone(doc.allocated_to, "allocated_to should have a default value")
		self.test_name = doc.name
	
	def tearDown(self):
		"""Clean up test records after the test."""
		if self.test_name:
			try:
				frappe.delete_doc("ToDo", self.test_name, force=True)
			except Exception:
				pass
