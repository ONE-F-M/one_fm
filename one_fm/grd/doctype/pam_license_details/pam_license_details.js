// Keeps "Total Available Quota" on PAM License Details in step with the
// quota_classification child table while the user edits it. The server
// (validate / recount_quota_rows) stays the authority and rewrites both the
// row figures and the total on save.

// Same formula as the server: allocated - registered - visas issued - transfer
// requests, never below zero, rounded half up, held as text.
function derive_available_quota(row) {
	const available = Math.max(
		flt(row.allocated_quota)
			- flt(row.registered_numbers_of_employees)
			- flt(row.number_of_visas_issued)
			- flt(row.number_of_transfer_requests),
		0
	);
	return String(Math.floor(available + 0.5));
}

function update_total_available_quota(frm) {
	const total = (frm.doc.quota_classification || []).reduce(
		(sum, row) => sum + flt(row.available_quota),
		0
	);
	frm.set_value("total_available_quota", String(total));
}

function recalculate_row(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "available_quota", derive_available_quota(row));
	update_total_available_quota(frm);
}

frappe.ui.form.on("Quota Classification", {
	allocated_quota(frm, cdt, cdn) {
		recalculate_row(frm, cdt, cdn);
	},

	number_of_transfer_requests(frm, cdt, cdn) {
		recalculate_row(frm, cdt, cdn);
	},

	available_quota(frm) {
		update_total_available_quota(frm);
	},

	quota_classification_remove(frm) {
		update_total_available_quota(frm);
	},
});
