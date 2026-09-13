frappe.ui.form.on("Penalty And Investigation", {
	setup: function (frm) {
		// A retired penalty code must not be offered for a new penalty (WI-001794).
		frm.set_query("applied_penalty_code", function () {
			return { filters: { is_active: 1 } };
		});
	},
	onload: function (frm) {
		if (frm.is_new()) {
			frm.set_value("issuance_date", frappe.datetime.get_today());
			frm.set_value("incident_date", frappe.datetime.get_today());

			frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name").then((result) => {
				if (result && result.message && result.message.name) {
					frm.set_value("issuer", result.message.name);
				}
			});
		}
	},
	refresh: function (frm) {
		frm.trigger("toggle_visibility");
	},
	workflow_state: function (frm) {
		frm.trigger("toggle_visibility");
	},
	toggle_visibility: function (frm) {
		const privileged_roles = ["Shift Supervisor", "Site Supervisor", "HR Supervisor", "HR Manager", "General Manager"];
		const has_privileged_role = privileged_roles.some(role => frappe.user.has_role(role));
		const is_employee_only = frappe.user.has_role("Employee") && !has_privileged_role;

		// 1. salary_deduction_days and salary_deduction_amount visibility for "Employee" only users
		if (is_employee_only) {
			const show_deduction = frm.doc.workflow_state === "Employee Rejected";
			frm.set_df_property("salary_deduction_days", "hidden", !show_deduction);
			frm.set_df_property("salary_deduction_amount", "hidden", !show_deduction);
		} else {
			// If not "only Employee", show them
			frm.set_df_property("salary_deduction_days", "hidden", 0);
			frm.set_df_property("salary_deduction_amount", "hidden", 0);
		}

		// 2. Hide specific fields for Shift/Site Supervisors (exclude if user also has HR Supervisor role)
		const is_supervisor = (frappe.user.has_role("Shift Supervisor") || frappe.user.has_role("Site Supervisor")) && !frappe.user.has_role("HR Supervisor");
		if (is_supervisor) {
			frm.set_df_property("hr_remarks", "hidden", 1);
			frm.set_df_property("general_manager_decision", "hidden", 1);
			frm.set_df_property("legal_department_remarks", "hidden", 1);
		} else {
			// If not supervisor, ensure they are shown
			frm.set_df_property("hr_remarks", "hidden", 0);
			frm.set_df_property("general_manager_decision", "hidden", 0);
			frm.set_df_property("legal_department_remarks", "hidden", 0);
		}

		// 3. general_manager_decision and hr_remarks read-only logic
		const current_state = (frm.doc.workflow_state || "").trim();
		const is_legal_investigation = current_state === "Pending Legal Investigation";
		const is_gm_decision = current_state === "Pending GM Decision";

		if (frappe.user.has_role("General Manager") && is_legal_investigation) {
			frm.set_df_property("general_manager_decision", "read_only", 1);
		} else {
			frm.set_df_property("general_manager_decision", "read_only", 0);
		}

		if (is_gm_decision || is_legal_investigation) {
			frm.set_df_property("hr_remarks", "read_only", 1);
		} else {
			frm.set_df_property("hr_remarks", "read_only", 0);
		}

		// 4. supervisor_remarks read-only logic
		const supervisor_read_only_states = ["Pending HR Review", "Pending GM Decision", "Pending Legal Investigation"];
		if (supervisor_read_only_states.includes(current_state)) {
			frm.set_df_property("supervisor_remarks", "read_only", 1);
		} else {
			frm.set_df_property("supervisor_remarks", "read_only", 0);
		}

		// 5. salary_deduction_amount read-only logic based on damages
		const has_damage = frm.doc.company_damage || frm.doc.asset_damage || frm.doc.customer_property_damage || frm.doc.other_damages;
		frm.set_df_property("salary_deduction_amount", "read_only", !has_damage);

		// 6. employee_remarks read-only logic
		const employee_rejection_read_only_states = [
			"Pending Supervisor Review",
			"Pending HR Review",
			"Pending GM Decision",
			"Pending Legal Investigation"
		];
		if (employee_rejection_read_only_states.includes(current_state)) {
			frm.set_df_property("employee_remarks", "read_only", 1);
		} else {
			frm.set_df_property("employee_remarks", "read_only", 0);
		}
	},
	applied_penalty_code: function (frm) {
		frm.trigger("fetch_penalty_details");
	},
	applied_level: function (frm) {
		frm.trigger("fetch_penalty_details");
	},
	employee: function (frm) {
		frm.trigger("fetch_employee_details");
	},
	incident_date: function (frm) {
		frm.trigger("fetch_employee_details");
	},
	company_damage: function (frm) {
		frm.trigger("toggle_visibility");
	},
	asset_damage: function (frm) {
		frm.trigger("toggle_visibility");
	},
	customer_property_damage: function (frm) {
		frm.trigger("toggle_visibility");
	},
	other_damages: function (frm) {
		frm.trigger("toggle_visibility");
	},
	fetch_employee_details: function (frm) {
		if (!frm.doc.employee) return;

		// The site/project lookup reads Employee Schedule (roster data). It is done
		// server-side so raising a penalty does not require roster read permission -
		// the method checks access and returns only the two fields it needs.
		frappe.call({
			method: "one_fm.legal.doctype.penalty_and_investigation.penalty_and_investigation.get_incident_site_project",
			args: {
				employee: frm.doc.employee,
				incident_date: frm.doc.incident_date
			},
			callback: function (r) {
				if (r && r.message) {
					if (r.message.site) frm.set_value("operations_site", r.message.site);
					if (r.message.project) frm.set_value("project", r.message.project);
				}
			}
		});
	},
	fetch_penalty_details: function (frm) {
		const clear = () => {
			frm.set_value("action_type", "");
			frm.set_value("penalty_category", "");
			frm.set_value("salary_deduction_days", 0);
		};

		if (!frm.doc.applied_penalty_code || !frm.doc.applied_level) {
			clear();
			return;
		}

		frappe.model.with_doc("Penalty Code", frm.doc.applied_penalty_code, function () {
			let pc = frappe.get_doc("Penalty Code", frm.doc.applied_penalty_code);
			if (pc && pc.penalty_level) {
				// applied_level now holds the ordinal the Penalty Level rows are keyed
				// on ("1st"), so it is matched directly - the old numeric-to-ordinal map
				// would find nothing and silently clear the sanction (WI-001794).
				const row = pc.penalty_level.find(
					(d) => d.offence_level === frm.doc.applied_level
				);
				if (row) {
					frm.set_value("action_type", row.deduction_type);
					frm.set_value("salary_deduction_days", row.salary_deduction_days);
					// Mirrors the server: the category only covers these two actions.
					frm.set_value(
						"penalty_category",
						["Warning", "Salary Deduction"].includes(row.deduction_type)
							? row.deduction_type
							: ""
					);
				} else {
					clear();
				}
			}
		});
	}
});
