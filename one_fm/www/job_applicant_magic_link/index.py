from google.cloud import vision
import os, io, base64, datetime, hashlib, frappe, json
from frappe.utils import cstr
import frappe.sessions
from mindee import Client, documents

from dateutil.parser import parse
from frappe import _
from frappe.utils.password import decrypt
from frappe.model.document import Document
from one_fm.one_fm.doctype.magic_link.magic_link import authorize_magic_link, send_magic_link
from one_fm.utils import set_expire_magic_link


@frappe.whitelist(allow_guest=True)
def get_magic_link():
    """
    Get magic link and decrypt, return the doc
    """
    result = {}
    try:
        
        if frappe.form_dict.magic_link:
            decrypted_magic_link = decrypt(frappe.form_dict.magic_link)
            if (frappe.db.exists("Magic Link", {'name':decrypted_magic_link})):
                magic_link = frappe.get_doc("Magic Link", {'name':decrypted_magic_link})
                if magic_link.expired:
                    result = {}
                else:
                    job_applicant = frappe.get_doc('Job Applicant', magic_link.reference_docname)
                    result = job_applicant
            else:
                result = {}
        else:
            result = {}

        return result
    except:
        frappe.log_error(frappe.get_traceback(), 'Magic Link')
        return result

    