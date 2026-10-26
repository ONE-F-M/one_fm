// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Arrival and Deployment", {

	refresh: function(frm) {
		// Override dashboard link routing for sibling tracking documents
		if (frm.dashboard) {
			frm.dashboard.open_document_list = function($link, show_open) {
				let doctype = $link.attr("data-doctype");
				if (doctype === "Job Applicant") {
					frappe.set_route("Form", "Job Applicant", frm.doc.job_applicant);
					return;
				}
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
		
		// Hide the ticket and pickup details for Local Hires (no Candidate Country Process)
		let is_local = !frm.doc.candidate_country_process;
		frm.toggle_display([
			'section_break_flight',
			'ticket_attachment'
		], !is_local);
	}
});
