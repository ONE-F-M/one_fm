// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('PAM Visa', {
	candidate_country_process: function(frm) {
		frappe.call({
			method: "get_applicant_data",
			doc: frm.doc,
			callback: function(r) {
				if(r.message){
					cur_frm.refresh_fields()
				}
			},
			freeze: true,
			freeze_message: __('Fetching Data..')
		});
	},
	pam_visa_submitted: function(frm) {
		if(frm.doc.pam_visa_submitted==1){
			frm.set_value("grd_operator_status", 'Done');
			frm.set_value("pam_visa_submitted_date_time", frappe.datetime.now_datetime());
		}
		else{
			frm.set_value("grd_operator_status", 'Pending');
			frm.set_value("pam_visa_submitted_date_time", '');
		}
	},
	pam_visa_submitted_supervisor: function(frm) {
		if(frm.doc.pam_visa_submitted_supervisor==1){
			frm.set_value("pam_visa_submitted_supervisor_date_time", frappe.datetime.now_datetime());
		}
		else{
			frm.set_value("pam_visa_submitted_supervisor_date_time", '');
		}
	},
	upload_tasriah_submitted: function(frm) {
		if(frm.doc.upload_tasriah_submitted==1){
			frm.set_value("upload_tasriah_status", 'Done');
		}
		else{
			frm.set_value("upload_tasriah_status", 'Pending');
		}
	},
	status: function(frm) {
		if(frm.doc.status=='Apporved'){
			frm.set_value("visa_application_rejected", false);
		}
	},
	pam_visa_approval_submitted: function(frm) {
		if(frm.doc.pam_visa_approval_submitted==1){
			frm.set_value("pam_visa_approval_status", 'Done');
		}
		else{
			frm.set_value("pam_visa_approval_status", 'Pending');
		}
	},
	upload_original_visa_submitted: function(frm) {
		if(frm.doc.upload_original_visa_submitted==1){
			frm.set_value("upload_original_visa_status", 'Done');
		}
		else{
			frm.set_value("upload_original_visa_status", 'Pending');
		}
	}
});
