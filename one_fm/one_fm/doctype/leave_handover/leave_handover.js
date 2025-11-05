// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Leave Handover", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === "Transferred" && frm.doc.employee_user_id === frappe.session.user) {
			frm.add_custom_button(__("Revert"), () => {
				frappe.confirm(
					__("You are about to replace the reliever with the Leave Applicant in each of the documents referenced in the table. Do you want to proceed?"),
					() => {
						frappe.call({
							method: "revert_handover",
							doc: frm.doc,
							callback: function(r) {
								if (!r.exc) {
									frm.reload_doc();
								}
							}
						});
					}
				);
			}).addClass("btn-primary");
		}
		set_submit_button(frm);
	},
	after_save(frm) {
		frm.dashboard.clear_headline();
		if (frm.doc.handover_items && frm.doc.handover_items.length > 0) {
			const doctype_counts = frm.doc.handover_items.reduce((acc, item) => {
				acc[item.reference_doctype] = (acc[item.reference_doctype] || 0) + 1;
				return acc;
			}, {});

			const message_parts = Object.entries(doctype_counts).map(([doctype, count]) => {
				return `${count} ${doctype}`;
			});

			const message = __("Found {0}. Proceed to set the relievers", [message_parts.join(", ")]);
			frappe.show_alert({ message: message, indicator: "green" });
		}
	},
	before_submit(frm) {
		if (frm.doc.employee_user_id !== frappe.session.user) {
			frappe.throw(__("You are not authorized to submit this Leave Handover."));
		}
	}
});

function set_submit_button(frm) {
	if (frm.doc.docstatus === 0 && !frm.is_new()) {
		frm.page.clear_primary_action();
		frm.page.set_primary_action(__('Submit'), function() {
			frappe.confirm(
				__("You are about to replace the Employee with the Reliever in each of the documents referenced in the table. Do you want to proceed?"),
				function() {
					frm.save('Submit'); // proceed
				},
				function() {
					frappe.msgprint(__('Submission cancelled'));
				}
			);
		});
	}
}
