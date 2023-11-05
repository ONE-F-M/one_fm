// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accommodation Asset and Consumable', {
	refresh: function(frm) {
		set_filters(frm);
	},
	employee: function(frm) {
		set_assets_and_consumables_details(frm);
	},
	type: function(frm) {
		set_assets_and_consumables_details(frm);
	}
});

var set_assets_and_consumables_details = function(frm) {
	frm.clear_table('assets');
	frm.clear_table('consumables');
	if(frm.doc.employee && frm.doc.type && frm.doc.designation){
		frappe.call({
			doc: frm.doc,
			method: 'set_assets_and_consumables_details',
			callback: function(r) {
				if(!r.exc){
					frm.refresh_fields()
				}
			},
			freeze: true,
			freeze_message: __('Fetching Uniform Details..')
		});
	}
};

var set_filters = function(frm) {
	frm.set_query("asset", "assets", function(doc, cdt, cdn) {
		var child = locals[cdt][cdn];
		return {
			filters: {'item_code': child.asset_item}
		}
	});
};
