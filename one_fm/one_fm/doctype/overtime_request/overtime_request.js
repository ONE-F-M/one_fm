// Copyright (c) 2021, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Overtime Request", {
	setup: function(frm) {
		// requested_by is auto-set via default:"__user" in DocType JSON
	},

	refresh: function(frm) {
		frm.trigger("set_employee_query");
		// Reset the acknowledgment flag on refresh
		frm._overtime_limit_acknowledged = false;
	},

	set_employee_query: function(frm) {
		// Story 1: Filter employees to only show non-shift-working employees (shift_working=0)
		frm.set_query("employee", () => {
			return {
				filters: {
					shift_working: 0,
					status: "Active"
				}
			};
		});
	},

	employee: function(frm) {
		// Story 3: Recalculate yearly hours when employee changes
		if (frm.doc.employee && frm.doc.overtime_hours) {
			frm.trigger("fetch_yearly_overtime_hours");
		}
	},

	start_time: function(frm) {
		// Story 3: Calculate overtime hours when start_time changes
		frm.trigger("calculate_overtime_hours");
	},

	end_time: function(frm) {
		// Story 3: Calculate overtime hours when end_time changes
		frm.trigger("calculate_overtime_hours");
	},

	calculate_overtime_hours: function(frm) {
		// Story 3: Calculate the difference between start_time and end_time
		// Handles overnight spans (e.g. 18:00 → 04:00 = 10 hours)
		if (!frm.doc.start_time || !frm.doc.end_time) return;

		let start = moment(frm.doc.start_time, "HH:mm:ss");
		let end = moment(frm.doc.end_time, "HH:mm:ss");

		// If end_time is before start_time, it crosses midnight — add 24 hours
		if (!end.isAfter(start)) {
			end.add(1, "day");
		}

		let duration = moment.duration(end.diff(start));
		let hours = parseFloat((duration.asHours()).toFixed(2));

		if (hours > 0) {
			frm.set_value("overtime_hours", hours);
			// Story 3: Fetch yearly overtime hours from server
			frm.trigger("fetch_yearly_overtime_hours");
		} else {
			frm.set_value("overtime_hours", 0);
			frm.set_value("yearly_overtime_hours", 0);
		}
	},

	fetch_yearly_overtime_hours: function(frm) {
		// Story 3: Fetch cumulative yearly overtime hours from server
		if (!frm.doc.employee || !frm.doc.overtime_hours || !frm.doc.date) return;

		frappe.call({
			method: "one_fm.one_fm.doctype.overtime_request.overtime_request.get_yearly_overtime_hours",
			args: {
				employee: frm.doc.employee,
				overtime_date: frm.doc.date,
				current_hours: frm.doc.overtime_hours,
				current_name: frm.doc.name || ""
			},
			callback: function(r) {
				if (r.message !== undefined) {
					frm.set_value("yearly_overtime_hours", r.message);
				}
			}
		});
	},

	before_save: function(frm) {
		// Story 4: 2-hour daily limit confirmation modal
		// Skip if already acknowledged or if yearly limit exceeded (server will block that)
		if (
			flt(frm.doc.overtime_hours) > 2
			&& flt(frm.doc.yearly_overtime_hours) <= 180
			&& !frm._overtime_limit_acknowledged
		) {
			frappe.validated = false;
			frappe.confirm(
				__("The requested overtime exceeds the limit of 2 hours per day. Do you acknowledge this limit and still wish to proceed with the submission?"),
				function() {
					// User clicked "Yes" — set flag and re-save
					frm._overtime_limit_acknowledged = true;
					frappe.validated = true;
					frm.save();
				},
				function() {
					// User clicked "No" — save is aborted (frappe.validated stays false)
					frm._overtime_limit_acknowledged = false;
				}
			);
		}
	}
});
