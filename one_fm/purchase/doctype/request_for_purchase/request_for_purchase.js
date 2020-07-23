// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Request for Purchase', {
	refresh: function(frm) {
		frm.events.make_custom_buttons(frm);
		if(frm.doc.docstatus == 1){
			frm.set_df_property('status', 'read_only', false);
		}
		if(frm.is_new() || frm.doc.docstatus != 1){
			frm.set_df_property('items_to_order', 'hidden', true);
		}
		else{
			frm.set_df_property('items_to_order', 'hidden', false);
		}
	},
	status: function(frm) {
		if(frm.doc.status && frm.doc.status == 'Rejected'){
			frm.set_df_property('reason_for_rejection', 'reqd', true);
		}
		else{
			frm.set_df_property('reason_for_rejection', 'reqd', false);
		}
	},
	make_custom_buttons: function(frm) {
		if (frm.doc.docstatus == 1){
			if(frm.doc.status == 'Draft') {
				frm.add_custom_button(__("Request for Quotation"),
					() => frm.events.make_request_for_quotation(frm), __('Create'));

				frm.add_custom_button(__("Compare Quotations"),
					() => frm.events.make_quotation_comparison_sheet(frm));
			}
			if(frm.doc.status == 'Approved'){
				frm.add_custom_button(__("Purchase Order"),
					() => frm.events.make_purchase_order(frm), __('Create'));
			}
		}
	},
	make_request_for_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "one_fm.purchase.doctype.request_for_purchase.request_for_purchase.make_request_for_quotation",
			frm: frm,
			run_link_triggers: true
		});
	},
	make_quotation_comparison_sheet: function(frm) {
		frappe.model.open_mapped_doc({
			method: "one_fm.purchase.doctype.request_for_purchase.request_for_purchase.make_quotation_comparison_sheet",
			frm: frm,
			run_link_triggers: true
		});
	},
	make_purchase_order: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'make_purchase_order_for_quotation',
			callback: function(data) {
				if(!data.exc){
					frm.reload_doc();
					frappe.show_alert({
						message: "Purchase Order Created",
						indicator: "green"
					});
				}
			},
			freeze: true,
			freeze_message: "Creating Purchase Order"
		})
	}
});
