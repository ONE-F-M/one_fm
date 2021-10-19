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
from frappe.utils.password import update_password as _update_password
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate



def test_excel():
    import xlsxwriter

    workbook = xlsxwriter.Workbook('/home/frappe/frappe-bench/apps/one_fm/one_fm/hello.xlsx')

    worksheet = workbook.add_worksheet()

    worksheet.write('A1', 'Sr.No')
    worksheet.write('B1', 'Candidate Name In English')
    worksheet.write('C1', 'Candidate Name In Arabic')
    worksheet.write('D1', 'Passport Number')
    worksheet.write('E1', 'Candidate Nationality in Arabic')
    worksheet.write('F1', 'Company Name in Arabic')

    worksheet.set_column('B:F', 22)

    candidates = ['1','Omhhar','عمر','12345','فلسطيني','ONE FM']

    row = 1
    column = 0

    for candidate in candidates:
        worksheet.write(row, column, candidate)
        column += 1

    row += 1

    workbook.close()
    print('Done')


def add_uniform_item():
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open("/home/frappe/frappe-bench/apps/one_fm/one_fm/Purchasing Data/uniform_item.csv", "r") as infile:
        rows = read_csv_content(infile.read())
        i = 0
        for index, row in enumerate(rows):
            if row[2]:
                if not frappe.db.exists("Item Group", {"name": '005-Uniforms'}):

                    frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": 'All Item Groups',
                      "item_group_code": '005',
                      "item_group_name": 'Uniforms',
                      "is_group": 1
                    }).insert(ignore_permissions=True)

                if not frappe.db.exists("Item Group", {"name": str(row[0])+'-'+str(row[1])}):

                    frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": '005-Uniforms',
                      "item_group_code": row[0],
                      "item_group_name": row[1],
                      "is_group": 1
                    }).insert(ignore_permissions=True)


                if not frappe.db.exists("Item Group", {"name": str(row[2])+'-'+str(row[3])}):

                    item_group_name_parent = str(row[0])+'-'+str(row[1])

                    doc = frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": item_group_name_parent,
                      "item_group_code": row[2],
                      "item_group_name": row[3],
                      "is_group": 0
                    })
                    doc.insert(ignore_permissions=True)

                if not frappe.db.exists("UOM", {"uom_abbreviation": row[6]}):
                    frappe.get_doc({
                      "doctype":"UOM",
                      "uom_name": row[6],
                      "uom_abbreviation": row[6]
                    }).insert(ignore_permissions=True)


                if not frappe.db.exists("Item", {"name": '005'+str(row[0])+str(row[2])+str(row[4])}):

                    subitem_group = str(row[0])+'-'+str(row[1])
                    item_group = str(row[2])+'-'+str(row[3])

                    doc = frappe.get_doc({
                      "doctype":"Item",
                      "parent_item_group": '005-Uniforms',
                      "subitem_group": subitem_group,
                      "item_group": item_group,
                      "item_id": str(row[4]),
                      "item_code": '005'+str(row[0])+str(row[2])+str(row[4]),
                      "stock_uom": row[6],
                      "description1": row[5],
                      "description2": row[5],
                      "description3": row[5],
                      "description4": row[5],
                      "description5": row[5],
                      "description": row[5]
                    })
                    doc.flags.ignore_mandatory = True
                    doc.insert(ignore_permissions=True)

                i+=1
                print(str(i)+ ' ----- ' +'005'+str(row[0])+str(row[2])+str(row[4]))

        print('*********************************')
        print(i)
        print('*********************************')







def add_services_item():
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open("/home/frappe/frappe-bench/apps/one_fm/one_fm/Purchasing Data/services_item.csv", "r") as infile:
        rows = read_csv_content(infile.read())
        i = 0
        for index, row in enumerate(rows):
            if row[2]:
                if not frappe.db.exists("Item Group", {"name": '004-Services'}):

                    frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": 'All Item Groups',
                      "item_group_code": '004',
                      "item_group_name": 'Services',
                      "is_group": 1
                    }).insert(ignore_permissions=True)

                if not frappe.db.exists("Item Group", {"name": str(row[0])+'-'+str(row[1])}):

                    frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": '004-Services',
                      "item_group_code": row[0],
                      "item_group_name": row[1],
                      "is_group": 1
                    }).insert(ignore_permissions=True)


                if not frappe.db.exists("Item Group", {"name": str(row[2])+'-'+str(row[3])}):

                    item_group_name_parent = str(row[0])+'-'+str(row[1])

                    doc = frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": item_group_name_parent,
                      "item_group_code": row[2],
                      "item_group_name": row[3],
                      "is_group": 0
                    })
                    doc.insert(ignore_permissions=True)

                if not frappe.db.exists("UOM", {"uom_abbreviation": row[6]}):
                    frappe.get_doc({
                      "doctype":"UOM",
                      "uom_name": row[6],
                      "uom_abbreviation": row[6]
                    }).insert(ignore_permissions=True)


                if not frappe.db.exists("Item", {"name": '004'+str(row[0])+str(row[2])+str(row[4])}):

                    subitem_group = str(row[0])+'-'+str(row[1])
                    item_group = str(row[2])+'-'+str(row[3])

                    doc = frappe.get_doc({
                      "doctype":"Item",
                      "parent_item_group": '004-Services',
                      "subitem_group": subitem_group,
                      "item_group": item_group,
                      "item_id": str(row[4]),
                      "item_code": '004'+str(row[0])+str(row[2])+str(row[4]),
                      "stock_uom": row[6],
                      "description1": row[5],
                      "description2": row[5],
                      "description3": row[5],
                      "description4": row[5],
                      "description5": row[5],
                      "description": row[5]
                    })
                    doc.flags.ignore_mandatory = True
                    doc.insert(ignore_permissions=True)

                i+=1
                print(str(i)+ ' ----- ' +'004'+str(row[0])+str(row[2])+str(row[4]))

        print('*********************************')
        print(i)
        print('*********************************')







def add_contarcting_item():
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open("/home/frappe/frappe-bench/apps/one_fm/one_fm/Purchasing Data/contarcting_item.csv", "r") as infile:
        rows = read_csv_content(infile.read())
        i = 0
        for index, row in enumerate(rows):
            if row[2]:
                if not frappe.db.exists("Item Group", {"name": '003-Contarcting'}):

                    frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": 'All Item Groups',
                      "item_group_code": '003',
                      "item_group_name": 'Contarcting',
                      "is_group": 1
                    }).insert(ignore_permissions=True)

                if not frappe.db.exists("Item Group", {"name": str(row[0])+'-'+str(row[1])}):

                    frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": '003-Contarcting',
                      "item_group_code": row[0],
                      "item_group_name": row[1],
                      "is_group": 1
                    }).insert(ignore_permissions=True)


                if not frappe.db.exists("Item Group", {"name": str(row[2])+'-'+str(row[3])}):

                    item_group_name_parent = str(row[0])+'-'+str(row[1])

                    doc = frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": item_group_name_parent,
                      "item_group_code": row[2],
                      "item_group_name": row[3],
                      "is_group": 0
                    })
                    doc.insert(ignore_permissions=True)

                if not frappe.db.exists("UOM", {"uom_abbreviation": row[6]}):
                    frappe.get_doc({
                      "doctype":"UOM",
                      "uom_name": row[6],
                      "uom_abbreviation": row[6]
                    }).insert(ignore_permissions=True)


                if not frappe.db.exists("Item", {"name": '003'+str(row[0])+str(row[2])+str(row[4])}):

                    subitem_group = str(row[0])+'-'+str(row[1])
                    item_group = str(row[2])+'-'+str(row[3])

                    doc = frappe.get_doc({
                      "doctype":"Item",
                      "parent_item_group": '003-Contarcting',
                      "subitem_group": subitem_group,
                      "item_group": item_group,
                      "item_id": str(row[4]),
                      "item_code": '003'+str(row[0])+str(row[2])+str(row[4]),
                      "stock_uom": row[6],
                      "description1": row[5],
                      "description2": row[5],
                      "description3": row[5],
                      "description4": row[5],
                      "description5": row[5],
                      "description": row[5]
                    })
                    doc.flags.ignore_mandatory = True
                    doc.insert(ignore_permissions=True)

                i+=1
                print(str(i)+ ' ----- ' +'003'+str(row[0])+str(row[2])+str(row[4]))

        print('*********************************')
        print(i)
        print('*********************************')






def add_consumables_item():
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open("/home/frappe/frappe-bench/apps/one_fm/one_fm/Purchasing Data/consumables_item.csv", "r") as infile:
        rows = read_csv_content(infile.read())
        i = 0
        for index, row in enumerate(rows):
            if row[2]:
                if not frappe.db.exists("Item Group", {"name": '002-Consumables'}):

                    frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": 'All Item Groups',
                      "item_group_code": '002',
                      "item_group_name": 'Consumables',
                      "is_group": 1
                    }).insert(ignore_permissions=True)

                if not frappe.db.exists("Item Group", {"name": str(row[0])+'-'+str(row[1])}):

                    frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": '002-Consumables',
                      "item_group_code": row[0],
                      "item_group_name": row[1],
                      "is_group": 1
                    }).insert(ignore_permissions=True)


                if not frappe.db.exists("Item Group", {"name": str(row[2])+'-'+str(row[3])}):

                    item_group_name_parent = str(row[0])+'-'+str(row[1])

                    doc = frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": item_group_name_parent,
                      "item_group_code": row[2],
                      "item_group_name": row[3],
                      "is_group": 0
                    })
                    doc.insert(ignore_permissions=True)

                if not frappe.db.exists("UOM", {"uom_abbreviation": row[6]}):
                    frappe.get_doc({
                      "doctype":"UOM",
                      "uom_name": row[6],
                      "uom_abbreviation": row[6]
                    }).insert(ignore_permissions=True)


                if not frappe.db.exists("Item", {"name": '002'+str(row[0])+str(row[2])+str(row[4])}):

                    subitem_group = str(row[0])+'-'+str(row[1])
                    item_group = str(row[2])+'-'+str(row[3])

                    doc = frappe.get_doc({
                      "doctype":"Item",
                      "parent_item_group": '002-Consumables',
                      "subitem_group": subitem_group,
                      "item_group": item_group,
                      "item_id": str(row[4]),
                      "item_code": '002'+str(row[0])+str(row[2])+str(row[4]),
                      "stock_uom": row[6],
                      "description1": row[5],
                      "description2": row[5],
                      "description3": row[5],
                      "description4": row[5],
                      "description5": row[5],
                      "description": row[5]
                    })
                    doc.flags.ignore_mandatory = True
                    doc.insert(ignore_permissions=True)

                i+=1
                print(str(i)+ ' ----- ' +'002'+str(row[0])+str(row[2])+str(row[4]))

        print('*********************************')
        print(i)
        print('*********************************')




def add_asset_item():
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open("/home/frappe/frappe-bench/apps/one_fm/one_fm/Purchasing Data/asset_item.csv", "r") as infile:
        rows = read_csv_content(infile.read())
        i = 0
        for index, row in enumerate(rows):
            if row[2]:
                if not frappe.db.exists("Item Group", {"name": '001-Assets'}):

                    frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": 'All Item Groups',
                      "item_group_code": '001',
                      "item_group_name": 'Assets',
                      "is_group": 1
                    }).insert(ignore_permissions=True)

                if not frappe.db.exists("Item Group", {"name": str(row[0])+'-'+str(row[1])}):

                    frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": '001-Assets',
                      "item_group_code": row[0],
                      "item_group_name": row[1],
                      "is_group": 1
                    }).insert(ignore_permissions=True)


                if not frappe.db.exists("Item Group", {"name": str(row[2])+'-'+str(row[3])}):

                    item_group_name_parent = str(row[0])+'-'+str(row[1])

                    doc = frappe.get_doc({
                      "doctype":"Item Group",
                      "parent_item_group": item_group_name_parent,
                      "item_group_code": row[2],
                      "item_group_name": row[3],
                      "is_group": 0
                    })
                    doc.insert(ignore_permissions=True)

                if not frappe.db.exists("UOM", {"uom_abbreviation": row[6]}):
                    frappe.get_doc({
                      "doctype":"UOM",
                      "uom_name": row[6],
                      "uom_abbreviation": row[6]
                    }).insert(ignore_permissions=True)


                if not frappe.db.exists("Item", {"name": '001'+str(row[0])+str(row[2])+str(row[4])}):

                    subitem_group = str(row[0])+'-'+str(row[1])
                    item_group = str(row[2])+'-'+str(row[3])

                    doc = frappe.get_doc({
                      "doctype":"Item",
                      "parent_item_group": '001-Assets',
                      "subitem_group": subitem_group,
                      "item_group": item_group,
                      "item_id": str(row[4]),
                      "item_code": '001'+str(row[0])+str(row[2])+str(row[4]),
                      "stock_uom": row[6],
                      "description1": row[5],
                      "description2": row[5],
                      "description3": row[5],
                      "description4": row[5],
                      "description5": row[5],
                      "description": row[5]
                    })
                    doc.flags.ignore_mandatory = True
                    doc.insert(ignore_permissions=True)

                i+=1
                print(str(i)+ ' ----- ' +'001'+str(row[0])+str(row[2])+str(row[4]))

        print('*********************************')
        print(i)
        print('*********************************')





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
