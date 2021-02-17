// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Head Hunt', {
	lead_owner_type: function(frm) {
		frm.set_value('lead_owner', '');
		if(frm.doc.lead_owner_type == 'Internal'){
			frm.set_value('lead_owner_dt', 'User');
		}
		else if(frm.doc.lead_owner_type == 'External'){
			frm.set_value('lead_owner_dt', 'Supplier');
		}
	},
	refresh: function(frm) {
		if(frm.is_new()){
			frm.set_value('lead_owner_dt', 'User');
		}
		// frm.add_custom_button(__("Create Applicant Lead"), function() {
		// 	frm.events.make_applicant_lead(frm)
		// });
	},
	make_applicant_lead: function (frm) {
		frappe.call({
			method: 'make_applicant_lead',
			doc: frm.doc,
			callback: function (r) {
				if(!r.exc){
					frappe.show_alert(__("Applicant Leads Created."));
				}
			},
			freeze: true,
			freeze_message: __("Creating Applicant Lead ...!")
		});
	}
});
