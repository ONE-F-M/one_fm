# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
from frappe import _
import frappe
from frappe.model.document import Document

def validate_leave_proof_document_requirement(doc, method):
    '''
        Function to validate Is Proof Document Required Flag in Leave Application
        Triger form Validate hook of Leave Application
    '''

    if doc.leave_type and doc.status in ['Open', 'Approved']:
        doc.is_proof_document_required = frappe.db.get_value('Leave Type', doc.leave_type, 'is_proof_document_required')
        if doc.is_proof_document_required and not doc.proof_document:
            frappe.throw(_("Proof Document Required for {0} Leave Type.!".format(doc.leave_type)))