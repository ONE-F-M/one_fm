// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Candidate Country Process', {
	country_process: function(frm) {
		if(cur_frm.doc.country_process){
            cur_frm.doc.agency_process_details = []
            frappe.model.with_doc("Country Process", frm.doc.country_process, function() {
                var tabletransfer= frappe.model.get_doc("Country Process", frm.doc.country_process)
                frm.doc.agency_process_details = []
                frm.refresh_field("agency_process_details");
                $.each(tabletransfer.agency_process_details, function(index, row){
                    var d = frm.add_child("agency_process_details");
                    d.process_name = row.process_name;
                    d.responsible = row.responsible;
                    d.total_duration = row.total_duration;
                    d.attachement = row.attachement;
                    d.notes = row.notes;
                    frm.refresh_field("agency_process_details");
                });
            })
        }
	}
});
