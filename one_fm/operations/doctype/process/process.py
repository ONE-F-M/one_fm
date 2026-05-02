# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

from frappe.utils.nestedset import NestedSet


class Process(NestedSet):
	nsm_parent_field = "parent_process"

	def before_save(self):
		self.predecessor_count = len(self.depends_on or [])
		self.successor_count = len(self.is_required_for or [])
