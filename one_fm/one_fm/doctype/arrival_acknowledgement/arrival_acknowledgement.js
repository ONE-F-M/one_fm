// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

const ARRIVAL_ACKNOWLEDGEMENT_DEPARTMENT_ROLES = {
	"Transportation": ["Transportation Manager"],
	"General Services": ["Accommodation User"],
	"Finance": ["Finance User"],
	"Warehouse": ["Warehouse Supervisor"],
	"Operations": ["Operation Admin", "T4 Admin"],
};

function arrival_acknowledgement_call_acknowledge(frm) {
	frappe.call({
		method: "one_fm.one_fm.doctype.arrival_acknowledgement.arrival_acknowledgement.acknowledge",
		args: { name: frm.doc.name },
		freeze: true,
		callback: function() {
			frm.reload_doc();
		}
	});
}

frappe.ui.form.on("Arrival Acknowledgement", {
	refresh: function(frm) {
		if (frm.is_new()) {
			return;
		}

		if (frm.doc.status !== "Acknowledged") {
			let required_roles = ARRIVAL_ACKNOWLEDGEMENT_DEPARTMENT_ROLES[frm.doc.department] || [];
			let can_acknowledge = frappe.user.has_role("System Manager") || required_roles.some((role) => frappe.user.has_role(role));
			if (!can_acknowledge) {
				return;
			}

			frm.add_custom_button(__("Mark as Acknowledged"), function() {
				arrival_acknowledgement_call_acknowledge(frm);
			}).addClass("btn-primary");
			return;
		}

		// Already Acknowledged -- Transportation gets a separate, later step to confirm
		// whether the candidate actually arrived.
		if (frm.doc.department === "Transportation" && !frm.doc.arrival_confirmation) {
			let can_confirm = frappe.user.has_role("System Manager") || frappe.user.has_role("Transportation Manager");
			if (!can_confirm) {
				return;
			}

			frm.add_custom_button(__("Confirm Arrival"), function() {
				frappe.prompt([
					{ label: __("Outcome"), fieldname: "outcome", fieldtype: "Select", options: ["Arrived", "Did Not Arrive"], reqd: 1 },
				], function(values) {
					frappe.call({
						method: "one_fm.one_fm.doctype.arrival_acknowledgement.arrival_acknowledgement.confirm_arrival",
						args: { name: frm.doc.name, outcome: values.outcome },
						freeze: true,
						callback: function() {
							frm.reload_doc();
						}
					});
				}, __("Confirm Arrival"), __("Submit"));
			}).addClass("btn-primary");
		}
	}
});
