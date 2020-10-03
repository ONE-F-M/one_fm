import frappe


def on_project_save(doc, handler=""):
    if doc.project_type == 'External':
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
