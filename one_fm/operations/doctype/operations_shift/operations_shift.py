# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr

class OperationsShift(Document):
	def autoname(self):
		print(type(self.start_time), self.end_time)
		self.name = self.site+"-"+self.shift_classification+"|"+cstr(self.start_time)+"-"+cstr(self.end_time)+"|"+cstr(self.duration)+" hours"


@frappe.whitelist()
def create_posts(data, site_shift, site, project):
	try:
		data = frappe._dict(json.loads(data))
		post_names = data.post_names
		print(type(post_names))
		skills = data.skills
		designations = data.designations
		gender = data.gender
		sale_item = data.sale_item
		post_template = data.post_template
		post_description = data.post_description
		post_location = data.post_location
		print(len(designations), len(skills), len(post_names))
		for post_name in post_names:
			operations_post = frappe.new_doc("Operations Post")
			operations_post.post_name = post_name["post_name"]
			operations_post.gender = gender
			operations_post.post_location = post_location
			operations_post.post_description = post_description
			operations_post.post_template = post_template
			operations_post.sale_item = sale_item
			operations_post.site_shift = site_shift
			operations_post.site = site
			operations_post.project = project
			for designation in designations:
				operations_post.append("designations",{
					"designation": designation["designation"],
					"primary": designation["primary"]
				})
			for skill in skills:
				operations_post.append("skills",{
					"skill": skill["skill"],
					"minimum_proficiency_required": skill["minimum_proficiency_required"]
				})
				
			operations_post.save()

		frappe.db.commit()
		frappe.msgprint(_("Posts created successfully."))
	except Exception as e:
		frappe.throw(_(frappe.get_traceback()))
	