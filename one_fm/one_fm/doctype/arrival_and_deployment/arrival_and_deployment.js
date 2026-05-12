// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Arrival and Deployment", {

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
		
		// Hide Flight and Transport details for Local Hires (no Candidate Country Process)
		let is_local = !frm.doc.candidate_country_process;
		frm.toggle_display([
			'arrival_time', 
			'transportation_manager', 
			'finance',
			'section_break_flight', 
			'flight_number', 
			'airline', 
			'ticket_attachment', 
			'arrival_airport', 
			'transport_acknowledged', 
			'finance_acknowledged'
		], !is_local);

		// Acknowledge Buttons for Pending Support Departments
		if (frm.doc.workflow_state === "Pending Support Departments") {
			let user = frappe.session.user;

			let add_ack_btn = (field, label, assignee_field) => {
				if (!frm.doc[field] && (user === frm.doc[assignee_field] || user === "Administrator")) {
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

			add_ack_btn("general_services_acknowledged", "General Services", "general_services");
			add_ack_btn("warehouse_acknowledged", "Warehouse", "warehouse");
            
            if (!is_local) {
                add_ack_btn("finance_acknowledged", "Finance", "finance");
                add_ack_btn("transport_acknowledged", "Transportation", "transportation_manager");
            }
		}

		frm.set_query("pickup_contact", function() {
			return {
				filters: {
					"designation": "Driver"
				}
			};
		});
	},
	
	validate: function(frm) {
		// client side validation
	},
	
	before_workflow_action: function(frm) {
		if (frappe.selected_workflow_action === "Submit to Onboarding") {
			if (!frm.doc.arrival_date) {
				frappe.throw("Please ensure Arrival Date is filled before submitting to Onboarding.");
			}
			if (frm.doc.candidate_country_process) {
				if (!frm.doc.arrival_time || !frm.doc.ticket_attachment || !frm.doc.flight_number || !frm.doc.airline || !frm.doc.arrival_airport) {
					frappe.throw("Please ensure Arrival Time, Flight Number, Airline, Ticket Attachment, and Arrival Airport are filled for Overseas hires before submitting to Onboarding.");
				}
			}
		}

		if (frappe.selected_workflow_action === "Mark as Joined" || frappe.selected_workflow_action === "Did Not Arrive") {
			let is_overseas = !!frm.doc.candidate_country_process;
			if (is_overseas && frappe.session.user !== frm.doc.transportation_manager && frappe.session.user !== "Administrator") {
				frappe.throw("Only the Transportation Manager can perform this action for Overseas hires.");
			} else if (!is_overseas && frappe.session.user !== frm.doc.general_services && frappe.session.user !== "Administrator") {
				frappe.throw("Only General Services can perform this action for Local hires.");
			}

			// Validate Pickup Details for Overseas candidates
			if (is_overseas) {
				if (!frm.doc.pickup_arranged) {
					frappe.throw("Please check 'Pickup Arranged' before proceeding.");
				}
				if (!frm.doc.pickup_contact) {
					frappe.throw("Please enter the Pickup Contact Person before proceeding.");
				}
			}
		}

		if (frappe.selected_workflow_action === "Mark as Joined") {
            let is_overseas = !!frm.doc.candidate_country_process;
            // Acknowledgement is no longer mandatory to block the workflow.
            // A background job handles daily reminders.
		}

		if (frappe.selected_workflow_action === "Did Not Arrive") {
			if (!frm.doc.recruiter) {
				frappe.throw("Please enter the Recruiter before notifying them that the candidate did not arrive.");
			}
		}
	}
});
