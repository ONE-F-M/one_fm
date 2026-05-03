// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bonus Request", {
	setup(frm) {
		// Set default effective_year to current year for new docs
		if (frm.is_new() && !frm.doc.effective_year) {
			frm.set_value("effective_year", new Date().getFullYear());
		}
	},

	refresh(frm) {
		// Toggle justification visibility based on others checkbox
		toggle_justification(frm);

		// Control Print button visibility based on workflow state
		toggle_print_visibility(frm);
	},

	others(frm) {
		toggle_justification(frm);
	}
});



function toggle_justification(frm) {
	let is_others = frm.doc.others;
	frm.toggle_display("justification", is_others);
	frm.toggle_reqd("justification", is_others);

	// Clear justification when Others is unchecked
	if (!is_others && frm.doc.justification) {
		frm.set_value("justification", "");
	}
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

		frm.add_custom_button(__("Print Bonus Request Letter"), () => {
			// Open printview directly with the correct format parameter
			let url = frappe.urllib.get_full_url(
				"/printview?doctype=" + encodeURIComponent(frm.doctype)
				+ "&name=" + encodeURIComponent(frm.doc.name)
				+ "&format=" + encodeURIComponent("Bonus Request Form")
			);
			window.open(url, "_blank");
		});
	}
}

