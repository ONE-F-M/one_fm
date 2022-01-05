// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quotation From Supplier', {
	refresh: function(frm) {
		frm.set_query("supplier", function() {
			return {
				query: "one_fm.purchase.utils.get_supplier_list",
				filters: {'request_for_quotation': frm.doc.request_for_quotation}
			}
		});
	},
	request_for_quotation: function(frm) {
		set_items(frm);
	}
});

frappe.ui.form.on('Quotation From Supplier Item', {
	rate: function(frm, cdt, cdn) {
		calculate_rate_and_amount(frm, cdt, cdn);
	},
	qty: function(frm, cdt, cdn) {
		calculate_rate_and_amount(frm, cdt, cdn);
	}
});

var calculate_rate_and_amount = function(frm, cdt, cdn) {
	var child = locals[cdt][cdn];
	if(child.rate && child.qty){
		frappe.model.set_value(cdt, cdn, 'amount', child.rate*child.qty);
	}
};

var set_items = function(frm) {
	frm.clear_table('items');
	if(frm.doc.request_for_quotation){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Request for Supplier Quotation',
				filters: {name: frm.doc.request_for_quotation}
			},
			callback: function(r) {
				if(r && r.message){
					var rfq = r.message;
					frm.doc.request_for_material = rfq.request_for_material;
					if(rfq.items){
						rfq.items.forEach((r_item, i) => {
							var item = frm.add_child('items');
							item.item_name = r_item.item_name
							item.description = r_item.description
							item.qty = r_item.qty
							item.uom = r_item.uom
						});
					}
				}
				frm.refresh_field('items');
			}
		});
	}
};
