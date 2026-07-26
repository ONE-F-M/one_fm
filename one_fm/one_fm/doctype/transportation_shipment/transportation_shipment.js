// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transportation Shipment", {
	refresh(frm) {
		frm.trigger("toggle_trip_request_fields");
	},

	onload(frm) {
		frm.trigger("toggle_trip_request_fields");
	},

	source_doctype(frm) {
		// Clearing/changing the source resets the ad-hoc waypoint rules.
		frm.trigger("toggle_trip_request_fields");
	},

	toggle_trip_request_fields(frm) {
		// When the shipment is sourced from a Trip Request, the long-term
		// Operations Site is irrelevant: hide it and force the ad-hoc Stop
		// Location to be visible and mandatory instead.
		const is_trip_request = frm.doc.source_doctype === "Trip Request";

		frm.toggle_display("operations_site", !is_trip_request);

		frm.toggle_display("stop_location", true);
		frm.set_df_property("stop_location", "reqd", is_trip_request ? 1 : 0);
		frm.refresh_field("stop_location");
	},
});
