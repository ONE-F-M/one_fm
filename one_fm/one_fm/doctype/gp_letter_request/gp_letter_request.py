# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url

class GPLetterRequest(Document):
    def validate(self):
        self.generate_pid()

    def generate_pid(self):
        if not self.pid :
            self.pid = frappe.generate_hash(length=30)


    def generate_new_pid(self):
        self.pid = frappe.generate_hash(length=30)


    def get_page_link(self):
        return get_url("/gp_letter_request?pid=" + self.pid)

    def send_travel_agent_email(self):
        page_link = self.get_page_link()
        msg = frappe.render_template('one_fm/templates/emails/gp_letter_request.html', context={"page_link": page_link})
        sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
        recipient = 'omar.ja93@gmail.com'
        frappe.sendmail(sender=sender, recipients= recipient,
            content=msg, subject="Employment Details", delayed=False)
        self.db_set("sent_date", frappe.utils.now())
        
@frappe.whitelist()
def get_suppliers(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql("""select parent from `tabSupplier Group Table`
        where parenttype='Supplier' and parentfield='supplier_group_table' and group=%(supplier_group)s and subgroup=%(supplier_subgroup)s
            and ({key} like %(txt)s
                or parent like %(txt)s)
        order by
            if(locate(%(_txt)s, parent), locate(%(_txt)s, parent), 99999),
            idx desc,
            parent
        limit %(start)s, %(page_len)s""".format(**{
            'key': searchfield
        }), {
            'txt': "%s%%" % txt,
            '_txt': txt.replace("%", ""),
            'start': start,
            'page_len': page_len,
            'supplier_group': filters.get('supplier_group'),
            'supplier_subgroup': filters.get('supplier_subgroup')
        })



