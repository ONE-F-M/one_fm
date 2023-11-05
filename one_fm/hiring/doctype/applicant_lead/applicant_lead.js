// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Applicant Lead', {
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
		else{
			frappe.db.get_value("Job Applicant", {"applicant_lead": frm.doc.name}, "name", function(r) {
				if(!r || !r.name){
					frm.add_custom_button(__("Create Job Applicant"), frm.events.make_job_applicant);
				}
			});
		}
	},
	make_job_applicant: function () {
		frappe.model.open_mapped_doc({
			method: "one_fm.hiring.doctype.applicant_lead.applicant_lead.make_job_applicant",
			frm: cur_frm
		})
	}
});
