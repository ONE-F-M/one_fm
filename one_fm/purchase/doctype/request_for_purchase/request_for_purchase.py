# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import nowdate, getdate, get_url
from one_fm.utils import fetch_employee_signature
from one_fm.processor import sendemail
from frappe.utils.user import get_users_with_role
from frappe.permissions import has_permission
from one_fm.api.doc_events import get_employee_user_id
from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError

def get_users_with_role(role):
    """
    Get the users with the role

    Args:
        role: Valid role 
    """
    enabled_users = frappe.get_all("User",{'enabled':1})
    enabled_users_ = [i.name for i in enabled_users if i.name!="Administrator"]
    required_users = frappe.get_all("Has Role",{'role':role,'parent':['In',enabled_users_]},['parent'])
    if required_users:
        return [i.parent for i in required_users]
    return []


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
	def assign_users(self):
		purchase_officers = get_users_with_role("Purchase User")
		if purchase_officers:
			requested_items = '<br>'.join([i.item_name for i in self.items])
			
			add_assignment({
					'doctype': self.doctype,
					'name': self.name,
					'assign_to': purchase_officers,
					'description': _(f"""Please Note that a Request for Purchase {self.name} has been submitted.<br>
									Requested Items: {requested_items} <br>
								
                      					Please review and take necessary actions""")
				})
			
		
		
	def on_submit(self):
		# Notify the Purchase Manger about the RFP to Do further action to create the Purchase Order
		self.notify_purchase_manager()
		self.assign_users()
		
			

	def notify_purchase_manager(self):
		users = get_users_with_role('Purchase Manager')
		filtered_users = []
		page_link = get_url(self.get_url())
		notified = False
		for user in users:
			if has_permission(doctype=self.doctype, user=user):
				filtered_users.append(user)
		if filtered_users and len(filtered_users) > 0:
			message = """
				Dear Purchase Manager, <br/>
				<p>Please Review the Request for Purchase <a href='{0}'>{1}</a> Submitted by {2}.
				Do further action on the Request for Purchase to Create the Purchase Order</p>
			""".format(page_link, self.name, self.requested_by)
			subject = '{0} Request for Purchase by {1}'.format(self.status, self.requested_by)
			send_email(self, filtered_users, message, subject)
			create_notification_log(subject, message, filtered_users, self)
			frappe.msgprint(_("Notification sent to Purchase Manager"))
		self.reload()

	@frappe.whitelist()
	def make_purchase_order_for_quotation(self, warehouse=None):
		if self.items_to_order:
			wh = warehouse if warehouse else self.warehouse
			for item in self.items_to_order:
				if item.t_warehouse:
					wh = item.t_warehouse
				create_purchase_order(supplier=item.supplier, request_for_purchase=self.name, item_code=item.item_code,
					qty=item.qty, rate=item.rate, delivery_date=item.delivery_date, uom=item.uom, description=item.description,
					warehouse=wh, quotation=item.quotation)

	@frappe.whitelist()
	def accept_approve_reject_request_for_purchase(self, status, approver, accepter, reason_for_rejection=None):
		page_link = get_url(self.get_url())
		# Notify Requester
		self.notify_requester_accepter(page_link, status, [self.requested_by], "Dear {0}, <br/>".format(self.requested_by), reason_for_rejection)

		# Notify Approver
		if status == 'Accepted' and frappe.session.user == accepter:
			message = "<p>Please Review and Approve or Reject the Request for Purchase <a href='{0}'>{1}</a>, Accepted by {2}</p>".format(page_link, self.name, frappe.session.user)
			subject = '{0} Request for Purchase by {1}'.format(status, frappe.session.user)
			send_email(self, [approver], message, subject)
			create_notification_log(subject, message, [approver], self)

		# Notify Accepter
		if status in ['Draft'] or (status in ['Approved', 'Rejected'] and frappe.session.user == approver):
			self.notify_requester_accepter(page_link, status, [accepter], "Dear RFP Accepter({0}), <br/>".format(accepter), reason_for_rejection)

		self.status = status
		self.reason_for_rejection = reason_for_rejection
		self.save()
		self.reload()

	def notify_requester_accepter(self, page_link, status, recipients, message="", reason_for_rejection=None):
		message += "Request for Purchase <a href='{0}'>{1}</a> is {2} by {3}".format(page_link, self.name, status, frappe.session.user)
		if status == 'Rejected' and reason_for_rejection:
			message += " due to {0}".format(reason_for_rejection)
		subject = '{0} - Request for Purchase by {1}'.format(status, frappe.session.user)
		send_email(self, recipients, message, subject)
		create_notification_log(subject, message, recipients, self)

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
		send_email(rfm, [rfm.requested_by], message, subject)
		create_notification_log(subject, message, [rfm.requested_by], rfm)
		self.db_set('notified_the_rfm_requester', True)
		frappe.msgprint(_("Notification sent to RFM Requester"))

def send_email(doc, recipients, message, subject):
	if 'Administrator' in recipients:
		recipients.remove('Administrator')
	if recipients and len(recipients) > 0:
		sendemail(
			recipients= recipients,
			subject=subject,
			message=message,
			reference_doctype=doc.doctype,
			reference_name=doc.name
		)

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
		# if not args.do_not_submit:
		# 	po.submit()

	return po
