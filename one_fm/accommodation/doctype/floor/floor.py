# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document

class Floor(Document):
	def before_insert(self):
		self.set_floor_name()

	def set_floor_name(self):
		self.floor_name = str(self.floor)+number_name(self.floor)

def number_name(num):
	value = str(num)
	if len(value) > 1:
		secondToLastDigit = value[-2]
		if secondToLastDigit == '1':
			return 'th'
	lastDigit = value[-1]
	if (lastDigit == '1'):
		return 'st'
	elif (lastDigit == '2'):
		return 'nd'
	elif (lastDigit == '3'):
		return 'rd'
	else:
		return 'th'
