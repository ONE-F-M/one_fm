# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest


def create_test_post():
	doc = frappe.new_doc("Operations Post")
	doc.post_name = "Test"
	doc.shift = frappe.get_doc("Operations Shift", "Admin-Farwaniya Camp-Morning-1").name
	doc.post_template = frappe.get_doc({"doctype": "Operations Role", "shift": doc.shift, })
	doc.post_template.save()
	doc.save()
	print("LETS STSTTETETETET")

	return doc
 
class TestOperationsPost(unittest.TestCase):
	
	def get_doc(self):
		return create_test_post()


	def test_delete_obj(self):
		frappe.delete_doc("Operations Post", self.get_doc().name)
