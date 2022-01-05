# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, get_url
from frappe import _
from frappe.utils.user import get_users_with_role
from frappe.permissions import has_permission
from erpnext.controllers.buying_controller import BuyingController
from one_fm.purchase.doctype.item_reservation.item_reservation import get_item_balance

class RequestforMaterial(BuyingController):
	def on_submit(self):
		self.notify_request_for_material_accepter()
		self.notify_request_for_material_approver()

	def notify_request_for_material_accepter(self):
		if self.request_for_material_accepter:
			page_link = get_url("/desk#Form/Request for Material/" + self.name)
			message = "<p>Please Review the Request for Material <a href='{0}'>{1}</a> Submitted by {2}.</p>".format(page_link, self.name, self.requested_by)
			subject = '{0} Request for Material by {1}'.format(self.status, self.requested_by)
			send_email(self, [self.request_for_material_accepter], message, subject)
			create_notification_log(subject, message, [self.request_for_material_accepter], self)

	def notify_request_for_material_approver(self):
		if self.request_for_material_approver:
			page_link = get_url("/desk#Form/Request for Material/" + self.name)
			message = "<p>Please Review and Approve or Reject the Request for Material <a href='{0}'>{1}</a> Submitted by {2}.</p>".format(page_link, self.name, self.requested_by)
			subject = '{0} Request for Material by {1}'.format(self.status, self.requested_by)
			send_email(self, [self.request_for_material_approver], message, subject)
			create_notification_log(subject, message, [self.request_for_material_approver], self)

	@frappe.whitelist()
	def accept_approve_reject_request_for_material(self, status, reason_for_rejection=None):
		if frappe.session.user in [self.request_for_material_accepter, self.request_for_material_approver]:
			page_link = get_url("/desk#Form/Request for Material/" + self.name)
			# Notify Requester
			self.notify_requester_accepter(page_link, status, [self.requested_by], reason_for_rejection)

			# Notify Approver
			if status == 'Accepted' and frappe.session.user == self.request_for_material_accepter and self.request_for_material_approver:
				message = "<p>Please Review and Approve or Reject the Request for Material <a href='{0}'>{1}</a>, Accepted by {2}</p>".format(page_link, self.name, frappe.session.user)
				subject = '{0} Request for Material by {1}'.format(status, frappe.session.user)
				send_email(self, [self.request_for_material_approver], message, subject)
				create_notification_log(subject, message, [self.request_for_material_approver], self)

			# Notify Accepter and requester
			if status in ['Approved', 'Rejected'] and frappe.session.user == self.request_for_material_approver and self.request_for_material_accepter:
				self.notify_requester_accepter(page_link, status, [self.request_for_material_accepter], reason_for_rejection)
				self.notify_material_requester(status, page_link)

			self.status = status
			if status == "Approved":
				# Notify Stock Manager - Stock Manger Check If Item Available
				# If Item Available then Create SE Issue and Transfer and update qty issued in the RFMItem
				# If Qty - qty Issued > 0 then Create RFP button appear
				users = get_users_with_role('Stock Manager')
				filtered_users = []
				for user in users:
					if has_permission(doctype=self.doctype, user=user):
						filtered_users.append(user)
				if filtered_users and len(filtered_users) > 0:
					self.notify_requester_accepter(page_link, status, filtered_users)

			self.reason_for_rejection = reason_for_rejection
			self.save()
			self.reload()
	def notify_material_requester(self, page_link, status):
		message = "Request for Material <a href='{0}'>{1}</a> is {2} by {3}. You will be notified of the expected delivery date as soon as the order is processed".format(page_link, self.name, status, frappe.session.user)
		subject = '{0} Request for Material by {1}'.format(status, self.requested_by)
		send_email(self, self.requested_by, message, subject)
		create_notification_log(subject, message, [self.requested_by], self)

	def notify_requester_accepter(self, page_link, status, recipients, reason_for_rejection=None):
		message = "Request for Material <a href='{0}'>{1}</a> is {2} by {3}".format(page_link, self.name, status, frappe.session.user)
		if status == 'Rejected' and reason_for_rejection:
			message += " due to {0}".format(reason_for_rejection)
		subject = '{0} Request for Material by {1}'.format(status, frappe.session.user)
		send_email(self, recipients, message, subject)
		create_notification_log(subject, message, recipients, self)

	def validate(self):
		self.validate_details_against_type()
		self.set_request_for_material_accepter_and_approver()
		self.set_item_fields()
		self.set_title()
		self.validate_item_qty()
		# self.validate_item_reservation()


	def validate_item_reservation(self):
		# validate item reservation
		added_items = []
		item_reservation_dict = {}
		for item in self.items:
			reservation = frappe.db.sql(f"""
				SELECT name, item_code, item_name, sum(qty) as qty, issued_qty,
				from_date, to_date
				FROM `tabItem Reservation`
				WHERE item_code="{item.item_code}" AND docstatus=1 AND status in ('Active')
				AND '{self.schedule_date}' BETWEEN from_date AND to_date
				GROUP BY item_code
			;""", as_dict=1)
			if(len(reservation)>0):
				# get_balance
				balance = get_item_balance(item.item_code)['total']
				if(item.qty>(balance-(reservation[0].qty-reservation[0].issued_qty))):
					added_items.append({
						'reserved': reservation[0].name,
						'issued': reservation[0].issued_qty,
						'from_date': reservation[0].from_date,
						'to_date': reservation[0].to_date,
						'item_code':item.item_code,
						'item_name': reservation[0].item_name,
						'reserved': reservation[0].qty,
						'reqd': item.qty,
						'available': balance-reservation[0].qty-reservation[0].issued_qty,
						'url': frappe.get_doc('Item Reservation', reservation[0].name).get_url()
					})
		# check added_items
		if(added_items):
			template = frappe.render_template(
				"one_fm/purchase/doctype/item_reservation/templates/reserved_rfm.html",
				context={'added_items':added_items})
			frappe.throw(template, title='Following items have been reserved.')


    #in process
	def validate_item_qty(self):
		if self.items:
			for d in self.items:
				if not d.qty:
					frappe.throw(_("No quantity set for {item}".format(item=d.item_name)))
				if d.actual_qty:
					if int(d.qty) > d.actual_qty:
						d.pur_qty = int(d.qty) - d.actual_qty
				elif d.actual_qty == 0:
					d.pur_qty = d.qty

				if d.actual_qty:
					if d.warehouse and flt(d.actual_qty, d.precision("actual_qty")) < flt(d.qty, d.precision("actual_qty")):
						frappe.msgprint(_("Row {0}: Quantity not available for {2} in warehouse {1}").format(d.idx,
							frappe.bold(d.warehouse), frappe.bold(d.item_code))
							+ '<br><br>' + _("Available quantity is {0}, Requested quantity is {1}. Please make a purchase request for the remaining.").format(frappe.bold(d.actual_qty),
								frappe.bold(d.qty)), title=_('Insufficient Stock'))

				if d.quantity_to_transfer and d.pur_qty:
					if (d.quantity_to_transfer+d.pur_qty)>d.qty:
						updated_total = d.quantity_to_transfer+d.pur_qty
						frappe.throw(_("Row {0}: Total quantity to transfer and purchase cannot exceed the original requested Quantiy: {1} for the Item: {2}").format(d.idx,
							frappe.bold(d.qty), frappe.bold(d.item_code))
							+ '<br><br>' + _("Current total quantity to purchase/transfer is {0}, Requested quantity is {1}. Please make a purchase request for the remaining.").format(frappe.bold(updated_total),
								frappe.bold(d.qty)), title=_('Quantity Exceeding'))

	def set_item_fields(self):
		if self.items and self.type == 'Stock':
			for item in self.items:
				item.requested_item_name = item.item_name
				item.requested_description = item.description

	def set_request_for_material_accepter_and_approver(self):
		if not self.request_for_material_accepter:
			self.request_for_material_accepter = frappe.db.get_value('Purchase Settings', None, 'request_for_material_accepter')
		if not self.request_for_material_approver:
			self.request_for_material_approver = frappe.db.get_value('Purchase Settings', None, 'request_for_material_approver')

	def validate_details_against_type(self):
		if self.type:
			if self.type == 'Individual':
				self.project = ''
				self.project_details = ''
			if self.type == 'Project Mobilization':
				self.employee = ''
				self.employee_name = ''
				self.department = ''
			if self.type == 'Project':
				self.employee = ''
				self.employee_name = ''
				self.department = ''

	def set_title(self):
		'''Set title as comma separated list of items'''
		# if not self.title:
		items = ', '.join([d.requested_item_name for d in self.items][:3])
		self.title = _('Material Request for {0}').format(items)[:100]

	def on_update_after_submit(self):
		self.validate_item_qty()
		from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError, remove as remove_assignment
		if self.technical_verification_needed == 'Yes' and self.technical_verification_from and not self.technical_remarks:
			try:
				add_assignment({
					'doctype': self.doctype,
					'name': self.name,
					'assign_to': self.technical_verification_from,
					'description': _('Please add Your Technical Remarks for the Item Descriptions')
				})
				self.add_comment("Comment", _("Waiting for Technical Verification"))
			except DuplicateToDoError:
				frappe.message_log.pop()
				pass
		elif self.technical_verification_needed == "No" and self.technical_verification_from:
			remove_assignment(self.doctype, self.name, self.technical_verification_from)

	def check_modified_date(self):
		mod_db = frappe.db.sql("""select modified from `tabRequest for Material` where name = %s""",
			self.name)
		date_diff = frappe.db.sql("""select TIMEDIFF('%s', '%s')"""
			% (mod_db[0][0], cstr(self.modified)))

		if date_diff and date_diff[0][0]:
			frappe.throw(_("{0} {1} has been modified. Please refresh.").format(_(self.doctype), self.name))

	def update_status(self, status):
		self.check_modified_date()
		self.status_can_change(status)
		# self.set_status(update=True, status=status)
		self.db_set('status', status)

	def status_can_change(self, status):
		"""
		validates that `status` is acceptable for the present controller status
		and throws an Exception if otherwise.
		"""
		if self.status and self.status == 'Cancelled':
			# cancelled documents cannot change
			if status != self.status:
				frappe.throw(
					_("{0} {1} is cancelled so the action cannot be completed").
						format(_(self.doctype), self.name),
					frappe.InvalidStatusError
				)

		elif self.status and self.status == 'Draft':
			# draft document to pending only
			if status != 'Pending':
				frappe.throw(
					_("{0} {1} has not been submitted so the action cannot be completed").
						format(_(self.doctype), self.name),
					frappe.InvalidStatusError
				)
    #For quantities available in warehouse
	def update_completed_qty(self, mr_items=None, update_modified=True):
		if not mr_items:
			mr_items = [d.name for d in self.get("items")]

		for d in self.get("items"):
			if d.name in mr_items:
				if self.type in ("Individual", "Project", "Project Mobilization","Stock","Onboarding"):
					d.ordered_qty =  flt(frappe.db.sql("""select sum(qty)
						from `tabStock Entry Detail` where one_fm_request_for_material = %s
						and one_fm_request_for_material_item = %s and docstatus = 1""",
						(self.name, d.name))[0][0])

					if d.ordered_qty and d.ordered_qty > d.stock_qty:
						frappe.throw(_("The total Issue / Transfer quantity {0} in Material Request {1}  \
							cannot be greater than requested quantity {2} for Item {3}").format(d.ordered_qty, d.parent, d.qty, d.item_code))

				frappe.db.set_value(d.doctype, d.name, "ordered_qty", d.ordered_qty)
	#for quantities that had to be purchased
	def update_purchased_qty(self, mr_items=None, update_modified=True):
		if not mr_items:
			mr_items = [d.name for d in self.get("items")]

		for d in self.get("items"):
			if d.name in mr_items:
				if self.type in ("Individual", "Project", "Project Mobilization","Stock","Onboarding"):
					d.purchased_qty =  flt(frappe.db.sql("""select sum(qty)
						from `tabPurchase Order Item` where material_request = %s
						and material_request_item = %s and docstatus = 1""",
						(self.name, d.name))[0][0])
					d.ordered_qty = d.ordered_qty + d.purchased_qty

				frappe.db.set_value(d.doctype, d.name, "purchased_qty", d.purchased_qty)
				frappe.db.set_value(d.doctype, d.name, "ordered_qty", d.ordered_qty)

		self._update_percent_field({
			"target_dt": "Request for Material Item",
			"target_parent_dt": self.doctype,
			"target_parent_field": "per_ordered",
			"target_ref_field": "stock_qty",
			"target_field": "ordered_qty",
			"name": self.name,
		}, update_modified)

	@frappe.whitelist()
	def create_reservation(self, filters):
		# create item reservation
		try:
			filters = frappe._dict(filters)
			reservation = frappe.get_doc({
				'doctype': 'Item Reservation',
				'item_code': filters.item_code,
				'qty':filters.qty,
				'rfm':filters.rfm,
				'from_date':filters.from_date,
				'to_date':filters.to_date,
				'comment': filters.comment
			})
			# reservation.flags.ignore = True
			reservation.submit()
			return reservation
		except Exception as e:
			frappe.throw(str(e))

def update_completed_and_requested_qty(stock_entry, method):
		if stock_entry.doctype == "Stock Entry":
			material_request_map = {}

			for d in stock_entry.get("items"):
				if d.one_fm_request_for_material:
					material_request_map.setdefault(d.one_fm_request_for_material, []).append(d.one_fm_request_for_material_item)

			for mr, mr_item_rows in material_request_map.items():
				if mr and mr_item_rows:
					mr_obj = frappe.get_doc("Request for Material", mr)

					if mr_obj.status in ["Stopped", "Cancelled"]:
						frappe.throw(_("{0} {1} is cancelled or stopped").format(_("Request for Material"), mr),
							frappe.InvalidStatusError)

					mr_obj.update_completed_qty(mr_item_rows)

def update_completed_purchase_qty(purchase_order, method):
		if purchase_order.doctype == "Purchase Order":
			material_request_map = {}

			for d in purchase_order.get("items"):
				if d.material_request:
					material_request_map.setdefault(d.request_for_material, []).append(d.material_request_item)

			for mr, mr_item_rows in material_request_map.items():
				if mr and mr_item_rows:
					mr_obj = frappe.get_doc("Request for Material", mr)

					if mr_obj.status in ["Stopped", "Cancelled"]:
						frappe.throw(_("{0} {1} is cancelled or stopped").format(_("Request for Material"), mr),
							frappe.InvalidStatusError)

					mr_obj.update_purchased_qty(mr_item_rows)
def send_email(doc, recipients, message, subject):
	frappe.sendmail(
		recipients= recipients,
		subject=subject,
		message=message,
		reference_doctype=doc.doctype,
		reference_name=doc.name
	)

def create_notification_log(subject, message, for_users, reference_doc):
	for user in for_users:
		doc = frappe.new_doc('Notification Log')
		doc.subject = subject
		doc.email_content = message
		doc.for_user = user
		doc.document_type = reference_doc.doctype
		doc.document_name = reference_doc.name
		doc.from_user = reference_doc.modified_by
		doc.insert(ignore_permissions=True)

@frappe.whitelist()
def bring_designation_items(designation):
	designation_doc = frappe.get_doc('Designation Profile', designation)
	item_list = []
	if designation_doc:
		for item in designation_doc.get("uniforms"):
			item_list.append({
				'item':item.item,
				'item_name':item.item_name,
				'quantity':item.quantity,
				'uom':item.uom
			})
		for item in designation_doc.get("accommodation_assets"):
			item_list.append({
				'item':item.item,
				'item_name':item.item_name,
				'quantity':item.quantity,
				'uom':item.uom
			})
		for item in designation_doc.get("accommodation_consumables"):
			item_list.append({
				'item':item.item,
				'item_name':item.item_name,
				'quantity':item.quantity,
				'uom':item.uom
			})
	else:
		frappe.throw(_("No profile found for {}").format(designation))
	return {'item_list': item_list}

@frappe.whitelist()
def bring_erf_items(erf):
	erf_doc = frappe.get_doc('ERF', erf)
	item_list = []
	if erf_doc:
		for item in erf_doc.get("tool_request_item"):
			item_list.append({
				# 'item':item.item,
				'item_name':item.item,
				'quantity':item.quantity,
				# 'uom':item.uom
			})
	else:
		frappe.throw(_("No ERF named {} exist").format(erf))
	return {'item_list': item_list}

@frappe.whitelist()
def update_status(name, status):
	request_for_material = frappe.get_doc('Request for Material', name)
	request_for_material.check_permission('write')
	request_for_material.update_status(status)

@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		# qty = flt(obj.qty)/ target.conversion_factor \
		# 	if flt(obj.actual_qty) > flt(obj.qty) else flt(obj.quantity_to_transfer)
		qty = obj.quantity_to_transfer
		target.qty = qty
		target.transfer_qty = qty * obj.conversion_factor
		target.conversion_factor = obj.conversion_factor

		target.s_warehouse = obj.warehouse
		target.t_warehouse = obj.t_warehouse

	def set_missing_values(source, target):
		target.purpose = 'Material Transfer'
		target.run_method("calculate_rate_and_amount")
		target.set_stock_entry_type()
		target.set_job_card_data()

	doclist = get_mapped_doc("Request for Material", source_name, {
		"Request for Material": {
			"doctype": "Stock Entry",
			"field_map": [
				["name", "one_fm_request_for_material"]
			],
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Material Item": {
			"doctype": "Stock Entry Detail",
			"field_map": {
				"uom": "stock_uom",
				"name": "one_fm_request_for_material_item",
				"parent": "one_fm_request_for_material"
			},
			"postprocess": update_item,
			"condition": lambda doc: (doc.item_code and doc.reject_item==0)
		}
	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def make_stock_entry_issue(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		# qty = flt(obj.qty)/ target.conversion_factor \
		# 	if flt(obj.actual_qty) > flt(obj.qty) else flt(obj.quantity_to_transfer)
		qty = obj.quantity_to_transfer
		target.qty = qty
		target.transfer_qty = qty * obj.conversion_factor
		target.conversion_factor = obj.conversion_factor

		target.s_warehouse = obj.warehouse
		target.t_warehouse = obj.t_warehouse

	def set_missing_values(source, target):
		target.purpose = 'Material Transfer'
		target.run_method("calculate_rate_and_amount")
		target.set_stock_entry_type()
		target.set_job_card_data()

	doclist = get_mapped_doc("Request for Material", source_name, {
		"Request for Material": {
			"doctype": "Stock Entry",
			"field_map": [
				["name", "one_fm_request_for_material"]
			],
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Material Item": {
			"doctype": "Stock Entry Detail",
			"field_map": {
				"uom": "stock_uom",
				"name": "one_fm_request_for_material_item",
				"parent": "one_fm_request_for_material"
			},
			"postprocess": update_item,
			"condition": lambda doc: (doc.item_code and doc.reject_item==0)
		}
	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		qty = flt(flt(obj.stock_qty) - flt(obj.ordered_qty))/ target.conversion_factor \
			if flt(obj.stock_qty) > flt(obj.ordered_qty) else 0
		target.qty = qty
		target.transfer_qty = qty * obj.conversion_factor
		target.conversion_factor = obj.conversion_factor

		# target.t_warehouse = obj.warehouse

	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	doclist = get_mapped_doc("Request for Material", source_name, {
		"Request for Material": {
			"doctype": "Sales Invoice",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Material Item": {
			"doctype": "Sales Invoice Item",
			"field_map": {
				"uom": "stock_uom"
			},
			"postprocess": update_item,
			"condition": lambda doc: (doc.item_code and doc.reject_item==0)
		}
	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def make_request_for_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc("Request for Material", source_name, 	{
		"Request for Material": {
			"doctype": "Request for Supplier Quotation",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Material Item": {
			"doctype": "Request for Supplier Quotation Item",
			"field_map": [
				["name", "request_for_material_item"],
				["parent", "request_for_material"]
			],
			"condition": lambda doc: not doc.item_code
		}
	}, target_doc)

	return doclist

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None):
	doclist = get_mapped_doc("Request for Material", source_name, 	{
		"Request for Material": {
			"doctype": "Delivery Note",
			"field_map": [
				["name", "request_for_material"]
			],
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Material Item": {
			"doctype": "Delivery Note Item",
			"field_map": [
				["requested_description", "description"],
				["requested_item_name", "item_name"],
				["name", "request_for_material_item"],
				["parent", "request_for_material"]
			]
		}
	}, target_doc)

	return doclist

@frappe.whitelist()
def make_request_for_purchase(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		qty = obj.pur_qty
		target.qty = qty
	doclist = get_mapped_doc("Request for Material", source_name, 	{
		"Request for Material": {
			"doctype": "Request for Purchase",
			"field_map": [
				["name", "request_for_material"],
				["t_warehouse","warehouse"]
			],
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Material Item": {
			"doctype": "Request for Purchase Item",
			"field_map": [
				["requested_description", "description"],
				["requested_item_name", "item_name"],
				["name", "request_for_material_item"],
				["parent", "request_for_material"]
			],
			"postprocess": update_item,
			"condition": lambda doc: (doc.item_code and doc.reject_item==0)
		}
	}, target_doc)

	return doclist
