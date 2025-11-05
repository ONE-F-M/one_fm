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
from one_fm.utils import get_users_with_role_permitted_to_doctype

class RequestforPurchase(Document):
	def onload(self):
		self.set_onload('exists_qfs', False)
		if frappe.db.get_value('Quotation From Supplier', {'request_for_purchase': self.name}, 'name'):
			self.set_onload('exists_qfs', True)

	def on_submit(self):
		self._update_linked_rfm_quantities()
		update_rfp_status(self.name)
  
	def on_update_after_submit(self):
		self._update_linked_rfm_quantities()
		update_rfp_status(self.name)
  
	def after_insert(self):
		self._update_linked_rfm_quantities()
  
	def on_update(self):
		self._update_linked_rfm_quantities()
  
	def on_trash(self):
		self._update_linked_rfm_quantities(delete_event=True)
  
	def on_cancel(self):
		self._update_linked_rfm_quantities(delete_event=True)

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
					rfp_doc = self.as_dict(),
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

 
 
	def update_purchase_order(self, item_qty_dict):
		"""
		Update all draft Purchase Orders linked to this RFP so that:
		- Quantities are reduced as per item_qty_dict (never increased)
		- If a PO has no items left, it is deleted
		- Items in the dict not present in any PO are ignored (never added)
		"""
		if not item_qty_dict:
			return
		draft_pos = frappe.get_all(
			"Purchase Order",
			filters={
				"one_fm_request_for_purchase": self.name,
				"docstatus": 0
			},
			fields=["name"]
		)
		
		item_po_map = {}
		po_docs = {}
		for po_row in draft_pos:
			po = frappe.get_doc("Purchase Order", po_row.name)
			po_docs[po.name] = po
			for item in list(po.items):
				# Remove items not in the dict
				if item.item_code not in item_qty_dict:
					po.items.remove(item)
					continue
				if item.item_code not in item_po_map:
					item_po_map[item.item_code] = []
				item_po_map[item.item_code].append((po, item))
		# For each item_code in the dict, reduce qty across POs (never increase, never add new rows)
		for item_code, new_total_qty in item_qty_dict.items():
			ordered_quantity = self.get_ordered_qty_for_item(item_code)
			new_total_qty = max(0, new_total_qty - ordered_quantity)
			po_items = item_po_map.get(item_code, [])
			po_items.sort(key=lambda x: x[0].name)
			current_total = sum(i.qty for _, i in po_items)
			# Only reduce if needed
			if new_total_qty < current_total:
				qty_left = new_total_qty
				for po, item in po_items:
					if qty_left <= 0:
						po.items.remove(item)
					elif item.qty > qty_left:
						item.qty = qty_left
						qty_left = 0
					else:
						qty_left -= item.qty
			# If new_total_qty >= current_total, do nothing (never increase or add)
		# Remove any POs with no items
		for po in po_docs.values():
			if not po.items:
				po.delete()
			else:
				po.save(ignore_permissions=True)
		
		# Fetch all valid purchase orders linked to this Request for Purchase
		
		
	def get_ordered_qty_for_item(self, item_code):
		# Calculate the total ordered quantity for the given item_code across all submitted POs
		ordered_qty = frappe.db.get_value(
			"Purchase Order Item",
			{
				"item_code": item_code,
				"parent": ["in", [po for po in frappe.db.get_list("Purchase Order", {"one_fm_request_for_purchase": self.name, "docstatus": 1}, pluck="name")]]
			},
			"sum(qty)"
		) or 0
		return ordered_qty
		
    
	@frappe.whitelist()
	def update_rfp_items(self, updated_items, reason):
		updated_item_names = {}
		removed_item_names = {}
		

		updated_items_data = json.loads(updated_items)
		updated_items_map = {item['name']: item for item in updated_items_data}

		# Validation and Update Phase
		items_to_remove = []
		for item in self.items_to_order:
			if item.name in updated_items_map:
				new_qty = frappe.utils.flt(updated_items_map[item.name]['qty'])

				

				ordered_qty = self.get_ordered_qty_for_item(item.item_code)
				if new_qty < ordered_qty:
					frappe.throw(_("New quantity for item {0} cannot be less than the already ordered quantity ({1}).").format(item.item_code, ordered_qty))

				# item.db_set('qty',new_qty)
				item.qty = new_qty
				updated_item_names[item.item_code] = new_qty
				#Update the same quantity in the main items table
				for main_item in self.items:
					if main_item.item_code == item.item_code:
						# main_item.db_set('qty',new_qty)
						main_item.qty = new_qty
						break
			else:
				# Item is being removed
				ordered_qty = self.get_ordered_qty_for_item(item.item_code)
				if ordered_qty > 0:
					frappe.throw(_("Cannot remove item {0} as it has already been ordered.").format(item.item_code))
				items_to_remove.append(item)
				removed_item_names[item.item_code] = item.qty

		for item in items_to_remove:
			self.remove(item)
			# Also remove from main items table
			for main_item in self.items:
				if main_item.item_code == item.item_code:
					self.remove(main_item)
					break

		# Propagate changes to draft POs
		#return the names and quantity of the updated and removed items as a string
		
		reason = "Reason for Item Update: " + reason
		self.add_comment("Comment", reason)
		self.save()
		version = frappe.new_doc("Version")
		if version.update_version_info(self.get_doc_before_save(), self):
			version.insert(ignore_permissions=True)
		self.update_purchase_order(updated_item_names)
		
		frappe.msgprint(_("Request for Purchase updated successfully."))

	def before_save(self):
		# Ensure latest exchange rate before saving (only at before_save)
		self.get_and_set_latest_exchange_rate()

	def get_and_set_latest_exchange_rate(self):
		"""Fetch latest (by date desc then creation desc) Currency Exchange and overwrite exchange_rate.
		Rules:
		- If company_currency == currency => exchange_rate = 1
		- Else query Currency Exchange where date <= today
		- If record found overwrite; if none found keep existing
		- On error log and keep existing
		"""
		try:
			from_currency = getattr(self, 'company_currency', None)
			to_currency = getattr(self, 'currency', None)
			if not from_currency or not to_currency:
				return
			if from_currency == to_currency:
				self.exchange_rate = 1
				return
			latest = frappe.get_list(
				'Currency Exchange',
				filters={
					'from_currency': from_currency,
					'to_currency': to_currency,
					'date': ['<=', frappe.utils.today()]
				},
				fields=['name', 'exchange_rate', 'date', 'creation'],
				order_by='date desc, creation desc',
				page_length=1
			)
			if latest:
				rate = latest[0].get('exchange_rate')
				if rate:  # guaranteed non-zero/non-negative by business rules
					self.exchange_rate = rate
		except Exception as e:
			frappe.log_error(f"Exchange rate fetch failed for RFP {getattr(self, 'name', 'NEW')}: {e}", 'RFP Exchange Rate Fetch')

def update_rfp_status(rfp_name):
	"""
	Updates the status of a Request for Purchase (RFP) based on the
	quantities of items ordered in linked Purchase Orders (POs).

	Args:
		rfp_name (str): The name of the Request for Purchase document.
	"""
	rfp = frappe.get_doc("Request for Purchase", rfp_name)

	# Only update the status if the RFP is in an approved state
	if rfp.workflow_state != "Approved":
		return

	# Calculate the total quantity required by the RFP
	total_required_qty = sum(item.qty for item in rfp.items)

	# Calculate the total quantity ordered across all submitted POs
	ordered_qty = frappe.db.sql("""
		SELECT SUM(item.qty)
		FROM `tabPurchase Order Item` item
		JOIN `tabPurchase Order` po ON item.parent = po.name
		WHERE po.one_fm_request_for_purchase = %s
		AND po.docstatus = 1
	""", rfp_name)[0][0] or 0

	# Determine the new status based on the quantities
	new_status = None
	if ordered_qty == 0:
		new_status = "To Order"
	elif ordered_qty < total_required_qty:
		new_status = "Partially Ordered"
	else:
		new_status = "Ordered"

	# Update the RFP status if it has changed
	if rfp.status != new_status:
		rfp.db_set("status", new_status)
		frappe.db.commit()


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
    po.buying_price_list = args.get('rfp_doc').price_list
    po.currency = args.get('rfp_doc').currency
    po.conversion_rate = args.get('rfp_doc').exchange_rate
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