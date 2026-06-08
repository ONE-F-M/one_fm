// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bonus Request", {
	setup(frm) {
		// Set default effective_year to current year for new docs
		if (frm.is_new() && !frm.doc.effective_year) {
			frm.set_value("effective_year", new Date().getFullYear());
		}

		// Auto-fetch requested_by from current user's employee record
		if (frm.is_new() && !frm.doc.requested_by) {
			frappe.db.get_value(
				"Employee",
				{ user_id: frappe.session.user, status: "Active" },
				"name",
				(r) => {
					if (r && r.name) {
						frm.set_value("requested_by", r.name);
					}
				}
			);
		}
	},

	refresh(frm) {
		// Hide standard print icon — custom print buttons are used instead
		frm.page.hide_icon_group();

		// Control Print button visibility based on workflow state
		toggle_print_visibility(frm);
	}
});


// ---- Child Table: Bonus Request Items ----
frappe.ui.form.on("Bonus Request Items", {
	bonus_amount(frm, cdt, cdn) {
		calculate_total_bonus_amount(frm);
	},

	items_remove(frm) {
		calculate_total_bonus_amount(frm);
	},

	items_add(frm) {
		calculate_total_bonus_amount(frm);
	}
});


function calculate_total_bonus_amount(frm) {
	let total = 0;
	(frm.doc.items || []).forEach((row) => {
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
