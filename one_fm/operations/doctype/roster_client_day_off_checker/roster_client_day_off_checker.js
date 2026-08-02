// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Roster Client Day Off Checker", {
	refresh(frm) {
		// WI-001690: open the roster already filtered to this employee's allocation, so a
		// supervisor can correct the Client Day Off without rebuilding the filters by hand.
		if (!frm.is_new()) {
			frm.add_custom_button(__("Take Action"), () => open_filtered_roster(frm)).addClass(
				"btn-primary"
			);
		}

		// Set all fields as read-only except status for supervisors
		if (!frappe.user.has_role("System Manager")) {
			frm.set_df_property("employee", "read_only", 1);
			frm.set_df_property("date", "read_only", 1);
			frm.set_df_property("monthweek", "read_only", 1);
			frm.set_df_property("assigned_client_day_off_count", "read_only", 1);
			frm.set_df_property("client_day_off_explanation", "read_only", 1);
			frm.set_df_property("repeat_count", "read_only", 1);
		}
	},
});

function open_filtered_roster(frm) {
	frappe.call({
		method:
			"one_fm.operations.doctype.roster_client_day_off_checker.roster_client_day_off_checker.get_take_action_data",
		args: { checker: frm.doc.name },
		freeze: true,
		freeze_message: __("Opening roster..."),
		callback: function (r) {
			if (!r.message || !r.message.path) {
				frappe.msgprint(__("Unable to determine the roster filters for this record."));
				return;
			}

			// Same handling as the Contract Compliance Checker: build the URL from the
			// returned params, dropping any the server could not resolve.
			let url = new URL(r.message.path, window.location.origin);
			Object.entries(r.message.params || {}).forEach(function ([key, value]) {
				if (value) url.searchParams.set(key, value);
			});
			window.open(url.toString(), "_blank");
		},
	});
}
