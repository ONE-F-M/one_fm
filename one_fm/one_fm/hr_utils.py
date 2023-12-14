# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
from frappe import _,scrub
from functools import reduce
import frappe
from frappe.model.document import Document
from erpnext.accounts.doctype.bank_account.bank_account import get_party_bank_account
import os,datetime
from frappe.utils.file_manager import write_file
from frappe.utils import  get_files_path,flt,nowdate
from erpnext.accounts.doctype.payment_entry.payment_entry import set_party_account_currency,set_party_type, \
    set_party_account,set_payment_type,set_grand_total_and_outstanding_amount,get_bank_cash_account,set_paid_amount_and_received_amount, \
    apply_early_payment_discount,get_reference_as_per_payment_terms,update_accounting_dimensions


@frappe.whitelist()
def create_invoice_payment_entry(
        dt, dn, party_amount=None, bank_account=None, bank_amount=None, party_type=None, payment_type=None
):
    """_summary_

    Args:
        dt (str): a valid doctype
        dn (str): a valid doctype

    """
    reference_doc = None
    doc = frappe.get_doc(dt, dn)

    # if doc.employee_advance:
    if dt in ("Sales Order", "Purchase Order") and flt(doc.per_billed, 2) >= 99.99:
        frappe.throw(_("Can only make payment against unbilled {0}").format(dt))

    if not party_type:
        party_type = set_party_type(dt)

    party_account = set_party_account(dt, dn, doc, party_type)
    party_account_currency = set_party_account_currency(dt, party_account, doc)

    if not payment_type:
        payment_type = set_payment_type(dt, doc)

    grand_total, outstanding_amount = set_grand_total_and_outstanding_amount(
        party_amount, dt, party_account_currency, doc
    )

    # bank or cash
    bank = get_bank_cash_account(doc, bank_account)

    paid_amount, received_amount = set_paid_amount_and_received_amount(
        dt, party_account_currency, bank, outstanding_amount, payment_type, bank_amount, doc
    )

    paid_amount, received_amount, discount_amount = apply_early_payment_discount(
        paid_amount, received_amount, doc
    )

    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = payment_type
    pe.company = doc.company
    pe.cost_center = doc.get("cost_center")
    pe.posting_date = nowdate()
    pe.mode_of_payment = doc.get("mode_of_payment")
    pe.party_type = party_type
    pe.party = doc.get(scrub(party_type))
    pe.contact_person = doc.get("contact_person")
    pe.contact_email = doc.get("contact_email")
    pe.ensure_supplier_is_not_blocked()
    pe.paid_from = party_account if payment_type == "Receive" else bank.account
    pe.paid_to = party_account if payment_type == "Pay" else bank.account
    pe.paid_from_account_currency = (
        party_account_currency if payment_type == "Receive" else bank.account_currency
    )
    pe.paid_to_account_currency = (
        party_account_currency if payment_type == "Pay" else bank.account_currency
    )
    pe.paid_amount = paid_amount
    pe.received_amount = received_amount
    pe.letter_head = doc.get("letter_head")
    if doc.get('employee_advance'):
        try:
            advance_account = frappe.get_value("Employee Advance",doc.employee_advance,'advance_account')
            pe.paid_from = advance_account
        except:
            frappe.log_error("An Error Occurred while creating the payment entry",frappe.get_traceback())

    if dt in ["Purchase Order", "Sales Order", "Sales Invoice", "Purchase Invoice"]:
        pe.project = doc.get("project") or reduce(
            lambda prev, cur: prev or cur, [x.get("project") for x in doc.get("items")], None
        )  # get first non-empty project from items

    if pe.party_type in ["Customer", "Supplier"]:
        bank_account = get_party_bank_account(pe.party_type, pe.party)
        pe.set("bank_account", bank_account)
        pe.set_bank_account_data()

    # only Purchase Invoice can be blocked individually
    if doc.doctype == "Purchase Invoice" and doc.invoice_is_blocked():
        frappe.msgprint(_("{0} is on hold till {1}").format(doc.name, doc.release_date))
    else:
        if doc.doctype in ("Sales Invoice", "Purchase Invoice") and frappe.get_value(
                "Payment Terms Template",
                {"name": doc.payment_terms_template},
                "allocate_payment_based_on_payment_terms",
        ):

            for reference in get_reference_as_per_payment_terms(
                    doc.payment_schedule, dt, dn, doc, grand_total, outstanding_amount
            ):
                pe.append("references", reference)
        else:
            if dt == "Dunning":
                pe.append(
                    "references",
                    {
                        "reference_doctype": "Sales Invoice",
                        "reference_name": doc.get("sales_invoice"),
                        "bill_no": doc.get("bill_no"),
                        "due_date": doc.get("due_date"),
                        "total_amount": doc.get("outstanding_amount"),
                        "outstanding_amount": doc.get("outstanding_amount"),
                        "allocated_amount": doc.get("outstanding_amount"),
                    },
                )
                pe.append(
                    "references",
                    {
                        "reference_doctype": dt,
                        "reference_name": dn,
                        "bill_no": doc.get("bill_no"),
                        "due_date": doc.get("due_date"),
                        "total_amount": doc.get("dunning_amount"),
                        "outstanding_amount": doc.get("dunning_amount"),
                        "allocated_amount": doc.get("dunning_amount"),
                    },
                )
            else:
                pe.append(
                    "references",
                    {
                        "reference_doctype": dt,
                        "reference_name": dn,
                        "bill_no": doc.get("bill_no"),
                        "due_date": doc.get("due_date"),
                        "total_amount": grand_total,
                        "outstanding_amount": outstanding_amount,
                        "allocated_amount": outstanding_amount,
                    },
                )

    pe.setup_party_account_field()
    pe.set_missing_values()

    update_accounting_dimensions(pe, doc)

    if party_account and bank:
        pe.set_exchange_rate(ref_doc=reference_doc)
        pe.set_amounts()
        if discount_amount:
            pe.set_gain_or_loss(
                account_details={
                    "account": frappe.get_cached_value("Company", pe.company, "default_discount_account"),
                    "cost_center": pe.cost_center
                                   or frappe.get_cached_value("Company", pe.company, "cost_center"),
                    "amount": discount_amount * (-1 if payment_type == "Pay" else 1),
                }
            )
            pe.set_difference_amount()

    return pe

def validate_leave_proof_document_requirement(doc, method):
    '''
        Function to validate Is Proof Document Required Flag in Leave Application
        Triger form Validate hook of Leave Application
    '''
    check_status = frappe.db.get_value("Employee", doc.employee, "is_in_kuwait")
    if check_status:
        if doc.leave_type and doc.status in ['Open', 'Approved'] and not doc.is_new():
            doc.is_proof_document_required = frappe.db.get_value('Leave Type', doc.leave_type, 'is_proof_document_required')
            if doc.is_proof_document_required and not doc.proof_documents:
                frappe.throw(_("Proof Document Required for {} Leave Type".format(doc.leave_type)))
                

            for each in doc.proof_documents:
                if not each.attachments:
                    frappe.throw(_("Proof Document Required for {} Leave Type in row {}".format(doc.leave_type,each.idx)))
    else:
        doc.is_proof_document_required = 0

