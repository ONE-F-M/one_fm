// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Resignation Withdrawal", {
	onload: function(frm) {
		let show_date = !frm.doc.__islocal && frm.doc.workflow_state && frm.doc.workflow_state !== "Draft";
		frm.toggle_display("relieving_date", show_date);
	},

	refresh: function(frm) {
		let show_date = !frm.doc.__islocal && frm.doc.workflow_state && frm.doc.workflow_state !== "Draft";
		frm.toggle_display("relieving_date", show_date);

		// Automatically fetch the employee + supervisor from the parent resignation
		if (frm.doc.employee_resignation && frm.doc.__islocal) {
			// Ensure it only overrides on creation
			frappe.db.get_doc("Employee Resignation", frm.doc.employee_resignation)
				.then(doc => {
					frm.set_value('employee', doc.employee);

					// AUTO-FETCH Supervisor logic (Same as Resignation)
					if (doc.site_allocation) {
						frappe.db.get_value('Operations Site', doc.site_allocation, 'site_supervisor')
							.then(site_data => {
								if (site_data && site_data.message) {
									// Always prioritize Line Manager from the resignation itself if it was set
									if (doc.supervisor) {
										frm.set_value('supervisor', doc.supervisor);
									} else if (site_data.message.site_supervisor) {
										frappe.db.get_value('Employee', site_data.message.site_supervisor, 'user_id')
											.then(user_data => {
												if (user_data && user_data.message && user_data.message.user_id) {
													frm.set_value('supervisor', user_data.message.user_id);
												}
											});
									}
								}
							});
					} else if (doc.supervisor) {
						 frm.set_value('supervisor', doc.supervisor);
					}
				});
		}

		// Bring the standard workflow button to the front
		setTimeout(() => {
			if (frm.page.custom_buttons) {
				let btn = frm.page.custom_buttons['Submit to Supervisor'];
				if (btn) {
					frm.page.change_custom_button_type('Submit to Supervisor', null, 'primary');
				}
			}
		}, 200);

		if (!frm.doc.__islocal && frm.doc.employee) {
			frm.remove_custom_button(__('Employee Exit Tab'), __('Employee Profiles'));
			frm.add_custom_button(__('Employee Exit Tab'), function() {
				frappe.route_options = {"scroll_to": "exit"};
				frappe.set_route('Form', 'Employee', frm.doc.employee).then(() => {
					let ticks = 0;
					let focus_tab = setInterval(() => {
						ticks++;
						if (frappe.get_route()[0] === "Form" && frappe.get_route()[1] === "Employee" && cur_frm && cur_frm.docname === frm.doc.employee && cur_frm.layout) {

							// Trigger standard scroll mechanism which natively maps and activates Tab Breaks
							try {
								cur_frm.scroll_to_field("exit");
							} catch(e) {}

							// Directly target the framework's internal tab link reference for Bulletproof v14/v15 Bootstrap triggering
							if (cur_frm.fields_dict.exit && cur_frm.fields_dict.exit.$tab) {
								let $tab = cur_frm.fields_dict.exit.$tab;
								if (!$tab.hasClass("active") || !$tab.parent().hasClass("active")) {
									if (typeof $tab.tab === "function") {
										$tab.tab("show");
									}
									$tab[0].click();
								}
							}
						}
						// Secure the transition against Frappe's post-render jitter over 1.5 seconds
						if (ticks > 15) {
							clearInterval(focus_tab);
						}
					}, 100);
				});
			}, __('Employee Profiles'));
		}

		if (frm.doc.employee_resignation) {
			frappe.db.get_value('Employee Resignation', frm.doc.employee_resignation, 'shift_working')
			.then(r => {
				let is_shift_worker = r.message ? cint(r.message.shift_working) : 0;
				frm.set_value('is_corporate', is_shift_worker ? 0 : 1);
				// Corporate hires have no Project Manager step -- their "Supervisor"
				// is really their Line Manager, the sole final approver.
				frm.set_df_property('supervisor', 'label', is_shift_worker ? __('Supervisor') : __('Line Manager'));
				frm.refresh_fields();
			});
		}
	},

	validate: function(frm) {
	    // Robust UI validator catch to ensure missing attachments strictly block saving
	    if (!frm.doc.reason || !frm.doc.resignation_withdrawal_letter) {
	        frappe.msgprint({
	            title: __('Missing Elements'),
	            message: __('You must provide both a Reason and a Withdrawal Letter to submit a withdrawal.'),
	            indicator: 'red'
	        });
	        frappe.validated = false;
	    }
	},

	before_workflow_action: function(frm) {
		if (!frm.doc.reason || !frm.doc.resignation_withdrawal_letter) {
			frappe.msgprint({
				title: __('Missing Elements'),
				message: __('You must provide both a Reason and a Withdrawal Letter to formally proceed.'),
				indicator: 'red'
			});

			// Absolute guarantee to unlock the Frappe UI freeze right after Promise rejection
			setTimeout(() => {
				frappe.dom.unfreeze();
			}, 100);

			return Promise.reject("Missing Elements");
		}

		// apply_workflow() reloads the document from the database before running
		// the transition, so a reason that only exists on this form is thrown
		// away and the server then refuses the rejection. Write the field on its
		// own first, whether it was typed into the form or into the prompt below.
		if (frm.selected_workflow_action === "Reject") {
			if (frm.doc.reason_for_rejection) {
				return persist_rejection_reason(frm, frm.doc.reason_for_rejection);
			}

			return new Promise((resolve, reject) => {
				let submitted = false;
				let dialog = new frappe.ui.Dialog({
					title: __("Reject Withdrawal"),
					fields: [{
						fieldname: "reason_for_rejection",
						fieldtype: "Small Text",
						label: __("Reason for Rejection"),
						reqd: 1
					}],
					primary_action_label: __("Reject"),
					primary_action: (values) => {
						submitted = true;
						dialog.hide();
						// Put the freeze back, so the framework's own unfreeze
						// once the workflow call settles stays balanced.
						frappe.dom.freeze();
						persist_rejection_reason(frm, values.reason_for_rejection)
							.then(resolve)
							.catch(reject);
					}
				});
				dialog.onhide = () => {
					if (!submitted) {
						// Already unfrozen below; nothing to release here.
						reject("Rejection Cancelled");
					}
				};
				// The workflow button freezes the page before calling us, and
				// #freeze sits at z-index 1055 against the dialog's 1050 -- the
				// prompt would render greyed out and swallow every click. Lift the
				// freeze for as long as the dialog is open.
				frappe.dom.unfreeze();
				dialog.show();
			});
		}
	}
});

// Store the Reason for Rejection by itself, then mirror it onto the open form so
// the field reads back correctly once the transition completes. Resolves only on
// a successful write -- letting a failed write through would land the approver on
// the same "Please provide Reason for Rejection" error this exists to prevent.
// Callers must hold the page freeze when they call this; the catch releases it.
function persist_rejection_reason(frm, reason_for_rejection) {
	return frappe
		.xcall(
			"one_fm.one_fm.doctype.employee_resignation_withdrawal.employee_resignation_withdrawal.set_rejection_reason",
			{ name: frm.doc.name, reason_for_rejection: reason_for_rejection }
		)
		.then((result) => {
			frm.doc.reason_for_rejection = reason_for_rejection;
			// apply_workflow is handed this same doc and saves it without
			// reloading, so it has to carry the timestamp the write just
			// produced or the save is rejected as a conflict.
			if (result && result.modified) {
				frm.doc.modified = result.modified;
			}
		})
		.catch((error) => {
			// The framework only unfreezes once the workflow call itself settles,
			// so a rejection here would otherwise leave the page locked.
			frappe.dom.unfreeze();
			throw error;
		});
}
