# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONEFM and contributors
# For license information, please see license.txt
import frappe

def set_payment_terms_template(doc, method):
    '''
        Method to set payment term template if no payment term template set
        and contracts having a payment terms template
    '''
    if not doc.payment_terms_template and doc.contracts:
        payment_terms_template = frappe.db.get_value('Contracts', doc.contracts, 'payment_terms_template')
        if payment_terms_template:
            doc.payment_terms_template = payment_terms_template
            doc.payment_schedule = []
            doc.set_payment_schedule()
