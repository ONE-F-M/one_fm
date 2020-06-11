// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Change Request', {
	refresh: function(frm) {
		frm.set_query("document_type", function() {
			return {
				"filters": [
					["DocType", "name", "in", ["Operations Site", "Operations Post", "Operations Shift", "Project"]],
				]
			}
		});
	},
	document_type: function(frm){
		let doctype = frm.doc.document_type;
		let fields_map = []
		if (doctype) {
			frappe.model.with_doctype(doctype, () => {
				// get all date and datetime fields
				frappe.get_meta(doctype).fields.map(df => {
					if (['Int', 'Float', 'Currency', 'Data', 'Date', 'Datetime', 'Dynamic Link', 'Float', 'Int', 'Link', 'Read Only', 'Select', 'Text', 'Time'].includes(df.fieldtype)) {
						fields_map.push({label: df.label, value: df.fieldname});
						// window.fields_map.push({ [df.fieldname] : df.label});
					}
				});
				frm.set_df_property('list_of_fields', 'options', fields_map);
			});
		}
	},
	document_name: function(frm){
		get_current_value(frm);
	},
	list_of_fields: function(frm){
		get_current_value(frm);
	}
});

function get_current_value(frm){
	let {document_name, document_type, list_of_fields} = frm.doc;
	if(document_type !== undefined && document_type !== undefined && list_of_fields !== undefined){
		frappe.db.get_value(document_type, {"name": document_name}, list_of_fields)
		.then(result => {
			if(!result.exc){
				// console.log(result, list_of_fields);
				frappe.model.set_value(frm.doc.doctype, frm.doc.name, "current_value", result.message[`${list_of_fields}`]);
			}	
		})
	}
}