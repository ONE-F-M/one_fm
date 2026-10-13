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
	},
	
	validate: function(frm) {
		// client side validation
	},
	
	before_workflow_action: function(frm) {
		if (frappe.selected_workflow_action === "Submit to Onboarding") {
			if (!frm.doc.arrival_date) {
				frappe.throw(__("Please ensure Arrival Date is filled before submitting to Onboarding."));
			}
			if (frm.doc.candidate_country_process) {
				if (!frm.doc.ticket_attachment) {
					frappe.throw(__("Please attach the Ticket for Overseas hires before submitting to Onboarding."));
				}
			}
		}

		if (["Arrange Pick Up", "Arrived", "Did Not Arrive"].includes(frappe.selected_workflow_action)) {
			let is_overseas = !!frm.doc.candidate_country_process;
			if (is_overseas && frappe.session.user !== frm.doc.transportation_manager && !frappe.user.has_role("System Manager")) {
				frappe.throw(__("Only the Transportation Manager named on this arrival can mark whether the candidate arrived."));
			}
		}

		if (frappe.selected_workflow_action === "Did Not Arrive") {
			if (!frm.doc.recruiter) {
				frappe.throw(__("Please enter the Recruiter before notifying them that the candidate did not arrive."));
			}
		}
	}
});
