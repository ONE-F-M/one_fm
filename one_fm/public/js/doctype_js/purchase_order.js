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
		set_field_property_for_documents(frm);
		set_field_property_for_other_documents(frm);
	},
	status: function(frm){
		confirm_accept_approve_purchase_order(frm);
	},
	confirm_accept_approve_purchase_order: function(frm) {
		frappe.confirm(
			__('A one time code will be sent to you for verification in order to use your signature for approval. Do You Want to {0} this Purchase Order?', [msg_status]),
			function(){
				// Yes
				var doctype = frm.doc.doctype
				var document_name = frm.doc.name
				var d = new Date();
				var current_datetime_string = d.getUTCFullYear() +"/"+ (d.getUTCMonth()+1) +"/"+ d.getUTCDate() + " " + d.getUTCHours() + ":" + d.getUTCMinutes() + ":" + d.getUTCSeconds();
				frappe.xcall('one_fm.utils.send_verification_code', {doctype, document_name, current_datetime_string})
					.then(res => {
						console.log(res);
					}).catch(e => {
						console.log(e);
					})
				var d = new frappe.ui.Dialog({
					title : __("Approval verification"),
					fields : [
						{
							fieldtype: "Int",
							label: "Enter verification code sent to your email address",
							fieldname: "verification_code",
							reqd: 1,
							onchange: function(){
								let code = d.get_value('verification_code')
								if (!is_valid_verification_code(code)){frappe.throw(__("Invalid verification code."))}
							}
						},
						{
							fieldtype: "Button", 
							label: "Resend code", 
							fieldname: "resend_verification_code"
						},
					],
					primary_action_label: __("Submit"),
					primary_action: function(){
						var verification_code = d.get_value('verification_code');
						frappe.xcall('one_fm.utils.verify_verification_code', {doctype, document_name, verification_code})
							.then(res => {
								if (res){
									d.hide()
									frm.events.accept_approve_purchase_order(frm, status, false);
								} else{
									frappe.msgprint(__("Incorrect verification code. Please try again."));
								}
							})
					},
				});
				d.fields_dict.resend_verification_code.input.onclick = function() {
					frappe.xcall('one_fm.utils.send_verification_code', {doctype, document_name, current_datetime_string})
					.then(res => {
						console.log(res);
					}).catch(e => {
						console.log(e);
					})
				}
				d.show();
			},
			function(){} // No
		);
	},
	accept_approve_purchase_order: function(frm, status, reason_for_rejection) {
		frappe.call({
			doc: frm.doc,
			method: 'one_fm.purchase.utils.accept_approve_purchase_order',
			args: {doc: frm.doc},
			callback(r) {
				if (!r.exc) {
					frm.reload_doc();
				}
			},
			freeze: true,
			freeze_message: __('Updating the Request..!')
		});
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
var confirm_accept_approve_purchase_order= function(frm) {
	if(frm.doc.workflow_state == "Approved"){
		console.log("All is well my bro")
		frappe.confirm(
			__('A one time code will be sent to you for verification in order to use your signature for approval. Do You Want to {0} this Purchase Order?', [msg_status]),
			function(){
				// Yes
				var doctype = frm.doc.doctype
				var document_name = frm.doc.name
				var d = new Date();
				var current_datetime_string = d.getUTCFullYear() +"/"+ (d.getUTCMonth()+1) +"/"+ d.getUTCDate() + " " + d.getUTCHours() + ":" + d.getUTCMinutes() + ":" + d.getUTCSeconds();
				frappe.xcall('one_fm.utils.send_verification_code', {doctype, document_name, current_datetime_string})
					.then(res => {
						console.log(res);
					}).catch(e => {
						console.log(e);
					})
				var d = new frappe.ui.Dialog({
					title : __("Approval verification"),
					fields : [
						{
							fieldtype: "Int",
							label: "Enter verification code sent to your email address",
							fieldname: "verification_code",
							reqd: 1,
							onchange: function(){
								let code = d.get_value('verification_code')
								if (!is_valid_verification_code(code)){frappe.throw(__("Invalid verification code."))}
							}
						},
						{
							fieldtype: "Button", 
							label: "Resend code", 
							fieldname: "resend_verification_code"
						},
					],
					primary_action_label: __("Submit"),
					primary_action: function(){
						var verification_code = d.get_value('verification_code');
						frappe.xcall('one_fm.utils.verify_verification_code', {doctype, document_name, verification_code})
							.then(res => {
								if (res){
									d.hide()
									accept_approve_purchase_order(frm);
								} else{
									frappe.msgprint(__("Incorrect verification code. Please try again."));
								}
							})
					},
				});
				d.fields_dict.resend_verification_code.input.onclick = function() {
					frappe.xcall('one_fm.utils.send_verification_code', {doctype, document_name, current_datetime_string})
					.then(res => {
						console.log(res);
					}).catch(e => {
						console.log(e);
					})
				}
				d.show();
			},
			function(){} // No
		);
	}
};
var accept_approve_purchase_order = function(frm) {
	frappe.call({
		doc: frm.doc,
		method: 'one_fm.purchase.utils.accept_approve_purchase_order',
		args: {doc: frm.doc},
		callback(r) {
			if (!r.exc) {
				frm.reload_doc();
			}
		},
		freeze: true,
		freeze_message: __('Updating the Request..!')
	});
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

function is_valid_verification_code(code){
	const code_expression = /^\d{6}(\s*,\s*\d{6})*$/;
	if (code_expression.test(code))  return true;

	return false;
}