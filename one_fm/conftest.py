# -*- coding: utf-8 -*-
"""Pytest configuration for one_fm tests.

This module handles test setup including overriding Frappe's default test record
creation for doctypes that have mandatory fields not provided by make_test_records().
"""

import frappe
import pytest
from frappe.test_runner import make_test_records as frappe_make_test_records


# Patch make_test_records to handle doctypes with custom mandatory requirements
_original_make_test_records = frappe_make_test_records


def make_test_records(doctype, values=None, commit=True):
	"""Wrapper around frappe.test_runner.make_test_records that handles
	doctypes with mandatory fields not provided by default test record creation.
	
	For ToDo, allocated_to is mandatory (set in one_fm.custom.property_setter.todo),
	so we ensure it's provided in test records.
	"""
	if doctype == "ToDo":
		# Ensure allocated_to is provided for ToDo test records
		if not values:
			values = []
		elif not isinstance(values, list):
			values = [values]
		
		# Add allocated_to to each record if not already present
		for i, record in enumerate(values):
			if isinstance(record, dict) and "allocated_to" not in record:
				record["allocated_to"] = "test@example.com"
			values[i] = record
		
		# If no values provided, create one with allocated_to
		if not values:
			values = [{"allocated_to": "test@example.com"}]
	
	return _original_make_test_records(doctype, values, commit)


# Monkey-patch make_test_records at import time
import frappe.test_runner
frappe.test_runner.make_test_records = make_test_records
