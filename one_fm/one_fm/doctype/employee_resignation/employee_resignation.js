// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

// Mirrors REVIEW_STATES in employee_resignation.py
const REVIEW_STATES = [
	"Pending Line Manager",
	"Pending Supervisor",
	"Pending T4 Admin",
	"Pending Janitorial Head Supervisor",
	"Pending Security Manager",
	"Pending Project Manager",
];

// The Remarks section's fields are shared/reused across every stage -- only
// the heading changes, to make clear whose remarks are currently expected.
const STAGE_REMARKS_SECTION_LABELS = {
	"Pending Line Manager": "Line Manager Remarks",
	"Pending Supervisor": "Supervisor Remarks",
	"Pending T4 Admin": "T4 Admin Remarks",
	"Pending Janitorial Head Supervisor": "Janitorial Head Supervisor Remarks",
	"Pending Security Manager": "Security Manager Remarks",
	"Pending Project Manager": "Project Manager Remarks",
};

function _has_step_remarks(frm) {
	return !!(frm.doc.negotiation_remarks && frm.doc.performance_remarks && frm.doc.complaints_remarks);
}

// Section Break labels are baked into the DOM once at render time -- Frappe's
// own set_df_property/refresh_field never re-render a section's heading text,
// so update the section-head element directly.
function _set_section_label(frm, fieldname, label) {
	let $head = frm.$wrapper.find(`.form-section[data-fieldname="${fieldname}"] > .section-head`);
	if (!$head.length) return;
	$head.contents().filter(function() { return this.nodeType === 3; }).remove();
	$head.prepend(document.createTextNode(label + " "));
}

frappe.ui.form.on("Employee Resignation", {
	onload: function(frm) {
		frm.trigger('update_operational_impact_visibility');
		load_resignation_autocomplete_options(frm);
	},

	refresh: function (frm) {
		load_resignation_autocomplete_options(frm);
		frm.trigger('update_operational_impact_visibility');

		let is_draft = frm.doc.__islocal || frm.doc.workflow_state === 'Draft';
		let is_editable = is_draft || frm.doc.workflow_state === 'Pending Relieving Date Correction';
		frm.set_df_property('resignation_initiation_date', 'read_only', is_editable ? 0 : 1);
		frm.set_df_property('relieving_date', 'read_only', is_editable ? 0 : 1);

		// Non-shift (corporate) hires have no Project Manager step -- their
		// "Supervisor" is really their Line Manager, the sole final approver
		// (matches Employee Resignation Withdrawal and Date Adjustment).
		frm.set_df_property('supervisor', 'label', frm.doc.shift_working ? __('Supervisor') : __('Line Manager'));
		frm.refresh_field('supervisor');

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

		// Mirrors validate_employee_permissions() server-side: at the final
		// decision stage, these roles may only touch the replacement fields.
		if (frm.doc.workflow_state === 'Pending Project Manager' && ['Operation Admin', 'T4 Admin', 'Transportation Manager'].some(role => frappe.user_roles.includes(role))) {
			frm.set_df_property('employee', 'read_only', 1);
			frm.set_df_property('resignation_initiation_date', 'read_only', 1);
			frm.set_df_property('relieving_date', 'read_only', 1);
			frm.set_df_property('reason_for_exit', 'read_only', 1);
			frm.set_df_property('supervisor', 'read_only', 1);
			frm.set_df_property('offboarding_officer', 'read_only', 1);

			// Explicitly allow editing of replacement fields
			frm.set_df_property('replacement_required', 'read_only', 0);
			frm.set_df_property('replacement_nationality', 'read_only', 0);
			frm.set_df_property('replacement_gender', 'read_only', 0);
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

		// Every review stage (Line Manager, Supervisor, T4 Admin, Cleaning Head
		// Supervisor, Security Manager, Project Manager) must have its Negotiation /
		// Performance / Complaints remarks filled in before the document is allowed
		// to leave that stage. Mirrors validate_step_remarks() server-side -- this
		// is just the friendlier inline warning.
		if (REVIEW_STATES.includes(frm.doc.workflow_state) && !_has_step_remarks(frm)) {
			frappe.msgprint({
				title: __('Missing Remarks'),
				message: __('Please record Negotiation, Performance, and Complaints remarks for this stage before proceeding.'),
				indicator: 'red'
			});
			setTimeout(() => {
				frappe.dom.unfreeze();
			}, 100);
			return Promise.reject("Missing Step Remarks");
		}

		if (frm.selected_workflow_action === "Approve" && frm.doc.workflow_state === "Pending Project Manager") {
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

				// Only set site supervisor if line manager (reports_to) was not found
				if (d.site_supervisor_id && !supervisor_found) {
					frm.set_value('supervisor', d.site_supervisor_id);
				}

				frm.trigger('update_operational_impact_visibility');
			}
		});
	},

	replacement_required: function(frm) {
		// Field trigger handled in server-side logic
	},

	update_operational_impact_visibility: function(frm) {
		if (!frm.doc.employee) {
			frm.toggle_display("operational_impact_section", false);
			frm.set_df_property('offboarding_officer', 'reqd', 0);
			return;
		}

		let show_ops_impact = REVIEW_STATES.includes(frm.doc.workflow_state) || ['Approved', 'Withdrawn'].includes(frm.doc.workflow_state);
		frm.toggle_display("operational_impact_section", show_ops_impact);

		_set_section_label(frm, 'remarks_history_section', STAGE_REMARKS_SECTION_LABELS[frm.doc.workflow_state] || __('Remarks'));

		let is_draft = frm.doc.__islocal || frm.doc.workflow_state === 'Draft';
		let is_restricted_stage = is_draft || frm.doc.workflow_state === 'Pending Relieving Date Correction';

		frm.set_df_property('offboarding_officer', 'hidden', is_restricted_stage ? 1 : 0);
		frm.set_df_property('offboarding_officer', 'reqd', is_restricted_stage ? 0 : 1);
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
