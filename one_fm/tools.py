# -*- coding:utf-8 -*-
# encoding: utf-8

# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import frappe, os
from frappe.model.document import Document
from frappe.utils import get_site_base_path
from frappe.utils.data import flt, nowdate, getdate, cint
from frappe.utils.csvutils import read_csv_content_from_uploaded_file
from frappe.utils.password import update_password as _update_password
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate



def add_suppliers():
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open("/home/frappe/frappe-bench/apps/one_fm/one_fm/Purchasing Data/supplier_code.csv", "r") as infile:   
        rows = read_csv_content(infile.read())
        i = 0
        for index, row in enumerate(rows):
            if not frappe.db.exists("Supplier Group", {"supplier_group_name": row[2]}):

                frappe.get_doc({
                  "doctype":"Supplier Group",
                  "supplier_group_name": row[2]
                }).insert(ignore_permissions=True)


            supp = frappe.get_doc({
              "doctype":"Supplier",
              "supplier_name": row[1],
              "supplier_group": row[2]
            })
            supp.insert(ignore_permissions=True)

            if row[3]:
                frappe.get_doc({
                  "doctype":"Address",
                  "address_type": 'Office',
                  "address_line1": row[3],
                  "city": 'KUWAIT',
                  "links": [
                      {
                        "doctype": "Dynamic Link",
                        "parenttype": "Address",
                        "link_doctype": 'Supplier',
                        "link_name": supp.name
                      }
                    ]
                }).insert(ignore_permissions=True)

            if row[4]:

                doc = frappe.new_doc('Contact')
                doc.first_name = row[4]

                if row[5]:
                    doc.append("phone_nos",{
                        "doctype": "Dynamic Link",
                            "parenttype": "Contact",
                            "phone": row[5],
                            "is_primary_phone": 1
                        })

                if row[6]:
                    doc.append("phone_nos",{
                        "doctype": "Dynamic Link",
                            "parenttype": "Contact",
                            "phone": row[6],
                            "is_primary_mobile_no": 1
                        })

                if row[7]:
                    doc.append("email_ids",{
                        "doctype": "Contact Email",
                            "parenttype": "Contact",
                            "email_id": row[7],
                            "is_primary": 1
                        })

                doc.append("links",{
                    "doctype": "Dynamic Link",
                        "parenttype": "Contact",
                        "link_doctype": 'Supplier',
                        "link_name": supp.name
                    })

                doc.insert(ignore_permissions=True)
                print(row[0])




def add_asset_item():
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open("/home/frappe/frappe-bench/apps/one_fm/one_fm/Purchasing Data/asset_item.csv", "r") as infile:   
        rows = read_csv_content(infile.read())
        i = 0
        for index, row in enumerate(rows):
            if not frappe.db.exists("Item Group", {"item_group_name": row[1]}):

                frappe.get_doc({
                  "doctype":"Item Group",
                  "parent_item_group": '001-Assets',
                  "item_group_name": row[1]
                }).insert(ignore_permissions=True)


            if not frappe.db.exists("Item Group", {"item_group_name": row[3]}):

                item_group_name_parent = frappe.db.get_value("Item Group", {"item_group_name": row[1]}, "name")


                doc = frappe.get_doc({
                  "doctype":"Item Group",
                  "parent_item_group": item_group_name_parent,
                  "item_group_name": row[3]
                })
                doc.insert(ignore_permissions=True)

            if not frappe.db.exists("UOM", {"uom_abbreviation": row[6]}):
                frappe.get_doc({
                  "doctype":"UOM",
                  "uom_abbreviation": row[6]
                }).insert(ignore_permissions=True)


            # subitem_group = frappe.db.get_value("Item Group", {"item_group_name": row[1]}, "name")
            # item_group = frappe.db.get_value("Item Group", {"item_group_name": row[3]}, "name")

            # doc = frappe.get_doc({
            #   "doctype":"Item",
            #   "parent_item_group": '001-Assets',
            #   "subitem_group": subitem_group,
            #   "item_group": item_group,
            #   "stock_uom": row[6],
            #   "description": row[8]
            # })
            # doc.flags.ignore_mandatory = True
            # doc.insert(ignore_permissions=True)

            i+=1
            print(i)

        print('*********************************')
        print(i)
        print('*********************************')





# def remov_data():
#     data = frappe.db.sql_list("select name from `tabUOM` where name not in ('PCS','Nos')")
#     for i in data:
#         doc = frappe.get_doc("UOM", i)
#         doc.delete()
#         print(i)


def add_fm_item_group():
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open("/home/frappe/frappe-bench/apps/one_fm/one_fm/Purchasing master plan .csv", "r") as infile:   
        rows = read_csv_content(infile.read())
        i = 0
        for index, row in enumerate(rows):
            frappe.get_doc({
              "doctype":"Item Group",
              "parent_item_group": row[0],
              "item_group_code": row[1],
              "item_group_name": row[2],
              "is_group": 1
            }).insert(ignore_permissions=True)

            i+=1
            print(row[0])

        print('*************')
        print(i)




def update_administrator_pass():
    _update_password('administrator', 'back2track700')


def add_fm_accounts():
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open("/home/frappe/frappe-bench/apps/one_fm/one_fm/Chart_of_Accounts.csv", "r") as infile:   
        rows = read_csv_content(infile.read())
        i = 0
        for index, row in enumerate(rows):
   #          frappe.get_doc({
            #   "doctype":"Account",
            #   "acount_name": row[0],
            #   "parent_account": row[1],
            #   "is_group": row[3]
            # }).insert(ignore_permissions=True)

            i+=1
            print(row[0])

        print('*************')
        print(i)



def get_website_info_data():
    # about_us_info = frappe.client.get_list("Website Info", fields=['section_title','section_header','section_subject'])
    about_us_info = frappe.db.get_single_value("Website Info", "section_subject")
    print(about_us_info)



def send_email_tst():
    msg = """Hiii this is tst email"""
    frappe.sendmail(recipients="omar.ja93@gmail.com", sender="omar.ja93@gmail.com", content=msg, subject="test subject")

