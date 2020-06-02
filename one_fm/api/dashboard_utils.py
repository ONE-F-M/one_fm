import frappe
from frappe import _
import json
from frappe.desk.notifications import get_filters_for

@frappe.whitelist()
def get_open_count(doctype, name, links):
	'''Get open count for given transactions and filters
	:param doctype: Reference DocType
	:param name: Reference Name
	:param transactions: List of transactions (json/dict)
	:param filters: optional filters (json/list)'''
	frappe.has_permission(doc=frappe.get_doc(doctype, name), throw=True)
	meta = frappe.get_meta(doctype)

	links = frappe._dict(json.loads(links))

	items = []
	for group in links.transactions:
		items.extend(group.get('items'))

	out = []
	for d in items:
		if d in links.get('internal_links', {}):
			# internal link
			continue

		filters = get_filters_for(d)
		fieldname = links.get('non_standard_fieldnames', {}).get(d, links.fieldname)
		data = {'name': d}
		if filters:
			filters[fieldname] = name
			total = len(frappe.get_all(d, fields='name',
				filters=filters, limit=100, distinct=True, ignore_ifnull=True))
			data['open_count'] = total

		total = len(frappe.get_all(d, fields='name',
			filters={fieldname: name}, limit=100, distinct=True, ignore_ifnull=True))
		data['count'] = total
		out.append(data)

	out = {
		'count': out,
	}

	module = frappe.get_meta_module(doctype)
	if hasattr(module, 'get_timeline_data'):
		out['timeline_data'] = module.get_timeline_data(doctype, name)
	# print(out)
	return out