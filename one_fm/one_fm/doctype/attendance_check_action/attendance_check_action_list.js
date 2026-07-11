// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.listview_settings["Attendance Check Action"] = {
	add_fields: ["status", "deadline_date", "docstatus"],
	get_indicator(doc) {
		// Submitted / Closed -> Green
		if (doc.docstatus === 1 || doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		}

		// Purchased -> Blue
		if (doc.status === "Purchased") {
			return [__("Purchased"), "blue", "status,=,Purchased"];
		}

		// Draft with a passed deadline -> Deadline Breached (Red, virtual)
		if (
			doc.status === "Draft" &&
			doc.deadline_date &&
			frappe.datetime.get_day_diff(frappe.datetime.get_today(), doc.deadline_date) > 0
		) {
			return [__("Deadline Breached"), "red", "status,=,Draft"];
		}

		// Draft -> Orange
		return [__("Draft"), "orange", "status,=,Draft"];
	},
};
