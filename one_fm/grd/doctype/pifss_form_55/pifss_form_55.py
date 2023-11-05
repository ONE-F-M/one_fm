# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt
import pandas as pd

class PIFSSForm55(Document):
	def after_insert(self):
		self.update_file_link()

	def update_file_link(self):
		file_doc = frappe.get_value("File", {"file_url": self.attach_report})
		frappe.set_value("File", file_doc, "attached_to_name", self.name)


@frappe.whitelist()
def import_deduction_data(file_url):
	url = frappe.get_site_path() + file_url
	print(url)
	
	df = pd.read_csv(url, encoding='utf-8') #.drop([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
	row_count = len(df.index)
	print(row_count)
	data = []
	for index, row in df.iterrows():
		print(row[0], row[1], row[7], row[8], row[10])
		print("----------------------------------------")
		data.append({'civil_id': row[0], 'full_name_arabic': row[1], 'social_allowance': row[7], 'qualification_bonus': row[8], 'financial_reward': row[10]})

	return data