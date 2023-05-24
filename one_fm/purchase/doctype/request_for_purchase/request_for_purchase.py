# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import nowdate, getdate, get_url, get_fullname
from one_fm.processor import sendemail
from frappe.utils.user import get_users_with_role
from frappe.permissions import has_permission
from one_fm.api.doc_events import get_employee_user_id
from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError
from one_fm.utils import send_workflow_action_email, get_users_with_role_permitted_to_doctype

class RequestforPurchase(Document):
	def onload(self):
		self.get_accepter_and_approver()

	def validate(self):
		accepter, approver = self.get_accepter_and_approver()
		if not self.approver:
			self.approver = approver
		if not self.accepter:
			self.accepter = accepter

	def get_accepter_and_approver(self):
		accepter = frappe.db.get_value('Purchase Settings', None, 'request_for_purchase_accepter')
		approver = frappe.db.get_value('Purchase Settings', None, 'request_for_purchase_approver')
		reports_to = False
		if self.type == 'Project' and self.project:
			reports_to = frappe.db.get_value('Project', self.project, 'account_manager')
		elif self.employee:
			reports_to = frappe.db.get_value('Employee', self.employee, 'reports_to')
		if reports_to:
			approver = get_employee_user_id(reports_to)
			if approver:
				accepter = approver
		self.set_onload('accepter', accepter)
		self.set_onload('approver', approver)
		return accepter, approver

	def on_submit(self):
		if self.workflow_state == 'Submit to Purchase Officer':
			self.assign_purchase_officer()

	def assign_purchase_officer(self):
		purchase_officers = get_users_with_role_permitted_to_doctype('Purchase Officer', self.doctype)
		if purchase_officers:
			requested_items = '<br>'.join([i.item_name for i in self.items])
			add_assignment({
				'doctype': self.doctype,
				'name': self.name,
				'assign_to': purchase_officers,
				'description':
				_(
					f"""
						Please Note that a Request for Purchase {self.name} has been submitted.<br>
						Requested Items: {requested_items} <br>
						Please review and take necessary actions
					"""
				)
			})

	def on_update_after_submit(self):
		if self.workflow_state == 'Pending Approval':
			self.validate_items_to_order()
			purchase_managers = get_users_with_role_permitted_to_doctype('Purchase Manager', self.doctype)
			if purchase_managers:
				send_workflow_action_email(self, purchase_managers)
			else:
				self.add_comment("Comment", _("Not able to send workflow action to Purchase Manager, because there is no user with role <b>Purchase Manager</b>"))

		if self.workflow_state in ['Approved', 'Rejected']:
			self.notify_purchase_officer()

	def notify_purchase_officer(self):
		if 'Purchase Officer' not in frappe.get_roles(frappe.session.user):
			purchase_officers = get_users_with_role_permitted_to_doctype('Purchase Officer', self.doctype)
			if purchase_officers:
				page_link = get_url(self.get_url())
				message = """
					Dear Purchase Officer,
					<br/>
					<p>
						The Request for Purchase <a href='{0}'>{1}</a> is {2} by {3}.
						Now you can initiate the Purchase Order
					</p>
				""".format(page_link, self.name, self.workflow_state, get_fullname(frappe.session.user))
				subject = '{0} Request for Purchase by {1}'.format(self.workflow_state, get_fullname(self.requested_by))
				sendemail(recipients=purchase_officers, subject=subject, message=message, reference_doctype=self.doctype, reference_name=self.name)
				create_notification_log(subject, message, purchase_officers, self)
				frappe.msgprint(_("Notification sent to Purchase Officer"))

	def validate_items_to_order(self):
		if not self.items_to_order:
			frappe.throw(_("Fill Items to Order to Submit for Approval"))
		no_item_code_in_items_to_order = [item.idx for item in self.items_to_order if (not item.item_code or not item.supplier)]
		if no_item_code_in_items_to_order and len(no_item_code_in_items_to_order) > 0:
			frappe.throw(_("Set Item Code/Supplier in <b>Items to Order</b> rows {0}".format(no_item_code_in_items_to_order)))

	@frappe.whitelist()
	def make_purchase_order_for_quotation(self, warehouse=None):
		if self.items_to_order:
			wh = warehouse if warehouse else self.warehouse
			for item in self.items_to_order:
				if item.t_warehouse:
					wh = item.t_warehouse
				create_purchase_order(supplier=item.supplier, request_for_purchase=self.name, item_code=item.item_code,
					qty=item.qty, rate=item.rate, delivery_date=item.delivery_date, uom=item.uom, description=item.description,
					warehouse=wh, quotation=item.quotation, do_not_submit=True)

	@frappe.whitelist()
	def notify_the_rfm_requester(self):
		rfm = frappe.get_doc('Request for Material', self.request_for_material)
		page_link = get_url(rfm.get_url())
		message = "Not able to fulfil the RFM <a href='{0}'>{1}</a>".format(page_link, rfm.name)
		message += "<br/> due to lack of availabilty of the item(s) listed below with the specification"
		message += "<ul>"
		for item in self.items:
			availabilty = False
			for items_to_order in self.items_to_order:
				if item.item_name == items_to_order.item_name:
					availabilty = True
			if not availabilty:
				message += "<li>" + item.item_name +"</li>"
		message += "</ul>"
		subject = "Not able to fulfil the RFM <a href='{0}'>{1}</a>".format(page_link, rfm.name)
		sendemail(recipients=[rfm.requested_by], subject=subject, message=message, reference_doctype=rfm.doctype, reference_name=rfm.name)
		create_notification_log(subject, message, [rfm.requested_by], rfm)
		self.db_set('notified_the_rfm_requester', True)
		frappe.msgprint(_("Notification sent to RFM Requester"))

def create_notification_log(subject, message, for_users, reference_doc):
	if 'Administrator' in for_users:
		for_users.remove('Administrator')
	for user in for_users:
		doc = frappe.new_doc('Notification Log')
		doc.subject = subject
		doc.email_content = message
		doc.for_user = user
		doc.document_type = reference_doc.doctype
		doc.document_name = reference_doc.name
		doc.from_user = reference_doc.modified_by
		# If notification log type is Alert then it will not send email for the log
		doc.type = 'Alert'
		doc.insert(ignore_permissions=True)

@frappe.whitelist()
def make_request_for_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc("Request for Purchase", source_name, 	{
		"Request for Purchase": {
			"doctype": "Request for Supplier Quotation",
			"field_map": [
				["name", "request_for_purchase"]
			],
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Purchase Item": {
			"doctype": "Request for Supplier Quotation Item",
			"field_map": [
				["uom", "uom"]
			]
		}
	}, target_doc)

	return doclist

@frappe.whitelist()
def make_quotation_comparison_sheet(source_name, target_doc=None):
	doclist = get_mapped_doc("Request for Purchase", source_name, 	{
		"Request for Purchase": {
			"doctype": "Quotation Comparison Sheet",
			"field_map": [
				["name", "request_for_purchase"]
			],
			"validation": {
				"docstatus": ["=", 1]
			}
		}
	}, target_doc)
	rfq = frappe.db.get_value('Request for Supplier Quotation', {'request_for_purchase': doclist.request_for_purchase}, 'name')
	doclist.request_for_quotation = rfq if rfq else ''
	return doclist

@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("get_schedule_dates")
		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		target.stock_qty = obj.qty # flt(obj.qty) * flt(obj.conversion_factor)

	doclist = get_mapped_doc("Request for Purchase", source_name,		{
		"Request for Purchase": {
			"doctype": "Purchase Order",
			"validation": {
				"docstatus": ["=", 1],
			}
		},
		"Request for Purchase Quotation Item": {
			"doctype": "Purchase Order Item",
			"field_map": [
				["quotation_item", "supplier_quotation_item"],
				["quotation", "supplier_quotation"],
				["request_for_material", "request_for_material"],
				["request_for_material_item", "request_for_material_item"],
				["sales_order", "sales_order"]
			],
			"postprocess": update_item
		}
	}, target_doc, set_missing_values)

	return doclist

def create_purchase_order(**args):
	args = frappe._dict(args)
	po_id = frappe.db.exists('Purchase Order',
		{'one_fm_request_for_purchase': args.request_for_purchase, 'docstatus': ['<', 2], 'supplier': args.supplier}
	)
	if po_id:
		po = frappe.get_doc('Purchase Order', po_id)
	else:
		po = frappe.new_doc("Purchase Order")
		po.transaction_date = nowdate()
		po.set_warehouse = args.warehouse
		po.quotation = args.quotation
		# po.schedule_date = add_days(nowdate(), 1)
		# po.company = args.company
		po.supplier = args.supplier
		po.is_subcontracted = args.is_subcontracted or "No"
		# po.currency = args.currency or frappe.get_cached_value('Company',  po.company,  "default_currency")
		po.conversion_factor = args.conversion_factor or 1
		po.supplier_warehouse = args.supplier_warehouse or None
		po.one_fm_request_for_purchase = args.request_for_purchase
		po.is_subcontracted = False

	po.append("items", {
		"item_code": args.item_code,
		"item_name": args.item_name,
		"description": args.description,
		"uom": args.uom,
		"qty": args.qty,
		"rate": args.rate,
		"amount": args.qty * args.rate,
		"schedule_date": getdate(args.delivery_date) if (args.delivery_date and getdate(nowdate()) < getdate(args.delivery_date)) else getdate(nowdate()),
		"expected_delivery_date": args.delivery_date
	})
	if not args.do_not_save:
		po.save(ignore_permissions=True)
		if not args.do_not_submit:
			po.submit()
