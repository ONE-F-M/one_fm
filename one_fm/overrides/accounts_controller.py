import frappe,json
from frappe import _,throw
from erpnext.controllers.accounts_controller import set_order_defaults,validate_and_delete_children
from frappe.model.workflow import get_workflow_name, is_transition_condition_satisfied
from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
from erpnext.buying.utils import update_last_purchase_rate
from frappe.utils import (
    add_days,
    add_months,
    cint,
    flt,
    fmt_money,
    formatdate,
    get_last_day,
    get_link_to_form,
    getdate,
    nowdate,
    today,
)
from erpnext.stock.get_item_details import (
    
    get_conversion_factor,
    
)

@frappe.whitelist()
def update_child_qty_rate(parent_doctype, trans_items, parent_doctype_name, child_docname="items"):
    def check_doc_permissions(doc, perm_type="create"):
        try:
            doc.check_permission(perm_type)
        except frappe.PermissionError:
            actions = {"create": "add", "write": "update"}

            frappe.throw(
                _("You do not have permissions to {} items in a {}.").format(
                    actions[perm_type], parent_doctype
                ),
                title=_("Insufficient Permissions"),
            )

    def validate_workflow_conditions(doc):
        workflow = get_workflow_name(doc.doctype)
        if not workflow:
            return

        workflow_doc = frappe.get_doc("Workflow", workflow)
        current_state = doc.get(workflow_doc.workflow_state_field)
        roles = frappe.get_roles()

        transitions = []
        for transition in workflow_doc.transitions:
            if transition.next_state == current_state and transition.allowed in roles:
                if not is_transition_condition_satisfied(transition, doc):
                    continue
                transitions.append(transition.as_dict())

        if not transitions:
            frappe.throw(
                _("You are not allowed to update as per the conditions set in {} Workflow.").format(
                    get_link_to_form("Workflow", workflow)
                ),
                title=_("Insufficient Permissions"),
            )

    def get_new_child_item(item_row):
        child_doctype = "Sales Order Item" if parent_doctype == "Sales Order" else "Purchase Order Item"
        return set_order_defaults(
            parent_doctype, parent_doctype_name, child_doctype, child_docname, item_row
        )

    def validate_quantity(child_item, new_data):
        if not flt(new_data.get("qty")):
            frappe.throw(
                _("Row # {0}: Quantity for Item {1} cannot be zero").format(
                    new_data.get("idx"), frappe.bold(new_data.get("item_code"))
                ),
                title=_("Invalid Qty"),
            )

        if parent_doctype == "Sales Order" and flt(new_data.get("qty")) < flt(child_item.delivered_qty):
            frappe.throw(_("Cannot set quantity less than delivered quantity"))

        if parent_doctype == "Purchase Order" and flt(new_data.get("qty")) < flt(
            child_item.received_qty
        ):
            frappe.throw(_("Cannot set quantity less than received quantity"))

    def should_update_supplied_items(doc) -> bool:
        """Subcontracted PO can allow following changes *after submit*:

        1. Change rate of subcontracting - regardless of other changes.
        2. Change qty and/or add new items and/or remove items
                Exception: Transfer/Consumption is already made, qty change not allowed.
        """

        supplied_items_processed = any(
            item.supplied_qty or item.consumed_qty or item.returned_qty for item in doc.supplied_items
        )

        update_supplied_items = (
            any_qty_changed or items_added_or_removed or any_conversion_factor_changed
        )
        if update_supplied_items and supplied_items_processed:
            frappe.throw(_("Item qty can not be updated as raw materials are already processed."))

        return update_supplied_items

    data = json.loads(trans_items)

    any_qty_changed = False  # updated to true if any item's qty changes
    items_added_or_removed = False  # updated to true if any new item is added or removed
    any_conversion_factor_changed = False

    sales_doctypes = ["Sales Order", "Sales Invoice", "Delivery Note", "Quotation"]
    parent = frappe.get_doc(parent_doctype, parent_doctype_name)

    check_doc_permissions(parent, "write")
    _removed_items = validate_and_delete_children(parent, data)
    items_added_or_removed |= _removed_items

    for d in data:
        new_child_flag = False

        if not d.get("item_code"):
            # ignore empty rows
            continue

        if not d.get("docname"):
            new_child_flag = True
            items_added_or_removed = True
            check_doc_permissions(parent, "create")
            child_item = get_new_child_item(d)
        else:
            check_doc_permissions(parent, "write")
            child_item = frappe.get_doc(parent_doctype + " Item", d.get("docname"))

            prev_rate, new_rate = flt(child_item.get("rate")), flt(d.get("rate"))
            prev_qty, new_qty = flt(child_item.get("qty")), flt(d.get("qty"))
            prev_con_fac, new_con_fac = flt(child_item.get("conversion_factor")), flt(
                d.get("conversion_factor")
            )
            prev_uom, new_uom = child_item.get("uom"), d.get("uom")

            if parent_doctype == "Sales Order":
                prev_date, new_date = child_item.get("delivery_date"), d.get("delivery_date")
            elif parent_doctype == "Purchase Order":
                prev_date, new_date = child_item.get("schedule_date"), d.get("schedule_date")

            rate_unchanged = prev_rate == new_rate
            qty_unchanged = prev_qty == new_qty
            uom_unchanged = prev_uom == new_uom
            conversion_factor_unchanged = prev_con_fac == new_con_fac
            any_conversion_factor_changed |= not conversion_factor_unchanged
            date_unchanged = (
                prev_date == getdate(new_date) if prev_date and new_date else False
            )  # in case of delivery note etc
            if (
                rate_unchanged
                and qty_unchanged
                and conversion_factor_unchanged
                and uom_unchanged
                and date_unchanged
            ):
                continue

        validate_quantity(child_item, d)
        if flt(child_item.get("qty")) != flt(d.get("qty")):
            any_qty_changed = True

        child_item.qty = flt(d.get("qty"))
        rate_precision = child_item.precision("rate") or 2
        conv_fac_precision = child_item.precision("conversion_factor") or 2
        qty_precision = child_item.precision("qty") or 2

        if flt(child_item.billed_amt, rate_precision) > flt(
            flt(d.get("rate"), rate_precision) * flt(d.get("qty"), qty_precision), rate_precision
        ):
            frappe.throw(
                _("Row #{0}: Cannot set Rate if amount is greater than billed amount for Item {1}.").format(
                    child_item.idx, child_item.item_code
                )
            )
        else:
            child_item.rate = flt(d.get("rate"), rate_precision)

        if d.get("conversion_factor"):
            if child_item.stock_uom == child_item.uom:
                child_item.conversion_factor = 1
            else:
                child_item.conversion_factor = flt(d.get("conversion_factor"), conv_fac_precision)

        if d.get("uom"):
            child_item.uom = d.get("uom")
            conversion_factor = flt(
                get_conversion_factor(child_item.item_code, child_item.uom).get("conversion_factor")
            )
            child_item.conversion_factor = (
                flt(d.get("conversion_factor"), conv_fac_precision) or conversion_factor
            )

        if d.get("delivery_date") and parent_doctype == "Sales Order":
            child_item.delivery_date = d.get("delivery_date")

        if d.get("schedule_date") and parent_doctype == "Purchase Order":
            child_item.schedule_date = d.get("schedule_date")

        if flt(child_item.price_list_rate):
            if flt(child_item.rate) > flt(child_item.price_list_rate):
                #  if rate is greater than price_list_rate, set margin
                #  or set discount
                child_item.discount_percentage = 0

                if parent_doctype in sales_doctypes:
                    child_item.margin_type = "Amount"
                    child_item.margin_rate_or_amount = flt(
                        child_item.rate - child_item.price_list_rate, child_item.precision("margin_rate_or_amount")
                    )
                    child_item.rate_with_margin = child_item.rate
            else:
                child_item.discount_percentage = flt(
                    (1 - flt(child_item.rate) / flt(child_item.price_list_rate)) * 100.0,
                    child_item.precision("discount_percentage"),
                )
                child_item.discount_amount = flt(child_item.price_list_rate) - flt(child_item.rate)

                if parent_doctype in sales_doctypes:
                    child_item.margin_type = ""
                    child_item.margin_rate_or_amount = 0
                    child_item.rate_with_margin = 0

        child_item.flags.ignore_validate_update_after_submit = True
        if new_child_flag:
            child_item.amount = child_item.base_rate*child_item.qty
            parent.load_from_db()
            child_item.idx = len(parent.items) + 1
            child_item.insert()
        else:
            child_item.amount = child_item.base_rate*child_item.qty
            child_item.save()

    parent.reload()
    parent.flags.ignore_validate_update_after_submit = True
    parent.set_qty_as_per_stock_uom()
    parent.calculate_taxes_and_totals()
    parent.set_total_in_words()
    if parent_doctype == "Sales Order":
        make_packing_list(parent)
        parent.set_gross_profit()
    frappe.get_doc("Authorization Control").validate_approving_authority(
        parent.doctype, parent.company, parent.base_grand_total
    )

    parent.set_payment_schedule()
    if parent_doctype == "Purchase Order":
        parent.validate_minimum_order_qty()
        parent.validate_budget()
        if parent.is_against_so():
            parent.update_status_updater()
    else:
        parent.check_credit_limit()

    # reset index of child table
    for idx, row in enumerate(parent.get(child_docname), start=1):
        row.idx = idx

    parent.save()

    if parent_doctype == "Purchase Order":
        update_last_purchase_rate(parent, is_submit=1)
        parent.update_prevdoc_status()
        parent.update_requested_qty()
        parent.update_ordered_qty()
        parent.update_ordered_and_reserved_qty()
        parent.update_receiving_percentage()
        if parent.is_old_subcontracting_flow:
            if should_update_supplied_items(parent):
                parent.update_reserved_qty_for_subcontract()
                parent.create_raw_materials_supplied()
            parent.save()
    else:  # Sales Order
        parent.validate_warehouse()
        parent.update_reserved_qty()
        parent.update_project()
        parent.update_prevdoc_status("submit")
        parent.update_delivery_status()

    parent.reload()
    validate_workflow_conditions(parent)

    parent.update_blanket_order()
    parent.update_billing_percentage()
    parent.set_status()