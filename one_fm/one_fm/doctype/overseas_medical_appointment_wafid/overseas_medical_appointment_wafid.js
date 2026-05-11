frappe.ui.form.on("Overseas Medical Appointment WAFID", {
	refresh: function(frm) {
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
			frappe.db.get_value("Overseas Remedical", {"original_medical_ref": frm.doc.name}, "name", function(r) {
				if (!r || !r.message || !r.message.name) {
					frappe.confirm('Do you want to create the Overseas Remedical record now?', function() {
						frappe.route_options = {
							candidate_country_process: frm.doc.candidate_country_process,
							original_medical_ref: frm.doc.name
						};
						frappe.new_doc("Overseas Remedical");
					});
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
