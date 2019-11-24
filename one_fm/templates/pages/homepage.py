# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, nowdate, cint
import datetime
from datetime import date
from frappe.utils.data import flt, nowdate, getdate, cint
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate , add_days


no_cache = 1
no_sitemap = 1

def get_context(context):
    context.show_search = True



@frappe.whitelist(allow_guest=True)
def get_website_info_count():
    project_count = frappe.db.sql(""" select count(name) from `tabProject` """)[0][0]
    employee_count = frappe.db.sql(""" select count(name) from `tabEmployee` """)[0][0]
    sites_count = frappe.db.sql(""" select count(name) from `tabProject` """)[0][0]
    clients_count = frappe.db.sql(""" select count(name) from `tabCustomer` """)[0][0]
    return project_count, employee_count, sites_count, clients_count


@frappe.whitelist(allow_guest=True)
def send_contact_email():

    # sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None

    # msg = frappe.render_template('client_customizer/templates/emails/employee_disclaimer.html', context={"page_link": page_link,"employee_name": emp_name})

    # rec = "omar.ja93@gmail.com" or None

    # if rec != None:
    #     try:
    #         frappe.sendmail(sender=sender, recipients= rec,
    #             content='msg', subject="Employee job - {0}".format('ahmed'))
    #     except:
    #         frappe.msgprint(_("could not send"))

    return 'holla yaah'

