import frappe


def get_depreciation_expense_amount(doc, handler=""):
    from_asset_depreciation = frappe.db.sql("""select sum(ja.debit) as depreciation_amount 
            from `tabJournal Entry Account` ja,`tabJournal Entry` j 
            where j.name = ja.parent and ja.parenttype = 'Journal Entry'
            and ja.project = %s and ja.reference_type = 'Asset'
            and j.voucher_type = 'Depreciation Entry' and ja.docstatus = 1 """,(doc.name),as_dict = 1)[0]

    doc.total_depreciation_expense = from_asset_depreciation.depreciation_amount

def on_project_save(doc, handler=""):
    if doc.project_type == 'External' and doc.customer:
        price_list = frappe.db.get_value('Price List', {'project': doc.name}, ['name'])
        if price_list:
            return
        else:
            price_list_doc = frappe.new_doc('Price List')
            price_list_doc.flags.ignore_permissions  = True
            price_list_doc.price_list_name = doc.name +'-'+doc.customer+'-'+'Selling'
            price_list_doc.project = doc.name
            price_list_doc.selling = 1
            price_list_doc.enabled = 1
            price_list_doc.append('countries', {
                'country':'Kuwait'
            })
            price_list_doc.update({
                'price_list_name': price_list_doc.price_list_name,
                'project': price_list_doc.project,
                'selling': price_list_doc.selling,
                'enabled': price_list_doc.enabled,
                'countries': price_list_doc.countries
            }).insert()
            return 	price_list_doc

def validate_poc_list(doc, method):
    project_type = str(doc.project_type)
    if project_type.lower() == "external" and len(doc.poc) == 0:
        frappe.throw('POC list is mandatory for project type <b>External</b>')