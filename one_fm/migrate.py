import frappe, os, json
from frappe.modules.utils import *


def sync_customizations_for_doctype(data, folder):
	'''Sync doctype customzations for a particular data set'''
	from frappe.core.doctype.doctype.doctype import validate_fields_for_doctype

	doctype = data['doctype']
	update_schema = False

	def sync(key, custom_doctype, doctype_fieldname):
		doctypes = list(set(map(lambda row: row.get(doctype_fieldname), data[key])))

		# sync single doctype exculding the child doctype
		def sync_single_doctype(doc_type):
			def _insert(data):
				if data.get(doctype_fieldname) == doc_type:
					data['doctype'] = custom_doctype
					doc = frappe.get_doc(data)
					doc.db_insert()

			if custom_doctype != 'Custom Field':
				frappe.db.sql('delete from `tab{0}` where `{1}` =%s'.format(
					custom_doctype, doctype_fieldname), doc_type)

				for d in data[key]:
					_insert(d)

			else:
				for d in data[key]:
					field = frappe.db.get_value("Custom Field", {"dt": doc_type, "fieldname": d["fieldname"]})
					if not field:
						d["owner"] = "Administrator"
						_insert(d)
					else:
						custom_field = frappe.get_doc("Custom Field", field)
						custom_field.flags.ignore_validate = True
						custom_field.update(d)
						custom_field.db_update()

		for doc_type in doctypes:
			# only sync the parent doctype and child doctype if there isn't any other child table json file
			if doc_type == doctype or not os.path.exists(os.path.join(folder, frappe.scrub(doc_type)+".json")):
				sync_single_doctype(doc_type)

	if data['custom_fields']:
		sync('custom_fields', 'Custom Field', 'dt')
		update_schema = True

	if data['property_setters']:
		sync('property_setters', 'Property Setter', 'doc_type')

	if data.get('custom_perms'):
		sync('custom_perms', 'Custom DocPerm', 'parent')

	print('Updating customizations for {0}'.format(doctype))
	# validate_fields_for_doctype(doctype)

	if update_schema and not frappe.db.get_value('DocType', doctype, 'issingle'):
		frappe.db.updatedb(doctype)


def after_migrate():
    # sync customizations
    folder = frappe.get_app_path('one_fm', 'One Fm', 'custom')
    print(folder)
    if os.path.exists(folder):
        for fname in os.listdir(folder):
            if ((fname.endswith('.json')) and (fname=='employee.json')):
                with open(os.path.join(folder, fname), 'r') as f:
                    data = json.loads(f.read())
                    sync_customizations_for_doctype(data, folder)
    # sync_customizations('one_fm')
