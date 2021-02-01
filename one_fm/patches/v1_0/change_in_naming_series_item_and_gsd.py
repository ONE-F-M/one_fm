from __future__ import unicode_literals
import frappe

def execute():
    # UNF-SHT-#### to UNF-SHT-######
    rename_item_according_to_new_series()
    # PUR-ORD-YYYY-##### to POR-YYYY-######
    rename_po_according_to_new_series()
    # MAT-PRE-YYYY-##### to PRC-YYYY-######
    rename_pr_according_to_new_series()
    # RM-YYYY-##### to RFM-YYYY-######
    rename_rfm_according_to_new_series()

def rename_rfm_according_to_new_series():
    frappe.reload_doc('purchase', 'doctype', 'request_for_material')
    for doc in frappe.get_all('Request for Material'):
        series = doc.name[8:]
        year = doc.name[3:7]
        new_name = "RFM-"+year+"-0"+series
        frappe.rename_doc('Request for Material', doc.name, new_name, force=True)
        print(doc.name)
        print(new_name)
        print("===========")

def rename_po_according_to_new_series():
    frappe.reload_doc('buying', 'doctype', 'purchase_order')
    for doc in frappe.get_all('Purchase Order'):
        series = doc.name[13:]
        year = doc.name[8:12]
        new_name = "POR-"+year+"-0"+series
        frappe.rename_doc('Purchase Order', doc.name, new_name, force=True)
        print(doc.name)
        print(new_name)
        print("===========")

def rename_pr_according_to_new_series():
    frappe.reload_doc('stock', 'doctype', 'purchase_receipt')
    for doc in frappe.get_all('Purchase Receipt'):
        series = doc.name[13:]
        year = doc.name[8:12]
        new_name = "PRC-"+year+"-0"+series
        frappe.rename_doc('Purchase Receipt', doc.name, new_name, force=True)
        print(doc.name)
        print(new_name)
        print("===========")

def rename_item_according_to_new_series():
    frappe.reload_doc('stock', 'doctype', 'item')
    old_item_code_field = False
    if frappe.db.has_column('Item', 'old_item_code'):
        old_item_code_field = True
    for doc in frappe.get_all('Item', filters={'subitem_group': 'Uniforms'}):
        if len(doc.name)==12:
            _doc = frappe.get_doc('Item', doc.name)
            if old_item_code_field:
                _doc.old_item_code = doc.name
            subitem_group_code = frappe.db.get_value('Item Group', _doc.subitem_group, 'one_fm_item_group_abbr')
            item_group_code = frappe.db.get_value('Item Group', _doc.item_group, 'one_fm_item_group_abbr')
            new_item_code = subitem_group_code+"-"+item_group_code+"-"+"00"+doc.name[-4:]
            _doc.item_code = new_item_code
            _doc.item_name = new_item_code
            _doc.item_barcode = new_item_code
            _doc.item_id = "00"+doc.name[-4:]
            _doc.save(ignore_permissions=True)
            frappe.rename_doc('Item', doc.name, new_item_code, force=True)
            print(doc.name)
            print(new_item_code)
