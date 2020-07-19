// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Candidate Country Process', {
    applicant: function(frm) {

        frappe.call({
            method: "get_candidate_passport_number",
            doc: cur_frm.doc,
            callback: function(r) { 
                if(r.message){
                    frm.set_value("candidate_passport_number", r.message)
                }else{
                    frm.set_value("candidate_passport_number", )
                }
            }
        });

    },
	agency_country_process: function(frm) {

		if(cur_frm.doc.agency_country_process){
            cur_frm.doc.agency_process_details = []
            frappe.model.with_doc("Agency Country Process", frm.doc.agency_country_process, function() {
                var tabletransfer= frappe.model.get_doc("Agency Country Process", frm.doc.agency_country_process)
                frm.doc.agency_process_details = []
                frm.refresh_field("agency_process_details");
                $.each(tabletransfer.agency_process_details, function(index, row){
                    var d = frm.add_child("agency_process_details");
                    d.process_name = row.process_name;
                    d.responsible = row.responsible;
                    d.total_duration = row.total_duration;
                    frm.refresh_field("agency_process_details");
                });
            })
        }
	}
});
