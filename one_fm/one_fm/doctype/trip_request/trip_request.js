// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Trip Request", {
	source_doctype(frm) {
		// Changing the source doctype invalidates the previously linked record
		// and any destination that was derived from it.
		frm.set_value("source_reference", null);
		frm.set_value("destination_location", null);
	},

	source_reference(frm) {
		fetch_destination_location(frm);
	},
});

function fetch_destination_location(frm) {
	if (!frm.doc.source_doctype || !frm.doc.source_reference) {
		return;
	}

	frappe.call({
		method: "one_fm.one_fm.doctype.trip_request.trip_request.get_destination_location",
		args: {
			source_doctype: frm.doc.source_doctype,
			source_reference: frm.doc.source_reference,
		},
		callback(r) {
			// r.message is null when the source carries no location (e.g.
			// Client Interview Shortlist) — leave the field empty in that case.
			frm.set_value("destination_location", r.message || null);
		},
	});
}
