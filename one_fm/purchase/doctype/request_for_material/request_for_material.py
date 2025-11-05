# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from collections import defaultdict
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, get_url, get_fullname,cstr
from frappe import _
from frappe.utils import nowdate, cstr
from frappe.utils.user import get_users_with_role
from frappe.permissions import has_permission
from erpnext.controllers.buying_controller import BuyingController
from one_fm.purchase.doctype.item_reservation.item_reservation import get_item_balance
from one_fm.utils import get_approver_user
from one_fm.processor import sendemail
from one_fm.api.doc_events import get_employee_user_id
from one_fm.utils import get_users_with_role_permitted_to_doctype
from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError, remove as remove_assignment, close_all_assignments

class RequestforMaterial(BuyingController):
    @frappe.whitelist()
    def get_default_warehouse(self):
        return frappe.db.get_single_value('Stock Settings', 'default_warehouse')

    def notify_material_requester(self):
        page_link = get_url(self.get_url())
        message = "Request for Material <a href='{0}'>{1}</a> is {2} by {3}.".format(page_link, self.name, self.workflow_state, frappe.session.user)
        if self.workflow_state == 'Approved':
            message += "You will be notified of the expected delivery date as soon as the order is processed"
        subject = '{0} {1} your Request for Material {2}'.format(self.workflow_state, get_fullname(frappe.session.user), self.name)
        send_email(self, [self.requested_by], message, subject)
        create_notification_log(subject, message, [self.requested_by], self)

    def validate(self):
        if self.is_new():
            self.linked_purchase_rfm = None
            
        self.validate_details_against_type()
        self.set_request_for_material_accepter_and_approver()
        self.set_item_fields()
        self.set_title()
        self.validate_item_qty()
        # self.validate_item_reservation()
        self.validate_linked_request_quantities()

    def _initialize_custom_quantities(self):
            """
            Initializes the custom RFP and pending quantities for each item
            when the Request for Material is submitted.
            """
            for item in self.items:
                    item.custom_rfp_quantity = 0
                    item.custom_pending_quantity = item.qty

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
                if item.item_name:
                    item.requested_item_name = item.item_name
                if item.description:
                    item.requested_description = item.description

    def set_request_for_material_accepter_and_approver(self):
        if not self.request_for_material_approver:
            approver = False
            if self.type == 'Project' and self.project:
                approver = frappe.db.get_value('Project', self.project, 'account_manager')
                if not approver:
                    approver = frappe.db.get_single_value("Operation Settings", "default_operation_manager")
                    if approver:
                        self.request_for_material_approver = approver
                        return
            elif self.type in ['Individual', 'Department'] and self.employee:
                approver = frappe.db.get_value('Employee', self.employee, 'reports_to')
            elif self.type == 'Onboarding':
                employee = frappe.db.exists("Employee", {'user_id': self.owner})
                if employee:
                    approver = frappe.db.get_value('Employee', employee, 'reports_to')
            if approver:
                request_for_material_approver = get_employee_user_id(approver)
            else:
                request_for_material_approver = frappe.db.get_value('Purchase Settings', None, 'request_for_material_approver')
            if request_for_material_approver:
                self.request_for_material_approver = request_for_material_approver

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
        items = ', '.join([d.requested_item_name for d in self.items if d.requested_item_name][:3])
        self.title = _('Material Request for {0}').format(items)[:100]

    def before_cancel(self):
        if self.workflow_state == 'Rejected' and frappe.session.user == self.request_for_material_approver:
            self.notify_material_requester()

    def on_submit(self):
        self._initialize_custom_quantities()
        self.validate_item_qty()
        self.assign_for_technical_verification()
        if self.workflow_state == 'Approved' and frappe.session.user == self.request_for_material_approver:
            self.notify_material_requester()
            self.assign_to_warehouse_supervisor()
        if self.per_received == 100:
            close_all_assignments(self.doctype, self.name)

    def _get_total_rfp_quantity(self):
        return frappe.db.sql("""
            SELECT SUM(qty)
            FROM `tabRequest for Purchase Item`
            WHERE parent IN (
                SELECT name
                FROM `tabRequest for Purchase`
                WHERE request_for_material = %s AND docstatus = 1
            )
        """, self.name)[0][0] or 0

    def _get_total_ordered_quantity(self):
        return frappe.db.sql("""
            SELECT SUM(qty)
            FROM `tabPurchase Order Item`
            WHERE parent IN (
                SELECT name
                FROM `tabPurchase Order`
                WHERE request_for_material = %s AND docstatus = 1
            )
        """, self.name)[0][0] or 0

    def _get_total_received_quantity(self):
        return frappe.db.sql("""
            SELECT SUM(qty)
            FROM `tabPurchase Receipt Item`
            WHERE parent IN (
                SELECT name
                FROM `tabPurchase Receipt`
                WHERE custom_request_for_material = %s AND docstatus = 1
            )
        """, self.name)[0][0] or 0

    def update_purchase_rfm_status(self):
        if self.purpose != "Purchase":
            return

        total_rfm_qty = sum(item.qty for item in self.items)
        total_rfp_qty = self._get_total_rfp_quantity()
        total_ordered_qty = self._get_total_ordered_quantity()
        total_received_qty = self._get_total_received_quantity()

        new_status = ""

        if total_rfp_qty == 0 and total_ordered_qty == 0 and total_received_qty == 0:
            new_status = "Pending"
        elif total_rfp_qty > 0 and total_rfp_qty < total_rfm_qty:
            new_status = "Partial RFP"
        elif total_rfp_qty == total_rfm_qty:
            if total_ordered_qty == 0:
                new_status = "RFP Processed"
            elif total_ordered_qty > 0 and total_ordered_qty < total_rfp_qty:
                new_status = "Partially Ordered"
            elif total_ordered_qty == total_rfp_qty:
                if total_received_qty == 0:
                    new_status = "Ordered"
                elif total_received_qty > 0 and total_received_qty < total_ordered_qty:
                    new_status = "Partially Received"
                elif total_received_qty == total_ordered_qty:
                    new_status = "Completed"

        if new_status and self.status != new_status:
            self.db_set("status", new_status)

    def assign_to_warehouse_supervisor(self):
        try:
            filtered_users = get_users_with_role_permitted_to_doctype('Warehouse Supervisor', self.doctype)
            if filtered_users and len(filtered_users) > 0:
                add_assignment({
                    'doctype': self.doctype,
                    'name': self.name,
                    'assign_to': filtered_users,
                    'description': _('{0}: Request for Material by {1}'.format(self.workflow_state, get_fullname(self.request_for_material_approver)))
                })
                self.add_comment("Comment", _("Assign to Warehouse Supervisor {0} to process the request".format(filtered_users[0])))
            else:
                frappe.msgprint(_("Not able to find user with role Warehouse Supervisor to assign this RFM"), alert=True)
                self.add_comment("Comment", _("On Approval, not able to find user with role Warehouse Supervisor to assign this RFM"))
        except DuplicateToDoError:
            frappe.message_log.pop()
            pass

    def assign_for_technical_verification(self):
        if self.technical_verification_needed == 'Yes' and self.technical_verification_from and not self.technical_remarks:
            try:
                add_assignment({
                    'doctype': self.doctype,
                    'name': self.name,
                    'assign_to': [self.technical_verification_from],
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

    def validate_linked_request_quantities(self):
        """Validate that this RFM (a derived / purchase RFM) does not exceed the quantities
        of a linked source RFM (issue_transfer_rfm or first row's linked_request_for_material).

        Aggregation Rules:
        - Primary key: item_code when present.
        - Fallback key: requested_item_name (trimmed) when item_code is empty.
        - requested_item_name assumed unique when used as fallback.
        - Matching is strict (case sensitive) and whitespace trimmed on both sides for names.
        - Multiple rows with the same key in either doc are summed.
        - If a key exists here but not in source -> violation.
        - If summed qty here > summed qty in source -> violation.
        - Rows must have either item_code or requested_item_name (guaranteed by business rule).
        """
        linked_name = getattr(self, 'issue_transfer_rfm', None)
        if not linked_name:
            # fall back to first child row's linked_request_for_material if provided
            if not self.items:
                return
            linked_name = getattr(self.items[0], 'linked_request_for_material', None)
            if not linked_name:
                return
        if linked_name == self.name:
            frappe.throw(_("Linked Request for Material cannot reference itself."))

        if not frappe.db.exists('Request for Material', linked_name):
            frappe.throw(_("Linked Request for Material {0} does not exist.").format(frappe.bold(linked_name)))
        source_doc = frappe.get_doc('Request for Material', linked_name)

        # Ensure back-link recorded
        if getattr(source_doc, 'linked_purchase_rfm', None) != self.name:
            source_doc.db_set('linked_purchase_rfm', self.name)

        def build_key(it):
            if getattr(it, 'item_code', None):
                return ('code', it.item_code.strip())  # strip just in case
            # fallback to requested_item_name
            name_val = (getattr(it, 'requested_item_name', None) or '').strip()
            return ('name', name_val)

        def add_to(bucket, key_tuple, qty):
            # key_tuple = (type, value) so different namespaces for code vs name
            bucket[key_tuple] = bucket.get(key_tuple, 0) + flt(qty)

        source_totals = {}
        for it in source_doc.items:
            key_type, key_val = build_key(it)
            if not key_val:  # safety, should not happen per business rule
                frappe.throw(_("Source RFM {0} contains a row without Item Code and Item Name.").format(frappe.bold(linked_name)))
            add_to(source_totals, (key_type, key_val), it.qty)

        current_totals = {}
        for it in self.items:
            key_type, key_val = build_key(it)
            if not key_val:
                frappe.throw(_("Row {0}: missing Item Code and Item Name").format(it.idx))
            add_to(current_totals, (key_type, key_val), it.qty)

        violations = []
        for key, curr_qty in current_totals.items():
            key_type, key_val = key
            src_qty = source_totals.get(key)
            label = key_val  # display value
            if src_qty is None:
                violations.append(_("Item {0}: not present in linked RFM {1}. Current total {2}").format(
                    frappe.bold(label), frappe.bold(linked_name), frappe.bold(curr_qty)))
            elif curr_qty > src_qty:
                violations.append(_("Item {0}: current total {1} exceeds linked RFM total {2}").format(
                    frappe.bold(label), frappe.bold(curr_qty), frappe.bold(src_qty)))

        if violations:
            msg = _("Quantity validation against Linked Request for Material failed:<br>{0}").format('<br>'.join(violations))
            frappe.throw(msg)

    @frappe.whitelist()
    def get_session_user_approver(self):
        return get_approver_user(frappe.db.get_value('Employee', {'user_id': frappe.session.user}))

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
    try:
        sendemail(
            recipients= recipients,
            subject=subject,
            message=message,
            reference_doctype=doc.doctype,
            reference_name=doc.name
        )
    except frappe.OutgoingEmailError:
        doc.log_error(_("Failed to send notification email"))

def create_notification_log(subject, message, for_users, reference_doc):
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
        target.purpose = 'Material Issue' if source.type == 'Individual' else 'Material Transfer'
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
def create_partial_request_for_purchase(source_name, items):
    """
    Creates a Request for Purchase for a subset of items from a Request for Material.
    :param source_name: The name of the source Request for Material.
    :param items: A list of dicts of items to include in the RFP.
    """
    if isinstance(items, str):
        items = json.loads(items)

    source_doc = frappe.get_doc("Request for Material", source_name)

    rfp = frappe.new_doc("Request for Purchase")
    rfp.company = source_doc.company
    rfp.request_for_material = source_name
    rfp.warehouse = source_doc.t_warehouse

    for item_data in items:
        source_item_doc = frappe.get_doc("Request for Material Item", item_data.get('request_for_material_item'))
        rfp.append("items", {
            "item_code": item_data.get('item_code'),
            "qty": item_data.get('qty'),
            "item_name": source_item_doc.item_name,
            "description": source_item_doc.requested_description,
            "uom": source_item_doc.uom,
            "schedule_date": source_item_doc.schedule_date,
            "request_for_material": source_name,
            "request_for_material_item": item_data.get('request_for_material_item'),
            "custom_request_for_material_item": item_data.get('request_for_material_item')
        })

    rfp.insert(ignore_permissions=True)
    
    return rfp

@frappe.whitelist()
def make_request_for_purchase(source_name, target_doc=None):
    
    def set_missing_values(source, target):
        if not target.get("items"):
            frappe.throw(_("Cannot create RFP. At least one line item must have a specified Item Code."))
        target.run_method('_update_linked_rfm_quantities')
        
        
    def update_item(obj, target, source_parent):
        if obj.custom_pending_quantity > 0:
            qty = obj.qty - obj.custom_rfp_quantity
            target.qty = qty
            target.custom_request_for_material_item = obj.name

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
                ["name", "custom_request_for_material_item"],
                ["parent", "request_for_material"]
            ],
            "postprocess": update_item,
            "condition": lambda doc: (doc.item_code and doc.custom_rfp_quantity < doc.qty and doc.reject_item==0)
        }
    }, target_doc, set_missing_values)
    doclist.save()
    frappe.db.commit()
    
    return doclist

@frappe.whitelist()
def create_stock_entry_from_rfm(rfm_name, stock_entry_type):
    rfm = frappe.get_doc("Request for Material", rfm_name)
    
    if stock_entry_type == "Material Issue" and rfm.purpose != "Issue":
        frappe.throw(_("RFM Purpose must be Issue for Material Issue"))
    
    if stock_entry_type in ["Material Transfer", "Material Transfer-In Transit"] and rfm.purpose != "Transfer":
        frappe.throw(_("RFM Purpose must be Transfer for Material Transfer"))
    
    if rfm.docstatus != 1:
        frappe.throw(_("RFM must be approved (submitted)"))
    
    non_uniform_items = [item for item in rfm.items if not item.is_uniform_request]
    
    if not non_uniform_items:
        frappe.throw(_("No items found to create Stock Entry. All items in this RFM are uniform requests."))
    
    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.company = rfm.company
    stock_entry.posting_date = nowdate()
    stock_entry.one_fm_request_for_material = rfm_name
    
    if rfm.purpose == "Transfer":
        stock_entry.stock_entry_type = "Material Transfer"
        if stock_entry_type == "Material Transfer-In Transit":
            stock_entry.add_to_transit = 1
            
    elif rfm.purpose == "Issue":
        stock_entry.stock_entry_type = "Material Issue"

    for item in rfm.items:
        if item.is_uniform_request:
            continue
        
        if rfm.purpose == "Issue":
            stock_entry.append("items", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "description": item.description,
                "qty": item.qty,
                "s_warehouse": item.warehouse,
                "uom": item.uom,
                "stock_uom": item.stock_uom,
                "conversion_factor": item.conversion_factor or 1
            })
        else:
            stock_entry.append("items", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "description": item.description,
                "qty": item.qty,
                "s_warehouse": item.warehouse,
                "t_warehouse": item.t_warehouse,
                "uom": item.uom,
                "stock_uom": item.stock_uom,
                "conversion_factor": item.conversion_factor or 1
            })

    
    stock_entry.insert()
    
    frappe.msgprint(_("Stock Entry {0} created successfully").format(stock_entry.name))
    
    return stock_entry.name

def update_rfm_status_against_rfp(doc, method):
    if hasattr(doc, 'request_for_material') and doc.request_for_material:
        rfm = frappe.get_doc("Request for Material", doc.request_for_material)
        rfm.update_purchase_rfm_status()

def update_rfm_status_against_purchase_order(doc, method):
    if hasattr(doc, 'request_for_material') and doc.request_for_material:
        rfm = frappe.get_doc("Request for Material", doc.request_for_material)
        rfm.update_purchase_rfm_status()

def update_rfm_status_against_purchase_receipt(doc, method):
    if hasattr(doc, 'custom_request_for_material') and doc.custom_request_for_material:
        rfm = frappe.get_doc("Request for Material", doc.custom_request_for_material)
        rfm.update_purchase_rfm_status()


@frappe.whitelist()
def has_pending_uniform_items(rfm_name: str):
    rfm = frappe.get_doc("Request for Material", rfm_name)
    
    uniform_items = [
        item for item in rfm.items 
        if item.is_uniform_request and item.employee
    ]
    
    if not uniform_items:
        return False
    
    for item in uniform_items:
        if not item.linked_employee_uniform:
            return True
        
        employee_uniform = frappe.get_doc("Employee Uniform", item.linked_employee_uniform)
        
        if not employee_uniform.stock_entry:
            return True
    
    return False


@frappe.whitelist()
def create_employee_uniform(rfm_name: str):
    rfm = frappe.get_doc("Request for Material", rfm_name)
    
    uniform_items = [
        item for item in rfm.items 
        if item.is_uniform_request and item.employee
    ]
    
    if not uniform_items:
        frappe.throw(_("No uniform request items found with assigned employees in this RFM."))
    
    already_linked = [
        item for item in uniform_items 
        if item.linked_employee_uniform
    ]
    
    if already_linked:
        frappe.throw(
            _("Some items are already linked to Employee Uniform documents. Employee Uniform can only be created once per RFM item.")
        )
    
    employee_warehouse_groups = defaultdict(lambda: defaultdict(list))
    for item in uniform_items:
        if not item.warehouse:
            frappe.throw(_("Row {0}: No warehouse specified for item {1}").format(item.idx, item.item_code or item.requested_item_name))
        employee_warehouse_groups[item.employee][item.warehouse].append(item)
    
    created_uniforms = []
    
    for employee, warehouse_groups in employee_warehouse_groups.items():
        for warehouse, items in warehouse_groups.items():
            try:
                employee_uniform = frappe.new_doc("Employee Uniform")

                employee_uniform.naming_series = "EUI-.YYYY.-" 
                employee_uniform.type = "Issue"
                employee_uniform.employee = employee
                employee_uniform.warehouse = warehouse
                employee_uniform.issued_on = frappe.utils.today()
                employee_uniform.linked_rfm = rfm_name
                
                total_qty = 0
                for rfm_item in items:
                    uniform_item = employee_uniform.append("uniforms", {})
                    uniform_item.item = rfm_item.item_code
                    uniform_item.item_name = rfm_item.requested_item_name or rfm_item.item_name
                    uniform_item.quantity = float(rfm_item.qty)
                    uniform_item.uom = rfm_item.uom
                    uniform_item.issued_on = frappe.utils.today()
                    uniform_item.linked_rfm = rfm_name
                    uniform_item.linked_rfm_reference = rfm_item.name
                    
                    total_qty += uniform_item.quantity
                
                employee_uniform.total_quantity = total_qty
                
                employee_uniform.insert(ignore_permissions=True)
                
                frappe.db.set_value(
                    "Employee Uniform",
                    employee_uniform.name,
                    "workflow_state",
                    "To be Issued",
                    update_modified=False
                )
                
                for rfm_item in items:
                    frappe.db.set_value(
                        "Request for Material Item",
                        rfm_item.name,
                        "linked_employee_uniform",
                        employee_uniform.name,
                        update_modified=False
                    )
                
                created_uniforms.append({
                    "name": employee_uniform.name,
                    "employee": employee,
                    "employee_name": employee_uniform.employee_name,
                    "warehouse": warehouse,
                    "total_items": len(items),
                    "total_quantity": total_qty
                })
                
                frappe.msgprint(
                    _("Employee Uniform {0} created for {1} from warehouse {2}").format(
                        frappe.bold(employee_uniform.name),
                        frappe.bold(employee_uniform.employee_name),
                        frappe.bold(warehouse)
                    )
                )
                
            except Exception as e:
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=f"Error creating Employee Uniform for {employee} - {warehouse}"
                )
                frappe.throw(
                    _("Error creating Employee Uniform for employee {0} from warehouse {1}: {2}").format(employee, warehouse, str(e))
                )
    
    frappe.db.commit()
    
    return {
        "success": True,
        "message": _("{0} Employee Uniform document(s) created successfully").format(len(created_uniforms)),
        "created_uniforms": created_uniforms
    }