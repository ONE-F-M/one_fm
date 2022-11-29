# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
from frappe import _
import frappe
from frappe.model.document import Document
import os,datetime
from frappe.utils.file_manager import write_file
from frappe.utils import  get_files_path


def validate_leave_proof_document_requirement(doc, method):
    '''
        Function to validate Is Proof Document Required Flag in Leave Application
        Triger form Validate hook of Leave Application
    '''

    if doc.leave_type and doc.status in ['Open', 'Approved'] and not doc.is_new():
        doc.is_proof_document_required = frappe.db.get_value('Leave Type', doc.leave_type, 'is_proof_document_required')
        if doc.is_proof_document_required and not doc.proof_documents:
            frappe.throw(_("Proof Document Required for {} Leave Type".format(doc.leave_type)))

        for each in doc.proof_documents:
            if not each.attachments:
                frappe.throw(_("Proof Document Required for {} Leave Type in row {}".format(doc.leave_type,each.idx)))

