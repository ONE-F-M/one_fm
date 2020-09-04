# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import nowdate, flt
from erpnext.accounts.party import get_party_account
from frappe.model.document import Document

class ResidencyPaymentRequest(Document):
	def on_submit(self):
		pass
		# self.update_payment_status()

	def on_cancel(self):
		pass
		# self.update_payment_status(cancel=True)

	def update_payment_status(self, cancel=False):
		pass
		# status = 'Payment Ordered'
		# if cancel:
		# 	status = 'Initiated'
		#
		# ref_field = "status" if self.payment_order_type == "Payment Request" else "payment_order_status"
		#
		# for d in self.references:
		# 	frappe.db.set_value(self.payment_order_type, d.get(frappe.scrub(self.payment_order_type)), ref_field, status)

	def validate(self):
		if self.references:
			total_amount = 0
			for reference in self.references:
				total_amount += reference.amount if reference.amount else 0
			self.total_amount = total_amount

	def set_todays_residency_payment_details(self):
		get_residency_entries(self)

def create_residency_payment_request():
	doc = frappe.new_doc('Residency Payment Request')
	doc.posting_date = nowdate()
	get_residency_entries(doc)
	doc.save(ignore_permissions=True)

def get_residency_entries(doc):
	residency_doctypes = [{'dt': 'Work Permit', 'amount_field': 'amount_to_pay'}]
	res = []
	for residency_doctype in residency_doctypes:
		residency_entries = frappe.db.sql("""
			select
				"{1}" as reference_type, t1.employee, t1.name as reference_name,
				t1.{0} as amount
			from
				`tab{1}` t1
			where
				t1.docstatus = 1
			""".format(residency_doctype['amount_field'], residency_doctype['dt']), as_dict=1)
		res += list(residency_entries)

	doc.set("references", [])
	doc.total_amount = 0
	for d in res:
		doc.total_amount += flt(d.amount)
		doc.append("references", {
			"employee": d.employee,
			"reference_type": d.reference_type,
			"reference_name": d.reference_name,
			"amount": flt(d.amount)
		})

def get_mop_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(""" select mode_of_payment from `tabResidency Payment Request Reference`
		where parent = %(parent)s and mode_of_payment like %(txt)s
		limit %(start)s, %(page_len)s""", {
			'parent': filters.get("parent"),
			'start': start,
			'page_len': page_len,
			'txt': "%%%s%%" % txt
		})

def get_supplier_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(""" select supplier from `tabResidency Payment Request Reference`
		where parent = %(parent)s and supplier like %(txt)s and
		(payment_reference is null or payment_reference='')
		limit %(start)s, %(page_len)s""", {
			'parent': filters.get("parent"),
			'start': start,
			'page_len': page_len,
			'txt': "%%%s%%" % txt
		})

@frappe.whitelist()
def make_payment(name, method):
	doc = frappe.get_doc('Residency Payment Request', name)
	# pi = create_purchase_invoice(doc)
	if method == "PE":
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
		return get_payment_entry(dt='Purchase Invoice', dn='ACC-PINV-2020-00013')
	elif method == "JE":
		from erpnext.accounts.doctype.journal_entry.journal_entry import get_payment_entry_against_invoice
		return get_payment_entry_against_invoice(dt='Purchase Invoice', dn='ACC-PINV-2020-00013')
	# make_journal_entry(doc, supplier, mode_of_payment)

@frappe.whitelist()
def make_payment_records(name, supplier, mode_of_payment=None):
	doc = frappe.get_doc('Residency Payment Request', name)
	# pi = create_purchase_invoice(doc)

	# make_journal_entry(doc, supplier, mode_of_payment)

def make_journal_entry(doc, supplier, mode_of_payment=None):
	je = frappe.new_doc('Journal Entry')
	je.one_fm_recidency_payment_request = doc.name
	je.posting_date = nowdate()
	mode_of_payment_type = frappe._dict(frappe.get_all('Mode of Payment',
		fields = ["name", "type"], as_list=1))

	je.voucher_type = 'Bank Entry'
	if mode_of_payment and mode_of_payment_type.get(mode_of_payment) == 'Cash':
		je.voucher_type = "Cash Entry"

	paid_amt = 0
	party_account = get_party_account('Supplier', supplier, doc.company)
	for d in doc.references:
		# if (d.supplier == supplier
		# 	and (not mode_of_payment or mode_of_payment == d.mode_of_payment)):
		je.append('accounts', {
			'account': party_account,
			'debit_in_account_currency': d.amount,
			'party_type': 'Supplier',
			'party': supplier,
			'reference_type': d.reference_type,
			'reference_name': d.reference_name
		})

		paid_amt += d.amount

	je.append('accounts', {
		'account': doc.references[0].account,
		'credit_in_account_currency': paid_amt
	})

	je.flags.ignore_mandatory = True
	je.save()
	frappe.msgprint(_("{0} {1} created").format(je.doctype, je.name))
