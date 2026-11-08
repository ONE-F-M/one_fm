# -*- coding: utf-8 -*-
# Copyright (c) 2019, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class PAMFile(Document):
	#def on_update(self):
		#if self.government_project == 1:
			#self.db_set('pam_file_number',self.contract_pam_file_number)

	def validate(self):
		if self.government_project:
			if self.file_number:
				frappe.throw("File Number cannot be set with Government project")

			if self.license_number:
				frappe.throw("Company License cannot be set with Governement Project")

		self.set_license_counts()

	def set_license_counts(self):
		"""Derive the active and inactive licence counts from the licence rows.

		A row counts once it names a licence; a row with no licence is an unfilled row, not a
		licence. Inactive is the only status that makes a licence inactive - Active,
		Suspended and a blank status all count as active.

		The fields are Data, so the figures are written as text, the way PAM License Details
		writes total_number_of_employees.
		"""
		active = 0
		inactive = 0
		for row in self.get("pam_licenses") or []:
			if not row.civil_id_number_for_licensing:
				continue

			if row.status == "Inactive":
				inactive += 1
			else:
				active += 1

		self.number_of_active_licenses = str(active)
		self.number_of_inactive_licenses = str(inactive)
		# A file is Active while it holds at least one active licence.
		self.file_status = "Active" if active else "Inactive"
