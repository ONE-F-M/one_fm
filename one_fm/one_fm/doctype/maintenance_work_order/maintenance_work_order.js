// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Maintenance Work Order", {
	refresh: function (frm) {
		// Apply priority filter whenever the form is loaded or refreshed
		apply_priority_filter(frm);

		// Enforce read-only on location fields (server-side enforcement is primary)
		set_location_fields_read_only(frm);

		// Expose the technician's first check-in action
		add_check_in_button(frm);
	},

	sla_master: function (frm) {
		// Re-apply priority filter when SLA Master changes
		apply_priority_filter(frm);
	},

	object: function (frm) {
		// When object changes, clear dependent fields so before_save re-fetches
		if (!frm.doc.object) {
			frm.set_value("object_name", "");
			frm.set_value("object_category", "");
			frm.set_value("space", "");
			frm.set_value("maintenance_floor", "");
			frm.set_value("building", "");
			frm.set_value("operations_site", "");
			frm.set_value("project", "");
			frm.set_value("client", "");

			// Clear child tables that depend on object
			frm.clear_table("object_parts");
			frm.clear_table("object_maintenance_checklist_items");
			frm.refresh_fields();
		}
	},

	assigned_maintenance_team: function (frm) {
		// When team changes, clear team members so before_save re-fetches
		if (!frm.doc.assigned_maintenance_team) {
			frm.set_value("maintenance_team_lead", "");
			frm.clear_table("object_maintenance_team");
			frm.refresh_fields();
		}
	},
});

function apply_priority_filter(frm) {
	/**
	 * Story 7: Dynamic Priority Filter
	 *
	 * When an SLA is linked, filter the Priority field to only show priorities
	 * that are configured in the SLA's Maintenance SLA Priority child table.
	 * When no SLA is linked, show all available priorities.
	 */
	if (frm.doc.sla_master) {
		// Fetch valid priorities via whitelisted server method
		frappe.call({
			method: "one_fm.one_fm.doctype.maintenance_work_order.maintenance_work_order.get_sla_priorities",
			args: { sla_master: frm.doc.sla_master },
			callback: function (r) {
				if (r && r.message && r.message.length > 0) {
					frm.set_query("priority", function () {
						return {
							filters: {
								name: ["in", r.message],
							},
						};
					});
				} else {
					// No priorities configured — remove filter
					frm.set_query("priority", function () {
						return {};
					});
				}
			},
		});
	} else {
		// No SLA linked — show all priorities
		frm.set_query("priority", function () {
			return {};
		});
	}
}

function add_check_in_button(frm) {
	/**
	 * First Check In: stamps the exact time the technician starts the job.
	 *
	 * Shown only for a saved, not-yet-submitted Preventive Maintenance Work Order
	 * that has not been checked in. The server records the timestamp once and
	 * evaluates the SLA Response Status.
	 */
	if (
		frm.is_new() ||
		frm.doc.docstatus !== 0 ||
		frm.doc.maintenance_type !== "Preventive Maintenance" ||
		frm.doc.first_check_in_time
	) {
		return;
	}

	frm.add_custom_button(__("Check In"), function () {
		frappe.call({
			method: "one_fm.one_fm.doctype.maintenance_work_order.maintenance_work_order.check_in",
			args: { work_order: frm.doc.name },
			freeze: true,
			freeze_message: __("Recording check-in..."),
			callback: function (r) {
				if (r && r.message) {
					frappe.show_alert({
						message: __("First check-in recorded."),
						indicator: "green",
					});
					frm.reload_doc();
				}
			},
		});
	});
}

function set_location_fields_read_only(frm) {
	/**
	 * Story 3: Read-only enforcement for location chain fields.
	 * These are also set read_only in JSON but we reinforce it client-side.
	 */
	var read_only_fields = [
		"object_name",
		"object_category",
		"space",
		"maintenance_floor",
		"building",
		"operations_site",
		"project",
		"client",
	];

	read_only_fields.forEach(function (field) {
		frm.set_df_property(field, "read_only", 1);
	});
}
