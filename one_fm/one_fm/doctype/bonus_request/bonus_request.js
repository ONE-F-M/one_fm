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

		// Auto-set requested_by from current user (Link → User)
		if (frm.is_new() && !frm.doc.requested_by) {
			frm.set_value("requested_by", frappe.session.user);
		}
	},

	refresh(frm) {
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
	},

	reject(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.reject) {
			frappe.model.set_value(cdt, cdn, "approve", 0);
		}
		frm.refresh_field("bonus_request_employees");
	}
});


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
