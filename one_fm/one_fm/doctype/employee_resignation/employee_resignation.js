// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Resignation", {
	onload: function (frm) {
		let show_header = !frm.doc.__islocal && frm.doc.workflow_state && (!["Draft", ""].includes(frm.doc.workflow_state));
		let is_corporate = frm.doc.project_allocation === "ONE FM - Head Office";
		let show_ops_impact = ["Pending Operations Manager", "Approved"].includes(frm.doc.workflow_state) || (frm.doc.workflow_state === "Pending Supervisor" && is_corporate);
		frm.toggle_display("operational_impact_section", show_ops_impact);
	},

	refresh: function (frm) {
		let show_header = !frm.doc.__islocal && frm.doc.workflow_state && (!["Draft", ""].includes(frm.doc.workflow_state));
		let is_corporate = frm.doc.project_allocation === "ONE FM - Head Office";
		let show_ops_impact = ["Pending Operations Manager", "Approved"].includes(frm.doc.workflow_state) || (frm.doc.workflow_state === "Pending Supervisor" && is_corporate);
		frm.toggle_display("operational_impact_section", show_ops_impact);

		let is_draft = frm.doc.__islocal || frm.doc.workflow_state === 'Draft';

		let is_editable = is_draft || frm.doc.workflow_state === 'Pending Relieving Date Correction';
		frm.set_df_property('resignation_initiation_date', 'read_only', is_editable ? 0 : 1);
		frm.set_df_property('relieving_date', 'read_only', is_editable ? 0 : 1);



		// Hide Operational Impact for Employee Draft and Correction stages
		let is_restricted_stage = is_draft || frm.doc.workflow_state === 'Pending Relieving Date Correction';

		if (is_restricted_stage) {
			frm.set_df_property('operations_manager', 'hidden', 1);
			frm.set_df_property('offboarding_officer', 'hidden', 1);
			frm.set_df_property('operations_manager', 'reqd', 0);
			frm.set_df_property('offboarding_officer', 'reqd', 0);
		} else {
			let is_corporate = frm.doc.project_allocation === "ONE FM - Head Office";
			frm.set_df_property('operations_manager', 'hidden', 0); // Keep visible to prevent column collapse
			frm.set_df_property('operations_manager', 'read_only', is_corporate ? 1 : 0);
			frm.set_df_property('offboarding_officer', 'hidden', 0);
			// Mandatory for Operations Manager and onwards, OR for Corporate in Pending Supervisor (since they skip OM)
			let is_mandatory = ["Pending Operations Manager", "Approved"].includes(frm.doc.workflow_state) || (frm.doc.workflow_state === "Pending Supervisor" && is_corporate);
			frm.set_df_property('operations_manager', 'reqd', (is_mandatory && !is_corporate) ? 1 : 0);
			frm.set_df_property('offboarding_officer', 'reqd', is_mandatory ? 1 : 0);
		}

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

		// Hide Withdrawal Status column strictly for initial entry
		if (frm.fields_dict.employees && frm.fields_dict.employees.grid) {
			frm.fields_dict.employees.grid.set_column_disp("withdrawal_status", show_header);
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

		if (!frm.doc.__islocal && frm.doc.employees && frm.doc.employees.length > 0) {
			let view_exit_tab = function (employee_id) {
				frappe.route_options = { "scroll_to": "exit" };
				frappe.set_route('Form', 'Employee', employee_id).then(() => {
					let ticks = 0;
					let focus_tab = setInterval(() => {
						ticks++;
						if (frappe.get_route()[0] === "Form" && frappe.get_route()[1] === "Employee" && cur_frm && cur_frm.docname === employee_id && cur_frm.layout) {

							// Trigger standard scroll mechanism which natively maps and activates Tab Breaks
							try {
								cur_frm.scroll_to_field("exit");
							} catch (e) { }

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
			};

			if (frm.doc.employees.length === 1) {
				frm.remove_custom_button(__('Employee Exit Tab'), __('Employee Profiles'));
				frm.add_custom_button(__('Employee Exit Tab'), function () {
					view_exit_tab(frm.doc.employees[0].employee);
				}, __('Employee Profiles'));
			} else {
				frm.doc.employees.forEach(row => {
					let btn_label = row.employee_name || row.employee;
					frm.add_custom_button(btn_label, function () {
						view_exit_tab(row.employee);
					}, __('Employee Profiles'));
				});
			}
		}
	},

	validate: function (frm) {
		if (["Draft", "Pending Relieving Date Correction"].includes(frm.doc.workflow_state) || frm.doc.__islocal) {
			frm.set_df_property('operations_manager', 'reqd', 0);
			frm.set_df_property('offboarding_officer', 'reqd', 0);
		} else {
			// Enforce mandatory strictly during OM assessment and beyond
			let is_corporate = frm.doc.project_allocation === "ONE FM - Head Office";
			let is_mandatory = ["Pending Operations Manager", "Approved"].includes(frm.doc.workflow_state) || (frm.doc.workflow_state === "Pending Supervisor" && is_corporate);
			frm.set_df_property('operations_manager', 'reqd', (is_mandatory && !is_corporate) ? 1 : 0);
			frm.set_df_property('offboarding_officer', 'reqd', is_mandatory ? 1 : 0);
		}

		if (!frm.doc.employees || frm.doc.employees.length === 0) {
			frappe.msgprint({
				title: __('Missing Information'),
				message: __('You must add at least one Resigning Employee before saving.'),
				indicator: 'red'
			});
			frappe.validated = false;
			return;
		}
	},

	after_save: function (frm) {
		// No longer automatic; user prefers clicking the button themselves
	},

	before_workflow_action: function (frm) {
		if (frm.selected_workflow_action === "Submit to Supervisor") {
			return new Promise((resolve, reject) => {
				let missing = [];
				if (frm.doc.employees) {
					frm.doc.employees.forEach(row => {
						if (!row.resignation_letter) missing.push(row.employee_name || row.employee);
					});
				}

				if (missing.length > 0) {
					frappe.msgprint({
						title: __('Missing Attachments'),
						message: __('Missing Resignation Letter for <b>{0}</b>. Please click the pencil edit icon ✏️ on their row and attach the file before submitting.').replace('{0}', missing.join(", ")),
						indicator: 'red'
					});
					frappe.dom.unfreeze();
					reject();
				} else {
					resolve();
				}
			});
		}

		if (frm.selected_workflow_action === "Approve") {
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
		}
	},

	after_workflow_action: function (frm) {
		if (frm.doc.replacement_required === "Yes" && frm.doc.docstatus === 1) {
			// Find the newly created PR and jump to it
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'Project Manpower Request',
					filters: { employee_resignation: frm.doc.name },
					fieldname: 'name'
				},
				callback: function (r) {
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

	on_submit: function (frm) {
		if (frm.doc.replacement_required === "Yes") {
			// Find the newly created PR and jump to it
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'Project Manpower Request',
					filters: { employee_resignation: frm.doc.name },
					fieldname: 'name'
				},
				callback: function (r) {
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
		// Legacy field triggers inside JS, safely disabled
	},

	replacement_required: function (frm) {
		// Field trigger handled in server-side logic
	}
});

frappe.ui.form.on('Employee Resignation Item', {
	employee: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (row.employee) {
			frappe.call({
				method: 'one_fm.one_fm.doctype.employee_resignation.employee_resignation.get_employee_resignation_details',
				args: { employee: row.employee },
				callback: function (r) {
					let d = r.message;
					if (d && Object.keys(d).length > 0) {
						// Validation: Profile completeness check
						if (!d.project || !d.designation) {
							let missing = [];
							if (!d.project) missing.push("Project");
							if (!d.designation) missing.push("Designation");

							frappe.msgprint({
								title: 'Incomplete Employee Profile',
								message: `Employee <b>${d.employee_name} (${row.employee})</b> cannot be added because their profile is missing: <b>${missing.join(" and ")}</b>. Please update their Employee record first.`,
								indicator: 'red'
							});
							frappe.model.set_value(cdt, cdn, 'employee', '');
							return;
						}

						// Force the child table exactly visually immediately
						frappe.model.set_value(cdt, cdn, 'employee_name', d.employee_name);
						frappe.model.set_value(cdt, cdn, 'project_allocation', d.project);
						frappe.model.set_value(cdt, cdn, 'designation', d.designation);
						frappe.model.set_value(cdt, cdn, 'employment_type', d.employment_type);
						// Natively sync properties if it's the first or master needs syncing
						if (!frm.doc.project_allocation) frm.set_value('project_allocation', d.project);
						if (!frm.doc.department) frm.set_value('department', d.department);
						if (!frm.doc.designation) frm.set_value('designation', d.designation);
						if (!frm.doc.site_allocation) frm.set_value('site_allocation', d.site);
						if (!frm.doc.employment_type) frm.set_value('employment_type', d.employment_type);
						if (!frm.doc.shift_allocation) frm.set_value('shift_allocation', d.shift);
						if (!frm.doc.operations_role_allocation) frm.set_value('operations_role_allocation', d.custom_operations_role_allocation);

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

						// Validate live Project AND Designation mismatch
						let errors = [];
						if (frm.doc.project_allocation && frm.doc.project_allocation !== d.project) {
							errors.push(`Project (${d.project} vs ${frm.doc.project_allocation})`);
						}
						if (frm.doc.designation && frm.doc.designation !== d.designation) {
							errors.push(`Designation (${d.designation} vs ${frm.doc.designation})`);
						}

						if (errors.length > 0) {
							frappe.msgprint({
								title: 'Mismatch Error',
								message: `Employee ${row.employee} does not match the collective batch! Mismatches: ${errors.join(", ")}. All resigning employees must share both exact Project AND Designation!`,
								indicator: 'red'
							});
							frappe.model.set_value(cdt, cdn, 'employee', '');
						}
					}
				}
			});
		}
	}
});
