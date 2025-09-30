# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import nowdate, getdate, get_url, get_fullname
from one_fm.processor import sendemail
from frappe.utils.user import get_users_with_role
from frappe.permissions import has_permission
from one_fm.api.doc_events import get_employee_user_id
from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError
from one_fm.utils import get_users_with_role_permitted_to_doctype

class RequestforPurchase(Document):
	def onload(self):
		self.set_onload('exists_qfs', False)
		if frappe.db.get_value('Quotation From Supplier', {'request_for_purchase': self.name}, 'name'):
			self.set_onload('exists_qfs', True)

	def on_submit(self):
		self.assign_purchase_officer()
		self._update_linked_rfm_quantities()
  
	def on_update_after_submit(self):
		self._update_linked_rfm_quantities()
  
	def after_insert(self):
		self._update_linked_rfm_quantities()
  
	def on_update(self):
		self._update_linked_rfm_quantities()
  
	def on_trash(self):
		self._update_linked_rfm_quantities(delete_event=True)
  
	def on_cancel(self):
		self._update_linked_rfm_quantities(delete_event=True)

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

	def validate_items_to_order(self):
		if not self.items_to_order:
			frappe.throw(_("Fill Items to Order!"))
		no_item_code_in_items_to_order = [item.idx for item in self.items_to_order if (not item.item_code or not item.supplier)]
		if no_item_code_in_items_to_order and len(no_item_code_in_items_to_order) > 0:
			frappe.throw(_("Set Item Code/Supplier in <b>Items to Order</b> rows {0}".format(no_item_code_in_items_to_order)))

		# Get items qty is greater than the requested qty
		items = [item.idx for item in self.items_to_order if (item.qty_requested and item.qty_requested < item.qty)]
		if items and len(items) > 0:
			frappe.throw(_("Items <b>Items Order</b> are greater in quantity than requested in rows {0}".format(items)))

		
	@frappe.whitelist()
	def make_purchase_order_for_quotation(self, warehouse=None):
		self.validate_items_to_order()
		created_pos = []
		skipped_items = []
		
		if self.items_to_order:
			wh = warehouse if warehouse else self.warehouse
			
			supplier_groups = {}
			for item in self.items_to_order:
				if item.supplier not in supplier_groups:
					supplier_groups[item.supplier] = []
				
				supplier_groups[item.supplier].append({
					"item_code": item.item_code,
					"qty": item.qty,
					"rate": item.rate,
					"delivery_date": item.delivery_date,
					"uom": item.uom,
					"description": item.description,
					"warehouse": item.t_warehouse if item.t_warehouse else wh,
					"quotation": item.quotation,
					"item_name": getattr(item, 'item_name', None)
				})
			
			for supplier, items_list in supplier_groups.items():
				po = create_purchase_order(
					supplier=supplier,
					request_for_purchase=self.name,
					warehouse=wh,
					items_list=items_list,
					do_not_submit=True
				)
				
				if po:
					created_pos.append(po.name)
				else:
					skipped_items.extend([item["item_code"] for item in items_list])
		
		if created_pos:
			frappe.msgprint(f"Created Purchase Orders: {', '.join(created_pos)}")
		
		if skipped_items:
			frappe.msgprint(f"Skipped items (no pending quantity): {', '.join(skipped_items)}")
		
		return {
			'created_pos': created_pos,
			'skipped_items': skipped_items
		}

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
  
	def validate_rfm_quantity(self):
		for one in self.items:
			rfm_qty = None
			total_qty = 0
			if one.custom_request_for_material_item:
				other_pr_rows = frappe.get_all(one.doctype,{'custom_request_for_material_item':one.custom_request_for_material_item,'parent': ['!=', self.name],'docstatus': ['!=', 2]},['parent','qty'])
				if other_pr_rows:
					total_qty = sum([row.qty for row in other_pr_rows])
				total_qty += one.qty
				if one.rfm_quantity>0:
					rfm_qty = one.rfm_quantity
				else:
					rfm_item = frappe.db.get_value("Request for Material Item", one.custom_request_for_material_item, ["qty", "custom_pending_quantity"], as_dict=True)
					rfm_qty = rfm_item.qty
				if  total_qty > rfm_qty:
					frappe.throw(_("Setting Row {0}: Quantity as <b>{1}</b> for item <b>{2}</b> will make the total quantity from across various Requests for Purchase as <b>{3}</b> and will the exceed quantity <b>{4}</b> in the linked Request for Material").format(one.idx, one.qty, one.item_name, total_qty,rfm_qty ), title=_("Quantity Exceeds Pending Quantity"))
	
	def _update_linked_rfm_quantities(self,delete_event = False):
		"""
		Recalculates the custom_rfp_quantity and custom_pending_quantity
		on the source Request for Material based on all linked RFPs.
		This method is called from hooks to ensure data is always in sync.
		"""
		self.validate_rfm_quantity()
		if not self.request_for_material:
			return

		rfm_name = self.request_for_material

		# Get the sum of quantities for all items from all non-cancelled RFPs
		# linked to the specific Request for Material in a single query.
		delete_condition =""
		if delete_event:
			delete_condition = " AND rfpi.parent != %(current_rfp)s "
		rfp_item_totals = frappe.db.sql("""
			SELECT
				rfpi.custom_request_for_material_item,
				SUM(rfpi.qty) as total_rfp_qty
			FROM
				`tabRequest for Purchase Item` AS rfpi
			JOIN
				`tabRequest for Purchase` AS rfp ON rfpi.parent = rfp.name
			WHERE
				rfp.request_for_material = %(rfm_name)s
				AND rfp.docstatus != 2 """ + delete_condition + """
			GROUP BY
				rfpi.custom_request_for_material_item
		""", {"rfm_name": rfm_name,'current_rfp':self.name}, as_dict=1)

		rfp_totals_map = {
			d.custom_request_for_material_item: d.total_rfp_qty
			for d in rfp_item_totals if d.custom_request_for_material_item
		}

		rfm_doc = frappe.get_doc("Request for Material", rfm_name)

		# Build a map of item_name to total_rfp_qty from self.items
		
		

		for rfm_item in rfm_doc.items:
			total_ordered_qty = rfp_totals_map.get(rfm_item.name, 0)
			pending_qty = rfm_item.qty - total_ordered_qty

			# Update RFM item fields directly to avoid triggering circular hooks
			if (rfm_item.custom_rfp_quantity != total_ordered_qty or rfm_item.custom_pending_quantity != pending_qty):
				frappe.db.set_value("Request for Material Item", rfm_item.name, {
					"custom_rfp_quantity": total_ordered_qty,
					"custom_pending_quantity": pending_qty
				}, update_modified=False)

		# After updating all items, update the modified timestamp on the parent RFM
		# frappe.db.update("Request for Material", rfm_name)


	def before_cancel(self):
		if self.workflow_state == "Rejected":
			self.check_related_pos_before_cancel()

	def check_related_pos_before_cancel(self):
		approved_pos = frappe.db.get_list('Purchase Order', {
			'one_fm_request_for_purchase': self.name,
			'docstatus': 1,
			'workflow_state': 'Approved'
		}, ['name'])
		
		draft_pos = frappe.db.get_list('Purchase Order', {
			'one_fm_request_for_purchase': self.name,
			'docstatus': ['in', [0, 1]],
			'workflow_state': 'Draft'
		}, ['name'])
		
		pending_pos = frappe.db.get_list('Purchase Order', {
			'one_fm_request_for_purchase': self.name,
			'docstatus': ['in', [0, 1]],
			'workflow_state': ['in', ['Pending Purchase Manager', 'Pending Finance Approver']]
		}, ['name', 'workflow_state'])
		
		if approved_pos:
			if pending_pos:
				approved_list = ", ".join([po.name for po in approved_pos])
				other_list = ", ".join([po.name for po in pending_pos])
				frappe.throw(
					_("Please note that {0} has related Purchase Orders in different stages: {1} > Pending Approval, {2} > Approved. Cancellation of this RFP is not allowed while Approved POs exist. You must first cancel the Approved POs.").format(
						self.name, other_list, approved_list
					),
					title=_("Cancellation Blocked – Mixed Purchase Order Stages Found"),
					exc=frappe.ValidationError
				)
			else:
				po_list = ", ".join([po.name for po in approved_pos])
				frappe.throw(
					_("Please note that {0} has related Purchase Orders ({1}) in Approved stage. To proceed, you must first cancel these Purchase Orders. Cancellation of this RFP is not allowed until all related POs are cancelled.").format(
						self.name, po_list
					),
					title=_("RFP Cancellation blocked. Approved Purchase Order found."),
					exc=frappe.ValidationError
				)

		elif draft_pos and pending_pos:
			all_draft_pending = draft_pos + pending_pos
			self.delete_related_pos(all_draft_pending)

		elif draft_pos:
			self.delete_related_pos(draft_pos)

		elif pending_pos:
			self.delete_related_pos(pending_pos)

	def delete_related_pos(self, related_pos):
		for po in related_pos:
			try:
				po_doc = frappe.get_doc('Purchase Order', po.name)
				
				if po_doc.docstatus == 1:
					po_doc.cancel()
				
				frappe.delete_doc('Purchase Order', po.name, force=1)
				
			except Exception as e:
				frappe.log_error(f"Error deleting PO {po.name}: {str(e)}")
				frappe.throw(_("Error deleting Purchase Order {0}: {1}").format(po.name, str(e)))



@frappe.whitelist()
def check_related_pos_before_cancel(doc):
    doc_dict = json.loads(doc)
    
    approved_pos = frappe.db.get_list('Purchase Order', {
        'one_fm_request_for_purchase': doc_dict.get('name'),
        'docstatus': 1,
        'workflow_state': 'Approved'
    }, ['name'])
    
    draft_pos = frappe.db.get_list('Purchase Order', {
        'one_fm_request_for_purchase': doc_dict.get('name'),
        'docstatus': ['in', [0, 1]],
        'workflow_state': 'Draft'
    }, ['name'])
    
    pending_pos = frappe.db.get_list('Purchase Order', {
        'one_fm_request_for_purchase': doc_dict.get('name'),
        'docstatus': ['in', [0, 1]],
        'workflow_state': ['in', ['Pending Purchase Manager', 'Pending Finance Approver']]
    }, ['name', 'workflow_state'])
    
    if approved_pos:
        all_other_pos = draft_pos + pending_pos
        if all_other_pos:
            approved_list = ", ".join([po.name for po in approved_pos])
            other_list = ", ".join([po.name for po in all_other_pos])
            return {
                'error': True,
                'type': 'mixed',
                'title': 'Cancellation Blocked – Mixed Purchase Order Stages Found',
                'message': f"Please note that {doc_dict.get('name')} has related Purchase Orders in different stages: {other_list} > Pending Approval, {approved_list} > Approved. Cancellation of this RFP is not allowed while Approved POs exist. You must first cancel the Approved POs.",
                'approved_list': approved_list,
                'other_list': other_list
            }
        else:
            po_list = ", ".join([po.name for po in approved_pos])
            return {
                'error': True,
                'type': 'approved_only',
                'title': 'RFP Cancellation blocked. Approved Purchase Order found.',
                'message': f"Please note that {doc_dict.get('name')} has related Purchase Orders ({po_list}) in Approved stage. To proceed, you must first cancel these Purchase Orders. Cancellation of this RFP is not allowed until all related POs are cancelled.",
                'approved_list': po_list
            }
    elif draft_pos and pending_pos:
        all_draft_pending = draft_pos + pending_pos
        po_list = ", ".join([po.name for po in all_draft_pending])
        return {
            'error': True,
            'type': 'draft_pending_confirmation',
            'title': 'Purchase Order is in Pending Approval Stage',
            'message': f"Please note that {doc_dict.get('name')} has related Purchase Orders ({po_list}) currently in Pending Approval stage. Cancelling this RFP will automatically delete these Purchase Orders. Do you want to proceed?",
            'draft_pending_list': po_list
        }
    elif draft_pos:
        po_list = ", ".join([po.name for po in draft_pos])
        return {
            'error': True,
            'type': 'draft_confirmation',
            'title': 'Purchase Order is in Pending Approval Stage',
            'message': f"Please note that {doc_dict.get('name')} has related Purchase Orders ({po_list}) currently in Pending Approval stage. Cancelling this RFP will automatically delete these Purchase Orders. Do you want to proceed?",
            'draft_list': po_list
        }
    
    return {'error': False}


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
def refresh_dashboard_connections(rfp_name):
	"""
	Utility function to refresh dashboard connections for a Request for Purchase.
	This can help troubleshoot connection display issues.
	"""
	if not frappe.has_permission("Request for Purchase", "write", rfp_name):
		frappe.throw(_("No permission to modify this Request for Purchase"))
	
	# Clear any cached data that might be affecting the dashboard
	frappe.clear_cache(doctype="Request for Purchase")
	frappe.clear_document_cache("Request for Purchase", rfp_name)
	
	# Get current connections to verify they exist
	connections = get_purchase_order_connections(rfp_name)
	
	return {
		"message": f"Dashboard connections refreshed. Found {connections['total_count']} Purchase Orders.",
		"connections": connections
	}

@frappe.whitelist()
def get_purchase_order_connections(rfp_name):
	"""
	Debug function to check Purchase Order connections for a Request for Purchase.
	This helps troubleshoot dashboard connection issues.
	"""
	if not frappe.has_permission("Request for Purchase", "read", rfp_name):
		frappe.throw(_("No permission to access this Request for Purchase"))
	
	connections = frappe.db.get_all(
		"Purchase Order",
		filters={"one_fm_request_for_purchase": rfp_name},
		fields=["name", "supplier", "status", "workflow_state", "docstatus", "transaction_date"],
		order_by="transaction_date desc"
	)
	
	return {
		"total_count": len(connections),
		"connections": connections,
		"rfp_name": rfp_name
	}

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


def create_purchase_order(**args):
    args = frappe._dict(args)
    
    items_to_process = args.get('items_list', [args])
    valid_items = []
    
    for item_args in items_to_process:
        item_args = frappe._dict(item_args)
        
        rfp_item = frappe.db.get_value(
            "Request for Purchase Quotation Item",
            {
                "parent": args.request_for_purchase,
                "item_code": item_args.item_code
            },
            ["qty", "ordered_qty", "pending_qty"],
            as_dict=True
        )
        
        if not rfp_item:
            frappe.msgprint(f"Item {item_args.item_code} not found in Request for Purchase {args.request_for_purchase}")
            continue
        
        available_qty = rfp_item.pending_qty or (rfp_item.qty - (rfp_item.ordered_qty or 0))
        
        if available_qty <= 0:
            frappe.msgprint(f"No pending quantity available for item {item_args.item_code}. All quantities have been ordered.")
            continue
        
        po_qty = min(item_args.qty, available_qty)
        
        if po_qty <= 0:
            frappe.msgprint(f"Calculated quantity is zero for item {item_args.item_code}. Skipping.")
            continue
        
        if po_qty != item_args.qty:
            frappe.msgprint(f"Requested quantity {item_args.qty} reduced to available pending quantity {po_qty} for item {item_args.item_code}")
        
        valid_items.append({
            "item_code": item_args.item_code,
            "item_name": item_args.get("item_name") or frappe.db.get_value("Item", item_args.item_code, "item_name"),
            "description": item_args.description,
            "uom": item_args.uom,
            "qty": po_qty,
            "rate": item_args.rate,
            "amount": po_qty * item_args.rate,
            "schedule_date": getdate(item_args.delivery_date) if (item_args.delivery_date and getdate(nowdate()) < getdate(item_args.delivery_date)) else getdate(nowdate()),
            "expected_delivery_date": item_args.delivery_date
        })
    
    if not valid_items:
        return None
    
    po = frappe.new_doc("Purchase Order")
    po.transaction_date = nowdate()
    po.set_warehouse = args.warehouse
    po.quotation = args.quotation
    po.supplier = args.supplier
    po.is_subcontracted = args.is_subcontracted or "No"
    po.conversion_factor = args.conversion_factor or 1
    po.supplier_warehouse = args.supplier_warehouse or None
    po.one_fm_request_for_purchase = args.request_for_purchase
    po.request_for_material = frappe.db.get_value(
        "Request for Purchase",
        args.request_for_purchase,
        "request_for_material"
    )
    po.is_subcontracted = False

    for item in valid_items:
        po.append("items", item)
    
    if not args.do_not_save:
        po.save(ignore_permissions=True)
        if not args.do_not_submit:
            po.submit()
    
    return po