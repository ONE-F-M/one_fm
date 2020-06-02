# -*- coding: utf-8 -*-
# Copyright (c) 2019, Mawrederp  and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import throw, msgprint
import requests
import json
from frappe.utils.file_manager import save_file
import hashlib
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate, formatdate ,get_url, get_datetime


def get_context(context):
    if frappe.local.request.method == "GET" and "pid" not in frappe.form_dict:
        frappe.local.flags.redirect_location = "/404"
        raise frappe.Redirect

    if frappe.local.request.method == "GET" and not verify_pid(frappe.form_dict.pid):
        frappe.local.flags.redirect_location = "/404"
        raise frappe.Redirect

    if frappe.local.request.method == "GET":
        context.pid = frappe.form_dict.pid

    
def verify_pid(pid):
    verified_pid = frappe.db.get_value("GP Letter Request", filters = {"pid": pid}, fieldname = "pid")
    return verified_pid if verified_pid else False



@frappe.whitelist(allow_guest=True)
def update_gp_letter_request_status(pid, gp_status):

    if gp_status not in ('Accept', 'Reject'):
        frappe.throw("Please select an option from above selection")

    gp_letter_request = frappe.get_value("GP Letter Request", filters = {"pid": pid}, fieldname = ["name", "gp_status"])
    if gp_letter_request:
        if gp_letter_request[1] in ('Accept', 'Reject'):
            frappe.msgprint("Your data is already sent!")
            return 'false'

        else:
            gp_doc = frappe.get_doc("GP Letter Request", gp_letter_request[0])
            gp_doc.gp_status = gp_status
            gp_doc.accept_date = frappe.utils.now()

            if gp_status=='Reject':
                gp_doc.supplier = ''
                gp_doc.supplier_name = ''

            gp_doc.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.msgprint("Your data has been successfully registered!")

            gp_letters = frappe.db.get_list("GP Letter", filters = {"gp_letter_request_reference": gp_letter_request[0]}, fields = ["name"])
            for gp_letter in gp_letters:
                doc = frappe.get_doc("GP Letter", gp_letter['name'])
                request_doc = frappe.get_doc("GP Letter Request", gp_letter_request[0])

                doc.gp_status = gp_status
                doc.gp_letter_request_date = frappe.utils.now()

                if gp_status=='Accept':
                    doc.supplier_category = request_doc.supplier_category
                    doc.supplier_subcategory = request_doc.supplier_subcategory
                    doc.supplier = request_doc.supplier

                doc.save(ignore_permissions=True)
                frappe.db.commit()


            if gp_status=='Accept':
                gp_letter_doc = frappe.get_doc("GP Letter Request", gp_letter_request[0])

                page_link = get_url("/gp_letter_attachment?pid=" + pid)
                msg = frappe.render_template('one_fm/templates/emails/gp_letter_attachment.html', context={"page_link": page_link, "candidates": gp_letter_doc.gp_letter_candidates})
                sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
                recipient = 'omar.ja93@gmail.com'
                frappe.sendmail(sender=sender, recipients= recipient,
                    content=msg, subject="GP Letter Attachment", delayed=False)
            else:
                
                gp_letter_request = frappe.db.get_value("GP Letter Request", filters = {"pid": pid}, fieldname = "name")

                page_link = get_url("/desk#Form/GP Letter Request/" + gp_letter_request)
                msg = frappe.render_template('one_fm/templates/emails/gp_letter_request_rejected.html', context={"page_link": page_link, "gp_letter_request": gp_letter_request})
                sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
                recipient = 'omar.ja93@gmail.com'
                frappe.sendmail(sender=sender, recipients= recipient,
                    content=msg, subject="GP Letter Request Rejected", delayed=False)



            return 'success'
    else:
        return 'invalid token'  

