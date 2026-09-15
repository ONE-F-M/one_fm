// Copyright (c) 2020, ONE FM and contributors
// For license information, please see license.txt

// WI-002096: the button that opens the next document in the legal sequence, once this one is
// complete. Shown only for the classifications that have a next step. The next document is
// found by the Preparation and employee this one carries, which is what pairs them: a
// Preparation opens one of each per employee.
var set_next_step_button = function(frm, next_doctype, classifications, classification_field){
	if(frm.doc.workflow_state !== 'Completed'){
		return;
	}
	if(!classifications.includes(frm.doc[classification_field])){
		return;
	}
	if(!frm.doc.preparation || !frm.doc.employee){
		return;
	}

	frm.add_custom_button(__('Go to {0}', [__(next_doctype)]), function(){
		frappe.db.get_value(
			next_doctype,
			{preparation: frm.doc.preparation, employee: frm.doc.employee, docstatus: ['!=', 2]},
			'name',
			(r) => {
				if(r && r.name){
					frappe.set_route('Form', next_doctype, r.name);
				} else {
					frappe.msgprint({
						title: __('Nothing to open'),
						message: __('No {0} was opened for this candidate.', [__(next_doctype)]),
						indicator: 'orange'
					});
				}
			}
		);
	}).addClass('btn-primary');
};

frappe.ui.form.on('Residency', {
	refresh(frm){
		// WI-002096 widens this from Transfer alone to every residency that has a civil ID
		// behind it - an Extend does not, so it gets no button - and pairs on the Preparation
		// rather than on a civil ID, which after a Damj merge is not the number the PACI was
		// opened under.
		set_next_step_button(frm, 'PACI', ['Renewal', 'First Time', 'Transfer'], 'category');
	},
	onload: function(frm) {
		// set_employee_details(frm);
		if(frm.doc.__islocal){
			frappe.call({
				method:"frappe.client.get_value",
				args: {
					doctype:"PAM File",
					filters: {
						name:"ONE FM Hawally Private File"
					},
					fieldname:["pam_file_number","company_unified_number","pam_file_governorate_arabic"]
				}, 
				callback: function(r) { 
			
					frm.set_value('company_pam_file_number', r.message.pam_file_number);
					frm.set_value('company_centralized_number', r.message.company_unified_number);
					frm.set_value('governorate', r.message.pam_file_governorate_arabic);
				}
			})
			frappe.call({
				method:"frappe.client.get_value",
				args: {
					doctype:"MOCI License",
					filters: {
						name:"ONE Facilities Management Company W.L.L."
					},
					fieldname:["license_trade_name_arabic","street","building"]
				}, 
				callback: function(r) { 
				// set the returned value in a field
					frm.set_value('company_trade_name', r.message.license_trade_name_arabic);
					frm.set_value('company_street_name', r.message.street);
					frm.set_value('company_building_name', r.message.building);
				}
			})
			frappe.call({
				method:"frappe.client.get_value",
				args: {
					doctype:"Company",
					filters: {
						name:"ONE Facilities Management"
					},
					fieldname:["email","phone_no"]
				}, 
				callback: function(r) { 
			
					// set the returned value in a field
					frm.set_value('company_email_id', r.message.email);
					frm.set_value('company_contact_number', r.message.phone_no);
				}
			})
			frappe.call({
				method:"frappe.client.get_value",
				args: {
					doctype:"PACI Number",
					filters: {
						name:"ONE Facilities Management"
					},
					fieldname:["paci_number","area_name","block"]
				}, 
				callback: function(r) { 
					// set the returned value in a field
					frm.set_value('paci_number', r.message.paci_number);
					frm.set_value('company_location', r.message.area_name);
					frm.set_value('company_block_number', r.message.block);	
				}
			})
		}
    },
    employee: function(frm){
        set_employee_details(frm);
    },
	invoice_attachment: function(frm){
		set_invoice_attachment_date(frm);
	},
	residency_attachment: function(frm){
		set_residency_attachment_date(frm);
	},
	new_residency_expiry_date: function(frm){
		set_new_residency_expiry_date_update_time(frm);
	},
	upload_damj_letter: function(frm){
		set_attachment_timestamp(frm, 'upload_damj_letter', 'upload_damj_letter_on');
	},
	upload_residency_fine_payment_receipt: function(frm){
		set_attachment_timestamp(frm, 'upload_residency_fine_payment_receipt', 'upload_residency_fine_payment_receipt_on');
	}
});
// WI-002022: stamp when an exception document went up, and clear the stamp if the file is
// removed. One helper for both pairs - the three older stamps below each carry their own
// copy of this same logic.
var set_attachment_timestamp = function(frm, attach_field, timestamp_field){
	if(frm.doc[attach_field] && !frm.doc[timestamp_field]){
		frm.set_value(timestamp_field, frappe.datetime.now_datetime());
	}
	if(!frm.doc[attach_field] && frm.doc[timestamp_field]){
		frm.set_value(timestamp_field, null);
	}
};
var set_employee_details = function(frm){
    if(frm.doc.employee){
        frappe.call({
            method:"frappe.client.get_value",//api calls
            args: {
                doctype:"Employee",
                filters: {
                name: frm.doc.employee
                },
                fieldname:["one_fm_first_name_in_arabic","one_fm_second_name_in_arabic","one_fm_third_name_in_arabic","one_fm_last_name_in_arabic",
				"first_name","middle_name","one_fm_third_name","last_name","one_fm_civil_id","designation","place_of_issue",
				"gender","date_of_birth","passport_number","one_fm_passport_type","date_of_issue","valid_upto","one_fm_pam_designation","one_fm_nationality","company_email"]
            }, 
            callback: function(r) { 
        
                // set the returned value in a field
                frm.set_value('first_name_arabic', r.message.one_fm_first_name_in_arabic);
                frm.set_value('second_name_arabic', r.message.one_fm_second_name_in_arabic);
                frm.set_value('third_name_arabic', r.message.one_fm_third_name_in_arabic);
                frm.set_value('last_name_arabic', r.message.one_fm_last_name_in_arabic);
                frm.set_value('first_name_english',r.message.first_name);
                frm.set_value('second_name_english', r.message.middle_name);
                frm.set_value('third_name_english', r.message.one_fm_third_name);
                frm.set_value('last_name_english',r.message.last_name);
                frm.set_value('one_fm_civil_id', r.message.one_fm_civil_id);
                frm.set_value('designation', r.message.designation);
                frm.set_value('place_of_birth', r.message.place_of_issue);
                frm.set_value('gender',r.message.gender);
                frm.set_value('birth_date', r.message.date_of_birth);
                frm.set_value('passport_number', r.message.passport_number);
                frm.set_value('passport_type',r.message.one_fm_passport_type);
                frm.set_value('passport_issue_date', r.message.date_of_issue);
                frm.set_value('passport_expiry_date', r.message.valid_upto);
                frm.set_value('pam_designation', r.message.one_fm_pam_designation);
                frm.set_value('nationality', r.message.one_fm_nationality);
                frm.set_value('company_email_id', r.message.company_email);
            }
        })
    }
};
var set_invoice_attachment_date = function(frm)
{//2
	if(((frm.doc.invoice_attachment) && (!frm.doc.invoice_attachment_date)))
	{
		frm.set_value('invoice_attachment_date',frappe.datetime.now_datetime())
	}if(((!frm.doc.invoice_attachment) && (frm.doc.invoice_attachment_date)))
	{
		frm.set_value('invoice_attachment_date',null)
	}
};
var set_residency_attachment_date = function(frm)
{//3
	if((frm.doc.residency_attachment) && (!frm.doc.residency_attachment_date))
	{
		frm.set_value('residency_attachment_date',frappe.datetime.now_datetime())
	}if((!frm.doc.residency_attachment) && (frm.doc.residency_attachment_date))
	{
		frm.set_value('residency_attachment_date',null)
	}
};
var set_new_residency_expiry_date_update_time = function(frm)
{//4
	if(((frm.doc.new_residency_expiry_date != null) && (!frm.doc.new_residency_expiry_date_update_time)))
	{	
		frm.set_value('new_residency_expiry_date_update_time',frappe.datetime.now_datetime())
	}if(((frm.doc.new_residency_expiry_date == null) && (frm.doc.new_residency_expiry_date_update_time)))
	{	
		frm.set_value('new_residency_expiry_date_update_time',null)
	}
};