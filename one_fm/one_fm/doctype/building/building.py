# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Building(Document):
	def validate(self):
		self.validate_project_matches_site()

	def validate_project_matches_site(self):
		"""Enforce that the Project field always matches the Operations Site's project.

		The project field is read-only on the client, but API calls can bypass that.
		This auto-corrects the value to maintain data integrity.
		"""
		if not self.operations_site:
			return

		site_project = frappe.db.get_value(
			"Operations Site", self.operations_site, "project"
		)

		if self.project != site_project:
			self.project = site_project
			frappe.msgprint(
				_("Project has been auto-corrected to '{0}' based on the selected Operations Site.").format(
					site_project
				),
				alert=True,
			)
