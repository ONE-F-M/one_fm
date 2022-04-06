# -*- coding: utf-8 -*-
# Copyright (c) 2019, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate, formatdate ,get_url

class ItemRequest(Document):
    def validate(self):
        if hasattr(self,"workflow_state"):
            if "Rejected" in self.workflow_state:
                self.docstatus = 1
                self.docstatus = 2

        page_link = get_url("/desk#Form/Item Request/" + self.name)

        # self.send_notifications(page_link)

        # Line manager
        if frappe.session.user!='Administrator':
            frappe.publish_realtime(event='msgprint', message='New Item Request has been created, need your action <a href="{0}">Here</a>.'.format(page_link), user='Administrator')


    def on_submit(self):
        frappe.msgprint("Your request has been received")

        check_stock = frappe.get_doc({
            "doctype": "Stock Check",
            "item_request": self.name,
            "employee": self.employee,
            "employee_name": self.employee_name,
            "project": self.project,
            "site": self.site,
            "item_request_date": self.posting_date,
            "priority": self.priority,
            "nature_of_demand": self.nature_of_demand,
            "budgeted": self.budgeted
            })

        for item in self.items:
            if item.accepted:
                check_stock.append('item_coding', {"item_code_name":item.item_name,"item_category":item.item_category,"item_description":item.item_description,"qty":item.qty,"uom":item.uom})

        check_stock.flags.ignore_validate = True
        check_stock.flags.ignore_mandatory = True
        check_stock.save()
        frappe.db.commit()

        page_link = get_url("/desk#Form/Stock Check/" + check_stock.name)

        # self.send_notifications(page_link)
        
        # stock manager
        frappe.publish_realtime(event='msgprint', message='New Item Request has been approved, please check next step from <a href="{0}">Here</a> for your Action'.format(page_link), user='Administrator')
        
        # employee who create
        prefered_email_employee = frappe.get_value("Employee", filters = {"name": self.employee}, fieldname = "prefered_email")
        frappe.publish_realtime(event='msgprint', message='Your Item Request has been approved, and its now under stock review', user=prefered_email_employee)


    def send_notifications(self,page_link):
        from frappe.core.doctype.communication.email import make
        
        msg_emp = frappe.render_template('one_fm/templates/emails/item_request_emp.html', context={"page_link": page_link})
        msg_mng = frappe.render_template('one_fm/templates/emails/item_request_mng.html', context={"page_link": page_link})

        # sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
        sender = "omar.ja93@gmail.com" or None
        prefered_email_employee = frappe.get_value("Employee", filters = {"name": self.employee}, fieldname = "prefered_email")
        prefered_email_manager = frappe.get_value("Employee", filters = {"name": frappe.session.user}, fieldname = "prefered_email")
        
        # stock manager
        frappe.publish_realtime(event='msgprint', message='New Item Request has been approved, please check next step from <a href="{0}">Here</a> for your Action'.format(page_link), user='omar.ja93@gmail.com')
        
        # employee who create
        frappe.publish_realtime(event='msgprint', message='Your Item Request has been approved, and its now under stock review', user=prefered_email_employee)

        if sender and prefered_email_employee:
            try:
                make(subject = "Item Request | {0}".format(self.name), content=msg_mng, recipients=prefered_email_employee,
                    send_email=True, sender=sender)
                
                print('send email for '+prefered_email_employee)
            except:
                print('could not send for '+prefered_email_employee)

        if sender and  prefered_email_manager:
            try:
                make(subject = "Item Request | {0}".format(page_link), content=msg_mng, recipients=prefered_email_manager,
                    send_email=True, sender=sender)
                
                print('send email for '+prefered_email_manager)
            except:
                print('could not send for '+prefered_email_manager)




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
    
