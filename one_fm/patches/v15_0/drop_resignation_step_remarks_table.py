import frappe


def execute():
	"""Resignation Step Remarks (a per-stage remarks child table) was replaced by
	three flat fields directly on Employee Resignation. `bench migrate` already
	auto-removes the orphaned DocType record once its source files are gone, but
	leaves the underlying SQL table behind -- drop it here.
	"""
	frappe.db.sql_ddl("drop table if exists `tabResignation Step Remarks`")
