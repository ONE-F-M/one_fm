// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bonus Request", {
	setup(frm) {
		// Set default posting_date to today for new docs
		if (frm.is_new() && !frm.doc.posting_date) {
			frm.set_value("posting_date", frappe.datetime.get_today());
		}

		// Set default effective_year to current year for new docs
		if (frm.is_new() && !frm.doc.effective_year) {
			frm.set_value("effective_year", new Date().getFullYear());
		}

		// Requested By is the current user's Employee record
		if (frm.is_new() && !frm.doc.requested_by) {
			frappe.db.get_value("Employee", { user_id: frappe.session.user, status: "Active" }, "name").then((r) => {
				if (r.message && r.message.name) {
					frm.set_value("requested_by", r.message.name);
				}
			});
		}
	},

	onload(frm) {
		// Remembered so a department change only asks when it would drop employees
		frm._prev_department = frm.doc.department || "";

		if (frm.is_new() && frm.doc.posting_date && !frm.doc.payroll_cycle) {
			frm.trigger("set_payroll_cycle");
		}
	},

	refresh(frm) {
		frm.trigger("sync_bulk_checkboxes");

		// Hide standard print icon — custom print buttons are used instead
		frm.page.hide_icon_group();

		// Control Print button visibility based on workflow state
		toggle_print_visibility(frm);

		// Toggle recurring fields visibility
		toggle_recurring_fields(frm);
	},

	is_recurring_monthly(frm) {
		toggle_recurring_fields(frm);
	},

	start_date(frm) {
		validate_recurring_dates_client(frm);
	},

	end_date(frm) {
		validate_recurring_dates_client(frm);
	},

	posting_date(frm) {
		frm.trigger("set_payroll_cycle");
	},

	set_payroll_cycle(frm) {
		if (!frm.doc.posting_date) {
			frm.set_value("payroll_cycle", "");
			return;
		}

		// Cycles are named "Month YYYY", e.g. "October 2026"
		const cycle_name = moment(frm.doc.posting_date).format("MMMM YYYY");
		frappe.db.get_value("Payroll Cycle", { name: cycle_name }, "name").then((r) => {
			if (r.message && r.message.name) {
				frm.set_value("payroll_cycle", r.message.name);
			} else {
				frm.set_value("payroll_cycle", "");
				frappe.msgprint({
					title: __("Missing Payroll Cycle"),
					indicator: "orange",
					message: __("Payroll Cycle <b>{0}</b> does not exist in the system. Please create this cycle in <i>Payroll Cycle List</i> before submitting.", [cycle_name])
				});
			}
		});
	},

	department(frm) {
		const has_employees = (frm.doc.bonus_request_employees || []).some((r) => r.employee);

		if (!frm._prev_department || !has_employees) {
			frm._prev_department = frm.doc.department || "";
			if (!has_employees && frm.doc.bonus_request_employees?.length) {
				frm.clear_table("bonus_request_employees");
				frm.refresh_field("bonus_request_employees");
			}
			return;
		}

		if (frm.doc.department !== frm._prev_department) {
			frappe.confirm(
				__("Changing the Department will clear all listed employees to maintain department isolation. Do you wish to continue?"),
				() => {
					frm._prev_department = frm.doc.department || "";
					frm.clear_table("bonus_request_employees");
					frm.refresh_field("bonus_request_employees");
				},
				() => {
					const old_department = frm._prev_department;
					frappe.run_serially([
						() => frm.set_value("department", old_department),
						() => { frm._prev_department = old_department; }
					]);
				}
			);
		}
	},

	approve_all(frm) {
		set_all_rows(frm, "approve", "reject", "reject_all");
	},

	reject_all(frm) {
		set_all_rows(frm, "reject", "approve", "approve_all");
	},

	sync_bulk_checkboxes(frm) {
		if (frm._setting_bulk_state) return;
		frm._setting_bulk_state = true;

		const rows = frm.doc.bonus_request_employees || [];
		const has_rows = rows.length > 0;
		frm.set_value("approve_all", has_rows && rows.every((r) => cint(r.approve) === 1) ? 1 : 0);
		frm.set_value("reject_all", has_rows && rows.every((r) => cint(r.reject) === 1) ? 1 : 0);

		frm._setting_bulk_state = false;
	}
});


// ---- Child Table: Bonus Request Items ----
frappe.ui.form.on("Bonus Request Items", {
	bonus_amount(frm, cdt, cdn) {
		calculate_total_bonus_amount(frm);
	},

	bonus_request_employees_remove(frm) {
		calculate_total_bonus_amount(frm);
	},

	bonus_request_employees_add(frm) {
		calculate_total_bonus_amount(frm);
	},

	approve(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.approve) {
			frappe.model.set_value(cdt, cdn, "reject", 0);
		}
		frm.refresh_field("bonus_request_employees");
		frm.trigger("sync_bulk_checkboxes");
	},

	reject(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.reject) {
			frappe.model.set_value(cdt, cdn, "approve", 0);
		}
		frm.refresh_field("bonus_request_employees");
		frm.trigger("sync_bulk_checkboxes");
	}
});


// Approve All / Reject All: tick the field on every row and clear its opposite
function set_all_rows(frm, field, opposite, opposite_all) {
	if (frm._setting_bulk_state) return;
	frm._setting_bulk_state = true;

	const checked = cint(frm.doc[field + "_all"]) === 1;
	if (checked) {
		frm.set_value(opposite_all, 0);
	}
	(frm.doc.bonus_request_employees || []).forEach((row) => {
		frappe.model.set_value(row.doctype, row.name, field, checked ? 1 : 0);
		if (checked) {
			frappe.model.set_value(row.doctype, row.name, opposite, 0);
		}
	});

	frm.refresh_field("bonus_request_employees");
	frm._setting_bulk_state = false;
}


function calculate_total_bonus_amount(frm) {
	let total = 0;
	(frm.doc.bonus_request_employees || []).forEach((row) => {
		total += flt(row.bonus_amount);
	});
	frm.set_value("total_bonus_amount", total);
}


function toggle_print_visibility(frm) {
	// Show a Print button only in Approved/Completed states
	let allowed_states = ["Approved", "Completed"];
	let workflow_state = frm.doc.workflow_state;

	if (workflow_state && allowed_states.includes(workflow_state)) {
		frm.add_custom_button(__("Print Bonus Acknowledgment Letter"), () => {
			// Open printview directly with the correct format parameter
			let url = frappe.urllib.get_full_url(
				"/printview?doctype=" + encodeURIComponent(frm.doctype)
				+ "&name=" + encodeURIComponent(frm.doc.name)
				+ "&format=" + encodeURIComponent("Bonus Acknowledgment Letter")
			);
			window.open(url, "_blank");
		});
	}
}


function toggle_recurring_fields(frm) {
	let is_recurring = frm.doc.is_recurring_monthly;
	frm.toggle_display("auto_generation_day", is_recurring);
	frm.toggle_display("start_date", is_recurring);
	frm.toggle_display("end_date", is_recurring);
	frm.toggle_reqd("auto_generation_day", is_recurring);
	frm.toggle_reqd("start_date", is_recurring);
	frm.toggle_reqd("end_date", is_recurring);
}


function validate_recurring_dates_client(frm) {
	if (!frm.doc.is_recurring_monthly) return;
	if (!frm.doc.start_date || !frm.doc.end_date) return;

	if (frm.doc.end_date <= frm.doc.start_date) {
		frappe.msgprint({
			title: __("Invalid Timeline"),
			message: __("End Date must be later than the Start Date."),
			indicator: "red"
		});
	}
}
