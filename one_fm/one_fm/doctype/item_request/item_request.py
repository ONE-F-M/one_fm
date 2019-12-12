# -*- coding: utf-8 -*-
# Copyright (c) 2019, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ItemRequest(Document):
    def on_submit(self):
        frappe.msgprint("Your request has been received")
        self.send_notifications()


    def send_notifications(self):
        from frappe.core.doctype.communication.email import make

        msg="<b>We have received your item request and it's under review.</b>"
        # sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
        sender = "omar.ja93@gmail.com" or None
        prefered_email_employee = frappe.get_value("Employee", filters = {"name": self.employee}, fieldname = "prefered_email")
        prefered_email_manager = frappe.get_value("Employee", filters = {"name": frappe.session.user}, fieldname = "prefered_email")
        
        if sender and prefered_email_employee:
            try:
                make(subject = "Item Request | {0}".format(self.name), content=msg, recipients=prefered_email_employee,
                    send_email=True, sender=sender)
                
                msg = """Email send successfully to Employee"""
                print('send email for '+prefered_email_employee)
                # frappe.msgprint(msg)
            except:
                print('could not send for '+prefered_email_employee)
                # frappe.msgprint("could not send")

        if sender and  prefered_email_manager:
            try:
                make(subject = "Item Request | {0}".format(self.name), content=msg, recipients=prefered_email_manager,
                    send_email=True, sender=sender)
                
                msg = """Email send successfully to Employee"""
                print('send email for '+prefered_email_manager)
                # frappe.msgprint(msg)
            except:
                print('could not send for '+prefered_email_manager)
                # frappe.msgprint("could not send")




@frappe.whitelist()
def get_data(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql("""select site from `tabProject Sites`
        where parent = %(project_parent)s
            and docstatus < 2
            and {key} like %(txt)s
        order by
            if(locate(%(_txt)s, site), locate(%(_txt)s, site), 99999),
            idx desc,
            site
        limit %(start)s, %(page_len)s""".format(**{
            'key': searchfield
        }), {
            'txt': "%s%%" % txt,
            '_txt': txt.replace("%", ""),
            'start': start,
            'page_len': page_len,
            'project_parent': filters.get("project_parent")
        })
    
