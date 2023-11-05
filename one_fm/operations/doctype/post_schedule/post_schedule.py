# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr

class PostSchedule(Document):
	def before_insert(self):
		if frappe.db.exists("Post Schedule", {"date": self.date, "post": self.post}):
			frappe.throw(_("Post Schedule already exists for {post} on {date}.".format(post=self.post, date=cstr(self.date))))
