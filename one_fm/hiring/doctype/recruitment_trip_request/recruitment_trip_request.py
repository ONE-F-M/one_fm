# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

class RecruitmentTripRequest(Document):
	def validate(self):
		#self.calculate_total_expense()
		self.validate_dates()
	def validate_dates(self):
		if self.from_date and self.to_date:
			if self.from_date > self.to_date:
				frappe.throw(_("To Date cannot be before From Date"))
# 	def on_submit(self):
# 		journal_entry = frappe.new_doc('Journal Entry')
# 		journal_entry.voucher_type = 'Journal Entry'
# 		journal_entry.posting_date = nowdate()
# 		journal_entry.append("accounts", {
# 			"account": 'Employee Advances - ONEFM',
# 			"party_type": 'Employee',
# 			"party": self.employee,
# 			"debit_in_account_currency": 100.00
#     	})
# 		journal_entry.append("accounts", {
# 			"account": 'Cash A/c - ONEFM',
# 			"cost_center": 'GP Tickets - ONEFM',
# 			"credit_in_account_currency": 100.00
#     	})
# 		journal_entry.save()
# 		frappe.db.commit()
# 	def on_submit(self):
# 		journal_entry = frappe.new_doc('Journal Entry')
# 		journal_entry.voucher_type = 'Journal Entry'
# 		journal_entry.accounts = ''
# 		journal_entry.posting_date = nowdate()
# 		total_debit = 0
# 		for item in self.travel_items:
# 			if journal_entry.accounts:
# 				for i in journal_entry.accounts:
# 					if i.account == item.expense_account:
# 						i.debit_in_account_currency +=  item.amount
# 					else:
# 						journal_entry.append("accounts", {
# 							"account": item.expense_account,
# 							"debit_in_account_currency": item.amount
# 						})
# 			else:
# 				journal_entry.append("accounts", {
# 					"account": item.expense_account,
# 					"debit_in_account_currency": item.amount
# 				})
# 			total_debit += item.amount
# 		for item1 in self.other_items:
# 			journal_entry.append("accounts", {
# 				"account": item1.expense_account,
# 				"debit_in_account_currency": item1.amount
# 			})
# 			total_debit += item1.amount
# 		journal_entry.append("accounts", {
# 			"account": 'Employee Advances - ONEFM',
# 			"cost_center": 'GP Tickets - ONEFM',
# 			"credit_in_account_currency": total_debit
# 		})
# 		journal_entry.save()
# 		frappe.db.commit()
# 	def calculate_total_expense(self):
# 		self.total_travel_expense = self.total_other_expense = self.total_expense = 0
# 		for item in self.travel_items:
# 			self.total_travel_expense += item.amount
# 		for item in self.other_items:
# 			self.total_other_expense += item.amount
# 		self.total_expense = self.total_travel_expense + self.total_other_expense
	
# @frappe.whitelist()
# def make_journal_for_advance(employee):
# 	journal_entry = frappe.new_doc('Journal Entry')
# 	journal_entry.voucher_type = 'Journal Entry'
# 	journal_entry.posting_date = nowdate()
# 	journal_entry.append("accounts", {
# 		"account": 'Employee Advances - ONEFM',
# 		"party_type": 'Employee',
# 		"party": employee,
# 		"debit_in_account_currency": 100.00
# 	})
# 	journal_entry.append("accounts", {
# 		"account": 'Cash A/c - ONEFM',
# 		"cost_center": 'GP Tickets - ONEFM',
# 		"credit_in_account_currency": 100.00
# 	})
# 	journal_entry.save()
# 	frappe.db.commit()
	

