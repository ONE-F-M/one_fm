// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.listview_settings['Project Manpower Request'] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		if (doc.status === "Open") {
			return [__("Open"), "orange", "status,=,Open"];
		} else if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		} else if (doc.status === "Withdrawn") {
			return [__("Withdrawn"), "gray", "status,=,Withdrawn"];
		}
	}
};
