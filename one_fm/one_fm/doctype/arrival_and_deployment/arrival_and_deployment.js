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

		// Acknowledge Buttons for Pending Support Departments
		if (frm.doc.workflow_state === "Pending Support Departments") {
			let user = frappe.session.user;

			let add_ack_btn = (field, label) => {
				if (!frm.doc[field]) {
					frm.add_custom_button(__(`Acknowledge ${label}`), function() {
						frappe.call({
							method: "one_fm.one_fm.doctype.arrival_and_deployment.arrival_and_deployment.acknowledge_department",
							args: { docname: frm.doc.name, field: field },
							callback: function(r) {
								if (!r.exc) {
									frappe.show_alert({message:__('Acknowledged Successfully'), indicator:'green'});
									frm.reload_doc();
								}
							}
						});
					}).addClass("btn-primary");
				}
			};

			add_ack_btn("transport_acknowledged", "Transportation");
			add_ack_btn("finance_acknowledged", "Finance");
			add_ack_btn("general_services_acknowledged", "General Services");
			add_ack_btn("warehouse_acknowledged", "Warehouse");
		}
	},
	
	validate: function(frm) {
		if (frappe.session.user === frm.doc.transportation_manager && !frm.doc.pickup_contact) {
			frappe.throw("As the Transportation Manager, you must enter the Pickup Contact Person.");
		}
	},
	
	before_workflow_action: function(frm) {
		if (frappe.selected_workflow_action === "Submit to Onboarding") {
			if (!frm.doc.arrival_date || !frm.doc.arrival_time || !frm.doc.ticket_attachment) {
				frappe.throw("Please ensure Arrival Date, Arrival Time, and Ticket Attachment are filled before submitting to Onboarding.");
			}
		}

		if (frappe.selected_workflow_action === "Mark as Joined") {
			if (!frm.doc.pickup_contact) {
				frappe.throw("Please enter the Pickup Contact Person before proceeding.");
			}
			if (!frm.doc.transport_acknowledged || !frm.doc.finance_acknowledged || !frm.doc.general_services_acknowledged || !frm.doc.warehouse_acknowledged) {
				frappe.throw("Cannot mark as Joined. All departments must acknowledge first.");
			}
		}

		if (frappe.selected_workflow_action === "Did Not Arrive") {
			if (!frm.doc.recruiter) {
				frappe.throw("Please enter the Recruiter before notifying them that the candidate did not arrive.");
			}
		}
	}
});
