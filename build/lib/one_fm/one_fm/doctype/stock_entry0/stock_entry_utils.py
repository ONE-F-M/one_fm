# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.utils import cint, flt

from six import string_types

@frappe.whitelist()
def make_stock_entry(**args):
	'''Helper function to make a Stock Entry

	:item_code: Item to be moved
	:qty: Qty to be moved
	:company: Company Name (optional)
	:from_warehouse: Optional
	:to_warehouse: Optional
	:rate: Optional
	:serial_no: Optional
	:batch_no: Optional
	:posting_date: Optional
	:posting_time: Optional
	:purpose: Optional
	:do_not_save: Optional flag
	:do_not_submit: Optional flag
	'''

	def process_serial_numbers(serial_nos_list):
		serial_nos_list = [
			'\n'.join(serial_num['serial_no'] for serial_num in serial_nos_list if serial_num.serial_no)
		]

		uniques = list(set(serial_nos_list[0].split('\n')))

		return '\n'.join(uniques)

	s = frappe.new_doc("Stock Entry")
	args = frappe._dict(args)

	if args.posting_date or args.posting_time:
		s.set_posting_time = 1

	if args.posting_date:
		s.posting_date = args.posting_date
	if args.posting_time:
		s.posting_time = args.posting_time

	# map names
	if args.from_warehouse:
		args.source = args.from_warehouse
	if args.to_warehouse:
		args.target = args.to_warehouse
	if args.item_code:
		args.item = args.item_code

	if isinstance(args.qty, string_types):
		if '.' in args.qty:
			args.qty = flt(args.qty)
		else:
			args.qty = cint(args.qty)

	# purpose
	if not args.purpose:
		if args.source and args.target:
			s.purpose = "Material Transfer"
		elif args.source:
			s.purpose = "Material Issue"
		else:
			s.purpose = "Material Receipt"
	else:
		s.purpose = args.purpose

	# company
	if not args.company:
		if args.source:
			args.company = frappe.db.get_value('Warehouse', args.source, 'company')
		elif args.target:
			args.company = frappe.db.get_value('Warehouse', args.target, 'company')

	# set vales from test
	if frappe.flags.in_test:
		if not args.company:
			args.company = '_Test Company'
		if not args.item:
			args.item = '_Test Item'

	s.company = args.company or erpnext.get_default_company()
	s.purchase_receipt_no = args.purchase_receipt_no
	s.delivery_note_no = args.delivery_note_no
	s.sales_invoice_no = args.sales_invoice_no
	s.is_opening = args.is_opening or "No"
	if not args.cost_center:
		args.cost_center = frappe.get_value('Company', s.company, 'cost_center')

	if not args.expense_account and s.is_opening == "No":
		args.expense_account = frappe.get_value('Company', s.company, 'stock_adjustment_account')

	# We can find out the serial number using the batch source document
	serial_number = args.serial_no

	if not args.serial_no and args.qty and args.batch_no:
		serial_number_list = frappe.get_list(
			doctype='Stock Ledger Entry',
			fields=['serial_no'],
			filters={
				'batch_no': args.batch_no,
				'warehouse': args.from_warehouse
			}
		)
		serial_number = process_serial_numbers(serial_number_list)

	args.serial_no = serial_number

	s.append("items", {
		"item_code": args.item,
		"s_warehouse": args.source,
		"t_warehouse": args.target,
		"qty": args.qty,
		"basic_rate": args.rate or args.basic_rate,
		"conversion_factor": 1.0,
		"serial_no": args.serial_no,
		'batch_no': args.batch_no,
		'cost_center': args.cost_center,
		'expense_account': args.expense_account
	})

	s.set_stock_entry_type()
	if not args.do_not_save:
		s.insert()
		if not args.do_not_submit:
			s.submit()
	return s
