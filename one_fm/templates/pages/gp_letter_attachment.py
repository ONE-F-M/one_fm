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
from one_fm.utils import sendemail


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

@frappe.whitelist(allow_guest = True)
def get_candidates(pid):
    gp_letter_request = frappe.db.get_value("GP Letter Request", filters = {"pid": pid}, fieldname = "name")

    candidates = frappe.db.sql("select name, candidate_name, gp_letter_attachment from `tabGP Letter` where gp_letter_request_reference='{0}'".format(gp_letter_request))
    if candidates:
        return candidates

@frappe.whitelist(allow_guest = True)
def get_attachment_details(data, qp_letter):

    form_data = json.loads(data)

    # fields = ["gp_letter_candidate1"]
    fields = json.loads(qp_letter)

    if not validate_missing_fields_values(form_data, fields):
        return

    if form_data["pid"]:
        gp_letter_request = frappe.db.get_value("GP Letter Request", filters = {"pid": form_data["pid"]}, fieldname = "name")

        for qp in fields:
            if qp:

                # gp_doc = frappe.get_doc("GP Letter", qp)


                # for attached_file in ["gp_letter_candidate1"]:
                # for attached_file in qp_letter:

                attach_file_to_gp_letter(form_data[qp], qp)

                attach_file_to_gp_letter_request(form_data[qp], gp_letter_request)


                doc = frappe.new_doc("PAM Visa")
                doc.pam_visa_reminder1 = frappe.utils.now()
                doc.insert()

                page_link = "http://206.189.228.82/desk#Form/PAM Visa/" + cstr(doc.name)
                # page_link = get_url("/desk#Form/PAM Visa/" + doc.name)
                msg = frappe.render_template('one_fm/templates/emails/pam_visa.html', context={"page_link": page_link})
                sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
                recipient = frappe.db.get_single_value('PAM Visa Setting', 'grd_operator')

                sendemail(sender=sender, recipients= recipient,
                    content=msg, subject="PAM Visa", delayed=False)


        return 'success'

    else:
        return 'invalid token'  

def attach_file_to_gp_letter(filedata, docname):

    fd_list = list(filedata["files_data"])
    for fd in fd_list:

        filedoc = save_file(fd["filename"], fd["dataurl"],
          "GP Letter", docname, decode=True, is_private=1)

        doc = frappe.get_doc("GP Letter", docname)
        doc.gp_letter_attachment = fd["filename"]
        doc.gp_letter_attachment_date = frappe.utils.now()
        doc.save(ignore_permissions=True)
        frappe.db.commit()


        gp_doc = frappe.get_doc("GP Letter Request", doc.gp_letter_request_reference)
        for candidate in gp_doc.gp_letter_candidates:
            if candidate.gp_letter==docname:
                candidate.gp_letter_attachment = fd["filename"]
                candidate.gp_letter_attachment_date = frappe.utils.now()
        gp_doc.save(ignore_permissions=True)
        frappe.db.commit()



def attach_file_to_gp_letter_request(filedata, docname):

    fd_list = list(filedata["files_data"])
    for fd in fd_list:

        filedoc = save_file(fd["filename"], fd["dataurl"],
          "GP Letter Request", docname, decode=True, is_private=1)

        doc = frappe.get_doc("GP Letter Request", docname)
        doc.gp_letter_attachment = fd["filename"]
        doc.save(ignore_permissions=True)
        frappe.db.commit()


def validate_missing_fields_values(form_data, fields):
    for field in fields:
        if not form_data[field]:
            frappe.response["message"] = "Please fill the missing fields"
            return False
    return True

    