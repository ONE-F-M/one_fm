// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('PAM Visa', {
	candidate_country_process: function(frm) {

        frappe.call({
            method: "get_applicant_data",
            doc: cur_frm.doc,
            callback: function(r) { 
                if(r.message){
                    cur_frm.refresh_fields()
                }
            }
        });

	},
	pam_visa_submitted: function(frm) {
		if(cur_frm.doc.pam_visa_submitted==1){
			frm.set_value("grd_operator_status", 'Done')
		}
	},
	upload_tasriah_submitted: function(frm) {
		if(cur_frm.doc.upload_tasriah_submitted==1){
			frm.set_value("upload_tasriah_status", 'Done')
		}
	},
	status: function(frm) {
		if(cur_frm.doc.status=='Apporved'){
			frm.set_value("visa_application_rejected", 0)
		}
	},
	pam_visa_approval_submitted: function(frm) {
		if(cur_frm.doc.pam_visa_approval_submitted==1){
			frm.set_value("pam_visa_approval_status", 'Done')
		}
	},
	upload_original_visa_submitted: function(frm) {
		if(cur_frm.doc.upload_original_visa_submitted==1){
			frm.set_value("upload_original_visa_status", 'Done')
		}
	}

});
