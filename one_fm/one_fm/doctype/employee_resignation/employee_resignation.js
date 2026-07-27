// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Resignation", {
	onload: function(frm) {
		frm.trigger('update_ops_manager_mandatory');
		load_resignation_autocomplete_options(frm);
	},

	refresh: function (frm) {
		load_resignation_autocomplete_options(frm);
		frm.trigger('update_ops_manager_mandatory');

		let is_draft = frm.doc.__islocal || frm.doc.workflow_state === 'Draft';
		let is_editable = is_draft || frm.doc.workflow_state === 'Pending Relieving Date Correction';
		frm.set_df_property('resignation_initiation_date', 'read_only', is_editable ? 0 : 1);
		frm.set_df_property('relieving_date', 'read_only', is_editable ? 0 : 1);

		// Corporate hires have no Operations Manager step -- their "Supervisor"
		// is really their Line Manager (matches Employee Resignation Withdrawal
		// and Employee Resignation Date Adjustment).
		frm.set_df_property('supervisor', 'label', frm.doc.shift_working ? __('Supervisor') : __('Line Manager'));
		frm.refresh_field('supervisor');

		// Corporate hires have no Operations Manager step -- their "Supervisor" is
		// really their Line Manager, so their remarks field is labeled to match.
		frm.set_df_property('supervisor_remarks', 'label', frm.doc.shift_working ? __('Supervisor Remarks') : __('Line Manager Remarks'));
		frm.refresh_field('supervisor_remarks');

		// Filter Offboarding Officer to only show users with the 'Offboarding Officer' role
		frm.set_query('offboarding_officer', () => {
			return {
				query: 'frappe.core.doctype.user.user.user_query',
				filters: {
					'role': 'Offboarding Officer'
				}
			};
		});

		// Filter Operations Manager to only show users with the 'Operations Manager' role
		frm.set_query('operations_manager', () => {
			return {
				query: 'frappe.core.doctype.user.user.user_query',
				filters: {
					'role': 'Operations Manager'
				}
			};
		});

		// Bring the standard workflow button to the front
		setTimeout(() => {
			if (frm.page.custom_buttons) {
				let btn = frm.page.custom_buttons['Submit to Supervisor'];
				if (btn) {
					frm.page.change_custom_button_type('Submit to Supervisor', null, 'primary');
				}
			}
		}, 200);

		if (!frm.doc.__islocal && frm.doc.docstatus < 2) {
			// Check if any withdrawal already exists
			frappe.db.count("Employee Resignation Withdrawal", {
				filters: {
					employee_resignation: frm.doc.name,
					docstatus: ["<", 2]
				}
			}).then(count => {
				if (count === 0) {
					frm.add_custom_button(__("Resignation Withdrawal"), function () {
						frappe.new_doc("Employee Resignation Withdrawal", {
							employee_resignation: frm.doc.name
						});
					}, __("Actions"));
				}
			});
		}

		// Force-fetch dashboard connection counts so the badge numbers display reliably.
		// Frappe's IntersectionObserver may not fire if the Connections panel is already
		// in the viewport when the form renders. Resetting the flag and calling
		// set_open_count periodically ensures the counts are always fetched.
		if (!frm.doc.__islocal && frm.dashboard) {
			console.log("[Employee Resignation] Initializing connection counts force-fetch");
			let attempts = 0;
			let interval = setInterval(() => {
				attempts++;
				if (frm.dashboard && !frm.doc.__islocal) {
					console.log(`[Employee Resignation] Force-fetching dashboard counts (Attempt ${attempts}/3)`);
					frm.dashboard._fetched_counts = false;
					frm.dashboard.set_open_count();
				}
				if (attempts >= 3) {
					clearInterval(interval);
				}
			}, 600);
		}

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

		if (frm.doc.workflow_state === 'Pending Operations Manager' && ['Operation Admin', 'T4 Admin', 'Transportation Manager'].some(role => frappe.user_roles.includes(role))) {
			// Disable editing of all fields except replacement details
			frm.set_df_property('employee', 'read_only', 1);
			frm.set_df_property('resignation_initiation_date', 'read_only', 1);
			frm.set_df_property('relieving_date', 'read_only', 1);
			frm.set_df_property('reason_for_exit', 'read_only', 1);
			frm.set_df_property('supervisor', 'read_only', 1);
			frm.set_df_property('operations_manager', 'read_only', 1);
			frm.set_df_property('offboarding_officer', 'read_only', 1);

			// Explicitly allow editing of replacement fields
			frm.set_df_property('replacement_required', 'read_only', 0);
			frm.set_df_property('replacement_nationality', 'read_only', 0);
			frm.set_df_property('replacement_gender', 'read_only', 0);
		}

		if (frm.doc.workflow_state === 'Pending Operations Manager' && (frappe.user_roles.includes('Operation Admin') || frappe.user_roles.includes('T4 Admin'))) {
			// Disable editing of all fields except replacement details
			frm.set_df_property('employees', 'read_only', 1);
			frm.set_df_property('resignation_initiation_date', 'read_only', 1);
			frm.set_df_property('relieving_date', 'read_only', 1);
			frm.set_df_property('reason', 'read_only', 1);
			frm.set_df_property('supervisor', 'read_only', 1);
			frm.set_df_property('operations_manager', 'read_only', 1);
			frm.set_df_property('offboarding_officer', 'read_only', 1);
			
			// Explicitly allow editing of replacement fields
			frm.set_df_property('replacement_required', 'read_only', 0);
			frm.set_df_property('replacement_nationality', 'read_only', 0);
			frm.set_df_property('replacement_gender', 'read_only', 0);

			// Disable buttons inside the child table grid if open
			if (frm.fields_dict.employees && frm.fields_dict.employees.grid) {
				frm.fields_dict.employees.grid.disable_and_hide_buttons();
			}
		}
	},

	before_save: function(frm) {
		// Prevent WAF payload blocking by stripping strings with special characters
		// The python backend has been programmed to repopulate these natively
		frm.doc.site_allocation = null;
		frm.doc.project_allocation = null;
		frm.doc.department = null;
		frm.doc.shift_allocation = null;
		frm.doc.operations_role_allocation = null;
	},

	validate: function(frm) {
	    if (!frm.doc.employee) {
	        frappe.msgprint({
	            title: __('Missing Information'),
	            message: __('You must select the Resigning Employee before saving.'),
	            indicator: 'red'
	        });
	        frappe.validated = false;
			return;
	    }
	},

	after_save: function(frm) {
	    // No longer automatic; user prefers clicking the button themselves
	},

	before_workflow_action: function(frm) {
		if (frm.selected_workflow_action === "Submit to Supervisor") {
			return new Promise((resolve, reject) => {
				if (!frm.doc.resignation_letter) {
					frappe.msgprint({
						title: __('Missing Attachments'),
						message: __('Missing Resignation Letter. Please attach the file before submitting.'),
						indicator: 'red'
					});
					frappe.dom.unfreeze();
					reject();
				} else {
					resolve();
				}
			});
		}

		// Supervisor/Line Manager Remarks are required before their step moves on --
		// "Submit for Approval" (shift-workers, to Operations Manager) or "Approve"
		// while still "Pending Supervisor" (corporate's direct-to-Approved path,
		// since they have no separate Operations Manager step).
		if (
			(frm.selected_workflow_action === "Submit for Approval" || frm.selected_workflow_action === "Approve")
			&& frm.doc.workflow_state === "Pending Supervisor"
			&& !frm.doc.supervisor_remarks
		) {
			frappe.msgprint({
				title: __('Missing Remarks'),
				message: frm.doc.shift_working
					? __('Please provide Supervisor Remarks before proceeding.')
					: __('Please provide Line Manager Remarks before proceeding.'),
				indicator: 'red'
			});
			setTimeout(() => {
				frappe.dom.unfreeze();
			}, 100);
			return Promise.reject("Missing Supervisor Remarks");
		}

		if (frm.selected_workflow_action === "Approve" && frm.doc.workflow_state === "Pending Operations Manager") {
			if (!frm.doc.replacement_required) {
				frappe.msgprint({
					title: __('Missing Replacement Decision'),
					message: __('You must explicitly select <b>Yes</b> or <b>No</b> for "Is a Replacement Required?" before approving this resignation.'),
					indicator: 'red'
				});
				setTimeout(() => {
					frappe.dom.unfreeze();
				}, 100);
				return Promise.reject("Missing Replacement Decision");
			}
			if (!frm.doc.operations_manager_remarks) {
				frappe.msgprint({
					title: __('Missing Remarks'),
					message: __('Please provide Operations Manager Remarks before approving.'),
					indicator: 'red'
				});
				setTimeout(() => {
					frappe.dom.unfreeze();
				}, 100);
				return Promise.reject("Missing Operations Manager Remarks");
			}
		}
	},

	after_workflow_action: function(frm) {
		if (frm.doc.replacement_required === "Yes" && frm.doc.docstatus === 1) {
			// Find the newly created PR and jump to it
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'Project Manpower Request',
					filters: { employee_resignation: frm.doc.name },
					fieldname: 'name'
				},
				callback: function(r) {
					if (r.message && r.message.name) {
						frappe.show_alert({
							message: __('Auto-redirecting to Project Manpower Request...'),
							indicator: 'green'
						});
						setTimeout(() => {
							frappe.set_route('Form', 'Project Manpower Request', r.message.name);
						}, 2000);
					}
				}
			});
		}
	},

	on_submit: function(frm) {
		if (frm.doc.replacement_required === "Yes") {
			// Find the newly created PR and jump to it
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'Project Manpower Request',
					filters: { employee_resignation: frm.doc.name },
					fieldname: 'name'
				},
				callback: function(r) {
					if (r.message && r.message.name) {
						frappe.show_alert({
							message: __('Auto-redirecting to Project Manpower Request...'),
							indicator: 'green'
						});
						setTimeout(() => {
							frappe.set_route('Form', 'Project Manpower Request', r.message.name);
						}, 2000);
					}
				}
			});
		}
	},

	employee: function (frm) {
		if (!frm.doc.employee) return;

		frappe.call({
			method: 'one_fm.one_fm.doctype.employee_resignation.employee_resignation.get_employee_resignation_details',
			args: { employee: frm.doc.employee },
			callback: function(r) {
				let d = r.message;
				if (!d || Object.keys(d).length === 0) return;

				// Validation: Profile completeness check
				if (!d.project || !d.designation) {
					let missing = [];
					if (!d.project) missing.push("Project");
					if (!d.designation) missing.push("Designation");

					frappe.msgprint({
						title: 'Incomplete Employee Profile',
						message: `Employee <b>${d.employee_name} (${frm.doc.employee})</b> cannot be selected because their profile is missing: <b>${missing.join(" and ")}</b>. Please update their Employee record first.`,
						indicator: 'red'
					});
					frm.set_value('employee', '');
					return;
				}

				frm.set_value('project_allocation', d.project);
				frm.set_value('department', d.department);
				frm.set_value('designation', d.designation);
				frm.set_value('site_allocation', d.site);
				frm.set_value('employment_type', d.employment_type);
				frm.set_value('shift_allocation', d.shift);
				frm.set_value('operations_role_allocation', d.custom_operations_role_allocation);

				frm.set_value('shift_working', cint(d.shift_working) || 0);

				// Automatically fetch Supervisor (Priority: Line Manager -> Site Supervisor)
				let supervisor_found = false;
				if (d.supervisor_id) {
					frm.set_value('supervisor', d.supervisor_id);
					supervisor_found = true;
				}

				if (d.operations_manager) {
					frm.set_value('operations_manager', d.operations_manager);
				}

				// Only set site supervisor if line manager (reports_to) was not found
				if (d.site_supervisor_id && !supervisor_found) {
					frm.set_value('supervisor', d.site_supervisor_id);
				}

				frm.trigger('update_ops_manager_mandatory');
			}
		});
	},

	replacement_required: function(frm) {
		// Field trigger handled in server-side logic
	},

	update_ops_manager_mandatory: function(frm) {
		if (!frm.doc.employee) {
			frm.toggle_display("operational_impact_section", false);
			frm.set_df_property('operations_manager', 'reqd', 0);
			frm.set_df_property('offboarding_officer', 'reqd', 0);
			return;
		}

		let is_shift_worker = cint(frm.doc.shift_working);

		let show_ops_impact = ['Pending Operations Manager', 'Approved', 'Withdrawn'].includes(frm.doc.workflow_state);
		frm.toggle_display("operational_impact_section", show_ops_impact);

		let is_draft = frm.doc.__islocal || frm.doc.workflow_state === 'Draft';
		let is_restricted_stage = is_draft || frm.doc.workflow_state === 'Pending Relieving Date Correction';

		if (is_restricted_stage) {
			frm.set_df_property('operations_manager', 'hidden', 1);
			frm.set_df_property('offboarding_officer', 'hidden', 1);
			frm.set_df_property('operations_manager', 'reqd', 0);
			frm.set_df_property('offboarding_officer', 'reqd', 0);
		} else {
			frm.set_df_property('operations_manager', 'hidden', 0);
			frm.set_df_property('operations_manager', 'read_only', !is_shift_worker ? 1 : 0);
			frm.set_df_property('offboarding_officer', 'hidden', 0);

			// Mandatory for all non-restricted stages (Pending Supervisor, Pending Operations Manager, Approved)
			frm.set_df_property('operations_manager', 'reqd', is_shift_worker ? 1 : 0);
			frm.set_df_property('offboarding_officer', 'reqd', 1);
		}
	}
});

// ─── Nationality / Gender Autocomplete helpers ────────────────────────────────
function _populate_autocomplete(frm, fieldname, options) {
	// Ensure no get_query is overriding the local filter path
	let field = frm.fields_dict[fieldname];
	if (!field) return;
	if (field.get_query) delete field.get_query;

	// Push data into awesomplete after the current call stack clears
	setTimeout(() => {
		let f = frm.fields_dict[fieldname];
		if (f && typeof f.set_data === "function") {
			f.set_data(options);
		}
	}, 0);
}

function load_resignation_autocomplete_options(frm) {
	const NATIONALITY_KEY = "__resignation_nationality_options";
	const GENDER_KEY = "__resignation_gender_options";

	if (frappe[NATIONALITY_KEY] && frappe[GENDER_KEY]) {
		_populate_autocomplete(frm, "replacement_nationality", frappe[NATIONALITY_KEY]);
		_populate_autocomplete(frm, "replacement_gender", frappe[GENDER_KEY]);
		return;
	}

	frappe.call({
		method: "one_fm.one_fm.doctype.employee_resignation.employee_resignation.get_autocomplete_options",
		callback: function(r) {
			if (r.message) {
				let nationalities = ["Any", "African", "Asian"];
				(r.message.nationalities || []).forEach(n => {
					if (!nationalities.includes(n)) {
						nationalities.push(n);
					}
				});
				frappe[NATIONALITY_KEY] = nationalities;
				_populate_autocomplete(frm, "replacement_nationality", nationalities);

				let genders = ["Any", "Male", "Female"];
				(r.message.genders || []).forEach(g => {
					if (!genders.includes(g)) {
						genders.push(g);
					}
				});
				frappe[GENDER_KEY] = genders;
				_populate_autocomplete(frm, "replacement_gender", genders);
			}
		}
	});
}
