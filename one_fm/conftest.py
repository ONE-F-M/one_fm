# -*- coding: utf-8 -*-
"""Pytest configuration for one_fm tests.

This module handles test setup including patching Frappe's make_test_objects to provide
allocated_to for ToDo records, since one_fm sets allocated_to as mandatory.
"""

import frappe
import pytest
from frappe.test_runner import make_test_objects as frappe_make_test_objects


# Store the original make_test_objects function
_original_make_test_objects = frappe_make_test_objects


def make_test_objects(doctype, values_list=None, **kwargs):
	"""Wrapper around frappe.test_runner.make_test_objects that handles
	doctypes with mandatory fields not provided by default test object creation.
	
	For ToDo, allocated_to is mandatory (set in one_fm.custom.property_setter.todo),
	so we ensure it's provided in test objects.
	"""
	if doctype == "ToDo":
		# Ensure allocated_to is provided for ToDo test objects
		if not values_list:
			values_list = [{}]
		
		# Add allocated_to to each record if not already present
		for record in values_list:
			if isinstance(record, dict) and "allocated_to" not in record:
				record["allocated_to"] = "test@example.com"
	
	return _original_make_test_objects(doctype, values_list, **kwargs)


# Monkey-patch make_test_objects at import time
import frappe.test_runner
frappe.test_runner.make_test_objects = make_test_objects


# Ensure test user exists for allocated_to field tests
def pytest_configure(config):
	"""Pytest hook to run at test startup."""
	try:
		if not frappe.db.exists("User", "test@example.com"):
			frappe.get_doc({
				"doctype": "User",
				"email": "test@example.com",
				"first_name": "Test",
			}).insert(ignore_permissions=True)
			frappe.db.commit()
	except Exception:
		# Ignore if user already exists or other setup errors
		pass
