frappe.ui.form.on("Overseas Remedical", {
	refresh: function(frm) {

		// Override dashboard link routing for sibling tracking documents
		setTimeout(() => {
			if (frm.dashboard && frm.dashboard.wrapper) {
				frm.dashboard.wrapper.find('.document-link').off('click').on('click', function(e) {
					e.preventDefault();
					e.stopPropagation();
					let doctype = $(this).attr('data-doctype');
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
				});
			}
		}, 1000);

		update_actual_remedical_status(frm);
	},
	validate: function(frm) {
		update_actual_remedical_status(frm);
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
		// Only update if it's currently "Yet to apply"
		if (frm.doc.status === "Yet to apply") {
			frm.set_value("status", "In process");
		}
	}
}
