"""Handlers for the ToDo DocType during setup/installation."""

import frappe


def set_todo_allocated_to_default(doc, method):
	"""Set allocated_to to Administrator if not provided.
	
	This handler ensures that test ToDo records can be created without
	explicitly providing the mandatory 'allocated_to' field. It applies
	a default value during validation, before the mandatory field check.
	"""
	if not doc.allocated_to:
		doc.allocated_to = "Administrator"
