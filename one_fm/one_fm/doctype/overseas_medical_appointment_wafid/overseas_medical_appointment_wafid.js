frappe.ui.form.on("Overseas Medical Appointment WAFID", {
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

		update_actual_medical_status(frm);
	},
	validate: function(frm) {
		update_actual_medical_status(frm);
	},
	appointment_status: function(frm) {
		update_actual_medical_status(frm);
	},
	appointment_date: function(frm) {
		update_actual_medical_status(frm);
	},
	status: function(frm) {
		if (frm.doc.status === "Medical failed and Proceeded to Remedical") {
			frappe.show_alert({
				message: __("Save this document to automatically create the Remedical record."),
				indicator: "orange"
			});
		}
	},
	after_save: function(frm) {
		if (frm.doc.status === "Medical failed and Proceeded to Remedical") {
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Overseas Remedical",
					filters: {
						candidate_country_process: frm.doc.candidate_country_process
					},
					limit_page_length: 1
				},
				callback: function(r) {
					if (!r.message || r.message.length === 0) {
						frappe.confirm('Do you want to create the Overseas Remedical record now?', function() {
							frappe.route_options = {
								candidate_country_process: frm.doc.candidate_country_process,
								original_medical_ref: frm.doc.name
							};
							frappe.new_doc("Overseas Remedical");
						});
					}
				}
			});
		}
	}
});

function update_actual_medical_status(frm) {
	if (frm.doc.appointment_status === "Booked" && frm.doc.appointment_date) {
		// Only update if it's currently "Yet to apply"
		if (frm.doc.status === "Yet to apply") {
			frm.set_value("status", "In process");
		}
	}
}
