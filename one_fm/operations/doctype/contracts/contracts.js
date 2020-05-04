// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Contractss', {
	client: function(frm) {
		let client = frm.doc.client;
		if(client != undefined){
			frm.set_query("project", function() {
				return {
					"filters": {
						"customer": client,
					}
				};
			});
		}
	}
});

frappe.ui.form.on('Contractss Addendum', {
	end_date: function(frm, cdt, cdn) {
		let doc = locals[cdt][cdn];
	},
	addendums_add: function(frm, cdt, cdn){
		let doc = locals[cdt][cdn];
		if(doc.idx == 1){
			frappe.model.set_value(doc.doctype, doc.name, "version", "1.0");
		}else{

		}
	}
});
