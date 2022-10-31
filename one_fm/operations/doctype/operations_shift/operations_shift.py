# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.model.document import Document
from frappe import _
from frappe.model.rename_doc import rename_doc
from frappe.utils import cstr, get_datetime
import schedule, time

from datetime import timedelta

class OperationsShift(Document):
	
	def autoname(self):
		#this method is updating the name of the record and sending clear message through exception if any of the records are missing
		try:
			self.name = self.service_type+"-"+self.site+"-"+self.shift_classification+"-"+cstr(self.shift_number)
		except Exception as e:
			if not self.service_type and self.site and self.shift_classification:
				frappe.throw("Kindly, make sure all required fields are not missing")

	def on_update(self):
		self.validate_name()

	def validate_name(self):
		#this method is updating the name of the record and sending clear message through exception if any of the records are missing
		try:
			new_name = self.service_type+"-"+self.site+"-"+self.shift_classification+"-"+cstr(self.shift_number)
			if new_name != self.name:
				rename_doc(self.doctype, self.name, new_name, force=True)
		except Exception as e:
			if not self.service_type and self.site and self.shift_classification:
				frappe.throw("Kindly, make sure all required fields are not missing")

@frappe.whitelist()
def create_posts(data, site_shift, site, project=None):
	try:
		data = frappe._dict(json.loads(data))
		post_names = data.post_names
		skills = data.skills
		designations = data.designations
		gender = data.gender
		sale_item = data.sale_item
		post_template = data.post_template
		post_description = data.post_description
		post_location = data.post_location

		for post_name in post_names:
			operations_role = frappe.new_doc("Operations Role")
			operations_role.post_name = post_name["post_name"]
			operations_role.gender = gender
			operations_role.post_location = post_location
			operations_role.post_description = post_description
			operations_role.post_template = post_template
			operations_role.sale_item = sale_item
			operations_role.site_shift = site_shift
			operations_role.site = site
			operations_role.project = project
			for designation in designations:
				operations_role.append("designations",{
					"designation": designation["designation"],
					"primary": designation["primary"] if "primary" in designation else 0
				})
			for skill in skills:
				operations_role.append("skills",{
					"skill": skill["skill"],
					"minimum_proficiency_required": skill["minimum_proficiency_required"]
				})
				
			operations_role.save()

		frappe.db.commit()
		frappe.msgprint(_("Posts created successfully."))
	except Exception as e:
		frappe.throw(_(frappe.get_traceback()))
	