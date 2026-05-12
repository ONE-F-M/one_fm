// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Overseas Remedical", {

	refresh: function(frm) {
		// Override dashboard link routing for sibling tracking documents
		if (frm.dashboard) {
			frm.dashboard.open_document_list = function($link, show_open) {
				let doctype = $link.attr("data-doctype");
				if (doctype && doctype !== "Candidate Country Process") {
					frappe.route_options = {
						"candidate_country_process": frm.doc.candidate_country_process
					};
				} else {
					frappe.route_options = {
						"name": frm.doc.candidate_country_process
					};
				}
				frappe.set_route("List", doctype);
			};
		}
	},
	
	appointment_status: function(frm) {
		update_actual_remedical_status(frm);
	},
	
	appointment_date: function(frm) {
		update_actual_remedical_status(frm);
	}

});

function update_actual_remedical_status(frm) {
	if (frm.doc.appointment_status === "Booked" && frm.doc.appointment_date) {
		if (frm.doc.status === "Yet to apply") {
			frm.set_value("status", "In process");
		}
	}
}
