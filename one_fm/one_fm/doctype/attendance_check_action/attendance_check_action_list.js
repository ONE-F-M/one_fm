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

		// Deadline Breached (resolved as a breach) -> Red
		if (doc.status === "Deadline Breached") {
			return [__("Deadline Breached"), "red", "status,=,Deadline Breached"];
		}

		// Draft whose deadline has already passed but not yet resolved -> Orange,
		// prompting the user to set a terminal status. Filters to unresolved drafts.
		if (
			doc.status === "Draft" &&
			doc.deadline_date &&
			frappe.datetime.get_day_diff(frappe.datetime.get_today(), doc.deadline_date) > 0
		) {
			return [__("Deadline Passed"), "orange", "status,=,Draft"];
		}

		// Draft -> Orange
		return [__("Draft"), "orange", "status,=,Draft"];
	},
};
