frappe.ui.form.on('Purchase Order', {
	setup: function(frm) {
		if(frappe.user.has_role("Purchase User")){
			frm.set_df_property('quoted_delivery_date', 'hidden', 0);
		} else {
			frm.set_df_property('quoted_delivery_date', 'hidden', 1);
		}
		// frm.set_df_property('quoted_delivery_date', 'hidden', (frm.doc.docstatus==1 && frappe.user.has_role("Purchase User"))?false:true);
	},
	refresh: function(frm) {
		hide_tax_fields(frm);
		set_signed_letter_head(frm);
		hide_subscription_section(frm);
		approve_if_signed(frm);
		set_field_property_for_documents(frm);
		set_field_property_for_other_documents(frm);
        console.log("All is well my bro")
	},
	set_warehouse: function(frm){
		if(frm.doc.set_warehouse){
			frappe.call({
				method: 'one_fm.purchase.utils.get_warehouse_contact_details',
				args: {'warehouse': frm.doc.set_warehouse},
				callback: function(r) {
					var contact = r.message;
					if(contact){
						if(contact[0]){
							frm.set_value('one_fm_warehouse_contact_person', contact[0].contact_display);
							frm.set_value('one_fm_contact_person_email', contact[0].contact_email);
							frm.set_value('one_fm_contact_person_phone', contact[0].contact_mobile);
						}
						frm.set_value('one_fm_warehouse_location', contact[1]);
					}
				}
			});
		}
	},
	one_fm_type_of_purchase: function(frm) {
		set_field_property_for_documents(frm);
	},
	one_fm_other_documents_required: function(frm) {
		set_field_property_for_other_documents(frm);
	}
});

var set_signed_letter_head = function(frm) {
	if(frm.doc.workflow_state == "Approved"){
		frm.set_value('letter_head', 'Authorization Signature');
	}
};

var approve_if_signed = function(frm){
	if(frm.doc.workflow_state == "Approved"){
		if(frm.doc.authority_signature == undefined){
			frappe.throw(__('Please Sign the form to Accept the Request'))
		};
	}
};

var set_field_property_for_other_documents = function(frm) {
	if(frm.doc.one_fm_other_documents_required && frm.doc.one_fm_other_documents_required == 'Yes'){
		frm.set_df_property('one_fm_details_of_other_documents', 'reqd', true);
	}
	else{
		frm.set_df_property('one_fm_details_of_other_documents', 'reqd', false);
		frm.set_value('one_fm_details_of_other_documents', '');
	}
};

var set_field_property_for_documents = function(frm) {
	if(frm.doc.one_fm_type_of_purchase && frm.doc.one_fm_type_of_purchase == "Import"){
		frm.set_df_property('one_fm_certificate_of_origin_required', 'reqd', true);
		frm.set_df_property('one_fm_other_documents_required', 'reqd', true);
	}
	else{
		frm.set_df_property('one_fm_certificate_of_origin_required', 'reqd', false);
		frm.set_df_property('one_fm_other_documents_required', 'reqd', false);
		frm.set_value('one_fm_certificate_of_origin_required', '');
		frm.set_value('one_fm_other_documents_required', '');
	}
};

var hide_tax_fields = function(frm) {
	let field_list = ['tax_category', 'section_break_52', 'taxes_and_charges', 'taxes', 'sec_tax_breakup', 'totals'];
	field_list.forEach((field, i) => {
		frm.set_df_property(field, 'hidden', true);
	});
};

var hide_subscription_section = function(frm) {
	frm.set_df_property('subscription_section', 'hidden', true);
};


frappe.ui.form.on('Payment Schedule', {
	refresh(frm) {
		// your code here
	},
	payment_term: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.payment_term == 'Purchase Receipt based') {
		    console.log("here")
			frm.set_df_property('payment_schedule', 'read_only', true);
		}
		else{
			frm.set_df_property('payment_schedule', 'read_only', false);
		}
	}
})