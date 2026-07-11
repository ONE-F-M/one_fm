// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Check Action", {
	refresh(frm) {
		// Action is strictly read-only and locked to "Issue a New Mobile".
		frm.set_df_property("action", "read_only", 1);
		show_deadline_indicator(frm);
	},

	purchasing_method(frm) {
		// Selecting either purchasing method defaults the grace period to 14 days.
		if (frm.doc.purchasing_method && !frm.doc.grace_period) {
			frm.set_value("grace_period", 14);
		}
	},

	grace_period(frm) {
		// Grace Period -> Deadline Date (Start Date + Grace Period).
		if (frm.doc.start_date && frm.doc.grace_period) {
			const deadline = frappe.datetime.add_days(frm.doc.start_date, frm.doc.grace_period);
			if (deadline !== frm.doc.deadline_date) {
				frm.set_value("deadline_date", deadline);
			}
		}
	},

	deadline_date(frm) {
		// Deadline Date -> Grace Period (Deadline Date - Start Date).
		if (frm.doc.start_date && frm.doc.deadline_date) {
			const grace = frappe.datetime.get_day_diff(frm.doc.deadline_date, frm.doc.start_date);
			if (grace !== frm.doc.grace_period) {
				frm.set_value("grace_period", grace);
			}
		}
	},

	start_date(frm) {
		// Recompute the deadline when the start date changes and a grace period is set.
		if (frm.doc.start_date && frm.doc.grace_period) {
			frm.set_value("deadline_date", frappe.datetime.add_days(frm.doc.start_date, frm.doc.grace_period));
		}
	},
});

function show_deadline_indicator(frm) {
	// Virtual "Deadline Breached" indicator (red) on the form header while still in Draft.
	if (
		frm.doc.docstatus === 0 &&
		frm.doc.status === "Draft" &&
		frm.doc.deadline_date &&
		frappe.datetime.get_day_diff(frappe.datetime.get_today(), frm.doc.deadline_date) > 0
	) {
		frm.dashboard.set_headline_alert(
			`<div class="text-danger font-weight-bold">${__("Deadline Breached")}</div>`
		);
	}
}
