# -*- coding: utf-8 -*-
# Copyright (c) 2019, omar jaber and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest



def create_doc():
	pam_file = frappe.new_doc("PAM File")
	pam_file.pam_file_name = "Testing PAM File"
	pam_file.pam_file_number = 902100
	pam_file.government_project = True
	pam_file.insert()

	print(pam_file)


class TestPAMFile(unittest.TestCase):
	
	#def setUp(self):
		#create_doc()

	def get_doc(self):
		doc = frappe.get_doc({
			"doctype": "PAM File",
			"pam_file_name": "Testing PAM File",

		})

		return doc

	def test_if_doc_exists(self):
		self.assertTrue(self.get_doc())


	
	def test_if_license_and_file_number_can_be_set_when_governent_project_is_False(self):
		doc = self.get_doc()
		doc.government_project = False
		doc.pam_file_number = 902100
		doc.file_number = 12345
		doc.license_number = 47
		doc.save()

		self.assertEqual(doc.license_number, 47)
		self.assertEqual(doc.file_number, 12345)


	
	def test_delete_test_obj(self):
		frappe.delete_doc("PAM File", "Testing PAM File")
		self.assertTrue(self.get_doc(), None)

