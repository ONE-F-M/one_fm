# Copyright (c) 2021, omar jaber, Anthony Emmanuel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today
from frappe import _
from frappe.model.document import Document
from erpnext.stock.doctype.quick_stock_balance.quick_stock_balance import get_stock_item_details

class ItemReservation(Document):

	def validate(self):
		self.check_date()
		self.check_qty()
		self.check_balance()
		self.validate_reservation_date()

	def before_submit(self):
		self.status = 'Active'


	def check_date(self):
		# check for backdating
		if(self.from_date < today() or self.to_date < today()):
			frappe.throw(_('You cannot backdate reservation date.'))

	def check_qty(self):
		# validate qty must be greater than 0
		if(self.qty<=0):
			frappe.throw(_('You cannot reserve 0 or less item.'))

	def check_balance(self):
		# check item balance against reservation qty
		item_balance = get_item_balance(self.item_code)
		if(item_balance < self.qty):
			frappe.throw(
				f"""
					Reservation QTY <b>{self.qty}</b> is greater than available QTY <b>{item_balance}</b>
					<br>for item <b>{self.item_code}</b>.
				"""
			)

	def validate_reservation_date(self):
		# validate no reservation within selected date range
		if(frappe.db.exists(
				{
					'doctype':self.doctype,
					'item_code':self.item_code,
					'docstatus':1,
					'from_date': [">=", self.from_date],
					'to_date': ["<=", self.to_date]
				}
			)):
			print(True)
		else:
			print(False)



@frappe.whitelist()
def get_item_balance(item_code):
	# get item balance from all warehouse
	warehouses = [warehouse.name for warehouse in frappe.db.sql("""
		SELECT name FROM `tabWarehouse` WHERE is_group=0;
	""", as_dict=1)]
	total = 0
	for warehouse in warehouses:
		total += get_stock_item_details(
			warehouse, today(),
			item=item_code, barcode=None
		)['qty']
	print(total)
	return total
