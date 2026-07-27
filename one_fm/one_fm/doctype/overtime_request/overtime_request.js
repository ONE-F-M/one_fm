// Copyright (c) 2021, ONE FM and contributors
// For license information, please see license.txt

// Hours of unredeemed public holiday overtime that earn one compensatory day off.
// Mirrors COMPENSATORY_DAY_OFF_THRESHOLD_HOURS in the controller.
const COMPENSATORY_DAY_OFF_THRESHOLD_HOURS = 9;

function apply_compensatory_day_off_eligibility(frm, balance) {
	// Eligibility is driven by the employee's cumulative unredeemed public holiday
	// overtime balance, not this request's hours (WI-001695). A request that has already
	// been redeemed stays eligible so its Compensatory Day Off section remains visible
	// after the balance drops back below the threshold.
	let eligible = (
		frm.doc.compensatory_leave_request
		|| flt(balance) >= COMPENSATORY_DAY_OFF_THRESHOLD_HOURS
	) ? 1 : 0;

	let was_eligible = frm.doc.eligible_for_compensatory_day_off ? 1 : 0;

	if (was_eligible !== eligible) {
		frm.set_value("eligible_for_compensatory_day_off", eligible);
	}

	// When no longer eligible, clear any previously selected day off
	if (!eligible && frm.doc.compensatory_day_off) {
		frm.set_value("compensatory_day_off", null);
	}

	// Prompt the employee to pick their Compensatory Day Off when they first become
	// eligible (transition from not-eligible → eligible).
	if (eligible && !was_eligible) {
		prompt_compensatory_day_off(frm, balance);
	}

	// Restrict the selectable range on the Compensatory Day Off picker.
	frm.trigger("set_compensatory_day_off_range");
}

function prompt_compensatory_day_off(frm, balance) {
	// Informational alert: tells the employee that a Compensatory Day Off is required,
	// which cumulative balance triggered it, and the window it must fall within (7 days
	// of the overtime date). The date itself is selected in the form field, and the
	// server blocks the workflow from progressing until it is set.
	if (!frm.doc.date) return;

	frappe.msgprint({
		title: __("Compensatory Day Off Required"),
		indicator: "blue",
		message: __("Your unredeemed Public Holiday overtime has reached {0} hours. Please select your Compensatory Day Off date (within 7 days of {1}).", [
			format_number(flt(balance), null, 2),
			frappe.datetime.str_to_user(frm.doc.date)
		])
	});
}

frappe.ui.form.on("Overtime Request", {
	setup: function(frm) {
		// requested_by is auto-set via before_insert in the controller
	},

	refresh: function(frm) {
		frm.trigger("set_employee_query");
		// Reset the acknowledgment flag on refresh
		frm._overtime_limit_acknowledged = false;

		// Read-only enforcement: lock end_time, present, and absent
		// from "Pending Payroll Officer" onwards
		let lock_attendance = [
			"Pending Payroll Officer",
			"Pending Finance Manager",
			"Completed",
			"Rejected"
		].includes(frm.doc.workflow_state);

		frm.set_df_property("end_time", "read_only", lock_attendance ? 1 : 0);
		frm.set_df_property("present", "read_only", lock_attendance ? 1 : 0);
		frm.set_df_property("absent", "read_only", lock_attendance ? 1 : 0);

		// Restrict the Compensatory Day Off picker when opening an eligible
		// record (e.g. the Line Manager reviewing a pending request).
		frm.trigger("set_compensatory_day_off_range");
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

		// The unredeemed Public Holiday balance is per employee, so it has to be
		// re-evaluated when the employee changes (WI-001695).
		frm.trigger("set_compensatory_day_off_eligibility");
	},

	overtime_type: function(frm) {
		// Re-evaluate compensatory day off eligibility when the type changes.
		// When switching away from "Overtime on Public Holiday", this resets
		// the flag, hides the section and clears the selected day off.
		frm.trigger("set_compensatory_day_off_eligibility");
	},

	date: function(frm) {
		// Re-apply the Compensatory Day Off window when the overtime date changes.
		frm.trigger("set_compensatory_day_off_range");
	},

	start_time: function(frm) {
		// Story 3: Calculate overtime hours when start_time changes
		frm.trigger("calculate_overtime_hours");
	},

	end_time: function(frm) {
		// Calculate overtime hours when end_time changes
		// This also handles recalculation when Line Manager edits End Time
		frm.trigger("calculate_overtime_hours");
	},

	present: function(frm) {
		// Mutual exclusion: uncheck Absent when Present is checked
		if (frm.doc.present) {
			frm.set_value("absent", 0);
		}
	},

	absent: function(frm) {
		// Mutual exclusion: uncheck Present when Absent is checked
		if (frm.doc.absent) {
			frm.set_value("present", 0);
		}
	},

	before_workflow_action: function(frm) {
		if (frm.selected_workflow_action === "Verify Attendance") {
			// Block if overtime end time has not passed
			let overtime_start = frappe.datetime.str_to_obj(frm.doc.date + " " + frm.doc.start_time);
			let overtime_end = frappe.datetime.str_to_obj(frm.doc.date + " " + frm.doc.end_time);
			if (overtime_start && overtime_end && overtime_end <= overtime_start) {
				overtime_end = moment(overtime_end).add(1, "day").toDate();
			}
			let now = frappe.datetime.str_to_obj(frappe.datetime.now_datetime());

			if (now < overtime_end) {
				frappe.dom.unfreeze();
				frappe.msgprint({
					title: __("Error"),
					indicator: "red",
					message: __("You cannot verify attendance until the scheduled overtime end time has passed.")
				});
				return Promise.reject();
			}

			// Block if neither Present nor Absent is checked
			if (!frm.doc.present && !frm.doc.absent) {
				frappe.dom.unfreeze();
				frappe.msgprint({
					title: __("Error"),
					indicator: "red",
					message: __("Please mark the employee as Present or Absent before verifying attendance.")
				});
				return Promise.reject();
			}
		}
		return Promise.resolve();
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
			// Use direct assignment to avoid async set_value side effects
			frm.doc.overtime_hours = hours;
			frm.refresh_field("overtime_hours");
			// Story 3: Fetch yearly overtime hours from server
			frm.trigger("fetch_yearly_overtime_hours");
		} else {
			frm.doc.overtime_hours = 0;
			frm.doc.yearly_overtime_hours = 0;
			frm.refresh_fields(["overtime_hours", "yearly_overtime_hours"]);
		}

		// Re-evaluate compensatory day off eligibility whenever hours change
		frm.trigger("set_compensatory_day_off_eligibility");
	},

	set_compensatory_day_off_eligibility: function(frm) {
		// The threshold is the employee's cumulative unredeemed Public Holiday overtime,
		// not this request's hours alone, so the balance has to come from the server.
		if (frm.doc.overtime_type !== "Overtime on Public Holiday" || !frm.doc.employee) {
			apply_compensatory_day_off_eligibility(frm, 0);
			return;
		}

		frappe.call({
			method: "one_fm.one_fm.doctype.overtime_request.overtime_request.get_projected_unredeemed_balance",
			args: {
				employee: frm.doc.employee,
				overtime_hours: flt(frm.doc.overtime_hours),
				current_name: frm.is_new() ? "" : frm.doc.name
			},
			callback: function(r) {
				apply_compensatory_day_off_eligibility(frm, flt(r.message));
			}
		});
	},

	set_compensatory_day_off_range: function(frm) {
		// Limit the Compensatory Day Off datepicker to the overtime date
		// through the overtime date + 7 days (inclusive). Server-side
		// validation remains the authority; this improves the UX.
		let field = frm.fields_dict["compensatory_day_off"];
		if (!field || !field.datepicker) return;

		if (frm.doc.eligible_for_compensatory_day_off && frm.doc.date) {
			field.datepicker.update({
				minDate: frappe.datetime.str_to_obj(frm.doc.date),
				maxDate: frappe.datetime.str_to_obj(frappe.datetime.add_days(frm.doc.date, 7))
			});
		} else {
			field.datepicker.update({ minDate: null, maxDate: null });
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
					frm.doc.yearly_overtime_hours = r.message;
					frm.refresh_field("yearly_overtime_hours");
				}
			}
		});
	},

	before_save: function(frm) {
		// Return a resolved Promise so that frappe.after_server_call() is NOT
		// called by the script_manager — otherwise unrelated pending AJAX calls
		// (chat widget, favicon loads, etc.) block the save indefinitely.

		// Story 4: 2-hour daily limit confirmation modal (new documents only)
		// Skip if already acknowledged or if yearly limit exceeded (server will block that)
		if (
			frm.is_new()
			&& flt(frm.doc.overtime_hours) > 2
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
		return Promise.resolve();
	}
});
