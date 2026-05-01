frappe.ui.form.on("Penalty And Investigation", {
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
			frm.set_df_property("legal_findings", "hidden", 1);
		} else {
			// If not supervisor, ensure they are shown
			frm.set_df_property("hr_remarks", "hidden", 0);
			frm.set_df_property("general_manager_decision", "hidden", 0);
			frm.set_df_property("legal_findings", "hidden", 0);
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

		// 4. supervisor_remarks and evidence read-only logic
		const supervisor_read_only_states = ["Pending HR Review", "Pending GM Decision", "Pending Legal Investigation"];
		if (supervisor_read_only_states.includes(current_state)) {
			frm.set_df_property("supervisor_remarks", "read_only", 1);
			frm.set_df_property("evidence", "read_only", 1);
		} else {
			frm.set_df_property("supervisor_remarks", "read_only", 0);
			frm.set_df_property("evidence", "read_only", 0);
		}

		// 5. salary_deduction_amount read-only logic based on damages
		const has_damage = frm.doc.company_damage || frm.doc.asset_damage || frm.doc.customer_property_damage || frm.doc.other_damages;
		frm.set_df_property("salary_deduction_amount", "read_only", !has_damage);

		// 6. employee_rejection_remarks read-only logic
		const employee_rejection_read_only_states = [
			"Pending Supervisor Review",
			"Pending HR Review",
			"Pending GM Decision",
			"Pending Legal Investigation"
		];
		if (employee_rejection_read_only_states.includes(current_state)) {
			frm.set_df_property("employee_rejection_remarks", "read_only", 1);
		} else {
			frm.set_df_property("employee_rejection_remarks", "read_only", 0);
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

		let set_details = (site, project) => {
			if (site) frm.set_value("location", site);
			if (project) frm.set_value("project", project);
		};

		if (frm.doc.incident_date) {
			frappe.db.get_list("Employee Schedule", {
				filters: {
					employee: frm.doc.employee,
					date: frm.doc.incident_date,
					employee_availability: "Working"
				},
				fields: ["site", "project"],
				limit: 1
			}).then(res => {
				if (res && res.length > 0) {
					set_details(res[0].site, res[0].project);
				} else {
					// Fallback to Employee Master
					frappe.db.get_value("Employee", frm.doc.employee, ["site", "project"], (r) => {
						if (r) set_details(r.site, r.project);
					});
				}
			});
		} else {
			// No incident date, fallback to master
			frappe.db.get_value("Employee", frm.doc.employee, ["site", "project"], (r) => {
				if (r) set_details(r.site, r.project);
			});
		}
	},
	fetch_penalty_details: function (frm) {
		if (!frm.doc.applied_penalty_code || !frm.doc.applied_level) {
			frm.set_value("deduction_type", "");
			frm.set_value("salary_deduction_days", 0);
			return;
		}

		frappe.model.with_doc("Penalty Code", frm.doc.applied_penalty_code, function () {
			let pc = frappe.get_doc("Penalty Code", frm.doc.applied_penalty_code);
			if (pc && pc.penalty_level) {
				const level_map = {
					"1": "1st",
					"2": "2nd",
					"3": "3rd",
					"4": "4th",
					"5": "5th"
				};
				const target_level = level_map[frm.doc.applied_level];
				const row = pc.penalty_level.find(d => d.offence_level === target_level);
				if (row) {
					frm.set_value("deduction_type", row.deduction_type);
					frm.set_value("salary_deduction_days", row.salary_deduction_days);
				} else {
					frm.set_value("deduction_type", "");
					frm.set_value("salary_deduction_days", 0);
				}
			}
		});
	}
});
