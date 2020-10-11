// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Uniform', {
	refresh: function(frm) {
		if(frm.doc.type == "Return"){
			frappe.meta.get_docfield("Employee Uniform Item", 'returned', frm.doc.name).hidden = true;
		}
	},
	employee: function(frm) {
		set_uniform_details(frm);
		set_filters(frm);
	},
	type: function(frm) {
		set_uniform_details(frm);
	},
	get_item_data: function(frm, item) {
		if (!item.item || frm.doc.type=='Return') return;
		frm.call({
			method: "erpnext.stock.get_item_details.get_item_details",
			child: item,
			args: {
				args: {
					item_code: item.item,
					doctype: frm.doc.doctype,
					buying_price_list: frappe.defaults.get_default('buying_price_list'),
					currency: frappe.defaults.get_default('Currency'),
					name: frm.doc.name,
					qty: item.quantity || 1,
					company: frm.doc.company,
					conversion_rate: 1,
					plc_conversion_rate: 1
				}
			},
			callback: function(r) {
				const d = item;
				if(!r.exc) {
					d['rate'] = r.message.price_list_rate;
					frm.refresh_field('uniforms')
				}
			}
		});
	},
});

frappe.ui.form.on('Employee Uniform Item', {
	uniforms_add: function(frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if(frm.doc.issued_on && frm.doc.type == "Issue") {
			row.expire_on = frappe.datetime.add_months(frm.doc.issued_on, 12);
			refresh_field("expire_on", cdn, "uniforms");
		}
	},
	item: function(frm, doctype, name) {
		const item = locals[doctype][name];
		frm.events.get_item_data(frm, item);
	},
});

var set_filters = function(frm) {
	if(frm.doc.type == "Return"){
		frm.set_query("item", "uniforms", function() {
			return {
				query: "one_fm.uniform_management.doctype.employee_uniform.employee_uniform.issued_items_not_returned",
				filters: {'employee': frm.doc.employee}
			}
		});
	}
};

var set_uniform_details = function(frm) {
	frm.clear_table('uniforms');
	if(frm.doc.employee && frm.doc.type && frm.doc.designation){
		frappe.call({
			doc: frm.doc,
			method: 'set_uniform_details',
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
