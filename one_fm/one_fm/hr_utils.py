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



# def upload_file_for_leave(fname, content,content_type = None, is_private=0):
# def upload_file_for_leave(content=None,fname=None,*args, **kwargs):
#     """write file to disk with a random name (to compare)"""
    
    
#     if content.is_private:
#         file_url = "/private/files/{0}".format(content.file_name)
#     else:
#         file_url = "/files/{0}".format(content.file_name)
    
    
#     if content.attached_to_doctype == "Leave Application" and "new" in content.attached_to_name:
#         #Change the attached to name field and set the content hash as 
#         content.attached_to_name = ''
#         frappe.cache().set_value(str(frappe.session.user)+str(content.file_name), [content.content_hash,content.file_name])
#     # fpath = write_file(content, content.file_name, content.is_private)
#     fpath = content.write_file()
#     if not fpath:
#         pass
#     return {
#         'file_name': os.path.basename(fpath),
#         'file_url': file_url
#     }
#     # return {"file_name": os.path.basename(fpath), "file_url": self.file_url}

