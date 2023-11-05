// Copyright (c) 2022, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accounts Additional Settings', {
	onload: function(frm) {
		set_options_for_assign_collection_officer_on_workflow_sate(frm);
		show_create_role_button(frm);
	},
	assign_collection_officer_to_sales_invoice_on_workflow_state: function(frm) {
		show_create_role_button(frm);
	},
	create_collection_officer_role: function(frm) {
		frappe.call({
			method: 'one_fm.one_fm.utils.create_role_if_not_exists',
			args: {'roles': ['Collection Officer']},
			callback: function(r) {
				if(!r.exc){
					frm.reload_doc();
				}
			},
			freeze: true,
			freeze_message: __("Creating Collection Officer Role !!")
		});
	}
});

var show_create_role_button = function(frm) {
	frm.set_df_property('create_collection_officer_role', 'hidden', true);
	if(frm.doc.assign_collection_officer_to_sales_invoice_on_workflow_state && 'collection_officer_role_exists' in frm.doc.__onload){
		frm.set_df_property('create_collection_officer_role', 'hidden', frm.doc.__onload['collection_officer_role_exists']?true:false);
	}
};

var set_options_for_assign_collection_officer_on_workflow_sate = function(frm) {
	frappe.call({
		method: "one_fm.one_fm.doctype.accounts_additional_settings.accounts_additional_settings.get_options_for_assign_collection_officer_on_workflow_sate",
		callback:function(r){
			if(r.message){
				r.message.forEach((item, i) => {
					frm.set_df_property('sales_invoice_workflow_sate_to_assign_collection_officer', "options", r.message);
					frm.refresh_field("sales_invoice_workflow_sate_to_assign_collection_officer");
				});
			}
		}
	});
};
