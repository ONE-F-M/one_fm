frappe.ui.form.on("Overseas Remedical", {
	appointment_status: function(frm) {
		update_actual_remedical_status(frm);
	},
	appointment_date: function(frm) {
		update_actual_remedical_status(frm);
	}
});

function update_actual_remedical_status(frm) {
	if (frm.doc.appointment_status === "Booked" && frm.doc.appointment_date) {
		// Only update if it's currently "Yet to apply"
		if (frm.doc.status === "Yet to apply") {
			frm.set_value("status", "In process");
		}
	}
}
