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
						frappe.db.get_value('Operations Site', doc.site_allocation, ['site_supervisor', 'operations_manager'])
							.then(site_data => {
								if (site_data && site_data.message) {
									if (site_data.message.operations_manager) {
										frm.set_value('operations_manager', site_data.message.operations_manager);
									}

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
	}
});
