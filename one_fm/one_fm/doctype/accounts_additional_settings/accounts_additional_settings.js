// Copyright (c) 2022, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accounts Additional Settings', {
	onload: function(frm) {
		set_options_for_assign_collection_officer_on_workflow_sate(frm);
	}
});

var set_options_for_assign_collection_officer_on_workflow_sate = function(frm) {
	frappe.call({
		method: "one_fm.one_fm.doctype.accounts_additional_settings.accounts_additional_settings.get_options_for_assign_collection_officer_on_workflow_sate",
		callback:function(r){
			console.log(r);
			if(r.message){
				r.message.forEach((item, i) => {
					frm.set_df_property('sales_invoice_workflow_sate_to_assign_collection_officer', "options", r.message);
					frm.refresh_field("sales_invoice_workflow_sate_to_assign_collection_officer");
				});
			}
		}
	});
};
