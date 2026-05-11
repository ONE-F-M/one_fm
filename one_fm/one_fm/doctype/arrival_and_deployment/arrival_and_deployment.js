// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Arrival And Deployment", {

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
	}
	},
	
	validate: function(frm) {
		if (frappe.session.user === frm.doc.transportation_manager && !frm.doc.pickup_contact) {
			frappe.throw("As the Transportation Manager, you must enter the Pickup Contact Person.");
		}
	},
	
	before_workflow_action: function(frm) {
		if (frappe.session.user === frm.doc.transportation_manager && !frm.doc.pickup_contact) {
			frappe.throw("Please enter the Pickup Contact Person before proceeding.");
			return false;
		}
	}
});
