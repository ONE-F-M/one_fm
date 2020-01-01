# -*- coding: utf-8 -*-
# Copyright (c) 2019, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate, formatdate ,get_url

class StockCheck(Document):
    def on_submit(self):
        for item in self.item_coding:
            if item.actual_qty > item.qty:

                delivery_doc = frappe.get_doc({
                    "doctype": "Delivery Note",
                    "item_request": self.item_request,
                    "set_warehouse": item.warehouse
                    })

                delivery_doc.append('items', {"item_code":item.item_code,"description":item.item_description,"qty":item.qty,"uom":item.uom})

                delivery_doc.flags.ignore_validate = True
                delivery_doc.flags.ignore_mandatory = True
                delivery_doc.save()
                frappe.db.commit()

                page_link = get_url("/desk#Form/Delivery Note/" + delivery_doc.name)
                frappe.msgprint("<a href='{0}'>Delivery Note</a> has been created".format(page_link))

                # self.send_notifications(page_link)

            else:
                purchase_doc = frappe.get_doc({
                    "doctype": "Purchase Order",
                    "item_request": self.item_request,
                    "set_warehouse": item.warehouse
                    })

                purchase_doc.append('items', {"item_code":item.item_code,"schedule_date":self.posting_date,"description":item.item_description,"qty":item.qty,"uom":item.uom,"warehouse":item.warehouse})

                purchase_doc.flags.ignore_validate = True
                purchase_doc.flags.ignore_mandatory = True
                purchase_doc.save()
                frappe.db.commit()

                page_link = get_url("/desk#Form/Purchase Order/" + purchase_doc.name)
                frappe.msgprint("<a href='{0}'>Purchase Order</a> has been created".format(page_link))

                # self.send_notifications(page_link)


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



    def set_actual_qty(self, item_code, warehouse):
        if item_code and warehouse:
            current_actual_qty = flt(0)
            actual_qty = frappe.db.sql("""select actual_qty from `tabBin`
                where item_code = %s and warehouse = %s""", (item_code, warehouse))
            if actual_qty:
                current_actual_qty = flt(actual_qty[0][0])

        return current_actual_qty
