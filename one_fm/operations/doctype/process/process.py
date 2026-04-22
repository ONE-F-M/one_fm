# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

# import frappe
from frappe.utils.nestedset import NestedSet


class Process(NestedSet):
	nsm_parent_field = "parent_process"
