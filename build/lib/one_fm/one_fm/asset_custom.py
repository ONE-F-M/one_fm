from __future__ import unicode_literals
import frappe

def on_asset_submit(doc, handler=""):
    #it will execute if it is not an existing asset
    asset_movement = frappe.db.get_value("Asset Movement Item",
		filters={'parenttype': 'Asset Movement', 'asset': doc.name},
		fieldname = ['parent'])
    
    make_asset_movement(doc)
    ass_doc = frappe.get_doc("Asset Movement", asset_movement)
    ass_doc.cancel()
    frappe.delete_doc("Asset Movement", asset_movement)

def after_insert_asset(doc,handler=""):
    row = doc.append("asset_transfer", {
        "purpose": "Receipt",
        "transfer_date": doc.purchase_date,
        "location": doc.location
    })
    doc.save()


def make_asset_movement(doc):
    for item in doc.asset_transfer:
        reference_doctype = reference_docname = None
        if item.purpose == 'Receipt':
            reference_doctype = 'Purchase Receipt' if doc.purchase_receipt else 'Purchase Invoice'
            reference_docname = doc.purchase_receipt or doc.purchase_invoice
        assets = [{
            'asset': doc.name,
            'asset_name': doc.asset_name,
            'target_location': item.location,
            'to_employee': item.employee
        }]
        asset_movement = frappe.get_doc({
            'doctype': 'Asset Movement',
            'assets': assets,
            'purpose': item.purpose,
            'company': doc.company,
            'transaction_date': item.transfer_date,
            'reference_doctype': reference_doctype,
            'reference_name': reference_docname
        }).insert()
        asset_movement.submit()
