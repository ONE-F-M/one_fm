// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Subcontractor Exit", {
	refresh: function (frm) {
		// Ensure requested_by is always read-only
		frm.set_df_property("requested_by", "read_only", 1);

		// Add "Fetch All Employees" button in the Basic Information section
		if (!frm.doc.docstatus || frm.doc.docstatus === 0) {
			add_fetch_employees_button(frm);
		}
	},
});

function add_fetch_employees_button(frm) {
	// Remove any previously rendered button to avoid duplicates on refresh
	frm.fields_dict.subcontractor_exit_type.$wrapper
		.parent()
		.find(".fetch-employees-wrapper")
		.remove();

	let button_html = `
		<div class="fetch-employees-wrapper" style="margin-top: 10px; margin-bottom: 10px;">
			<button class="btn btn-primary btn-sm btn-fetch-employees">
				${__("Fetch All Employees")}
			</button>
			<p class="text-muted small" style="margin-top: 5px;">
				${__("Use this button for Bulk Employee Fetching")}
			</p>
		</div>
	`;

	frm.fields_dict.subcontractor_exit_type.$wrapper
		.parent()
		.append(button_html);

	frm.fields_dict.subcontractor_exit_type.$wrapper
		.parent()
		.find(".btn-fetch-employees")
		.on("click", function () {
			handle_fetch_employees(frm);
		});
}

function handle_fetch_employees(frm) {
	// Client-side validation: both fields must be filled
	if (!frm.doc.subcontractor_name || !frm.doc.operations_site) {
		frappe.msgprint({
			title: __("Validation"),
			indicator: "orange",
			message: __(
				"Please select both Subcontractor Name and Operations Site before fetching employees."
			),
		});
		return;
	}

	frappe.call({
		method: "one_fm.one_fm.doctype.subcontractor_exit.subcontractor_exit.fetch_subcontractor_employees",
		args: {
			subcontractor_name: frm.doc.subcontractor_name,
			operations_site: frm.doc.operations_site,
		},
		freeze: true,
		freeze_message: __("Fetching employees..."),
		callback: function (r) {
			if (r.message && r.message.length > 0) {
				// Clear existing rows to prevent duplication
				frm.clear_table("subcontract_exit_employee");

				r.message.forEach(function (emp) {
					let row = frm.add_child("subcontract_exit_employee");
					row.employee_id = emp.name;
					row.employee_name = emp.employee_name;
				});

				frm.refresh_field("subcontract_exit_employee");
				frappe.show_alert({
					message: __("{0} employee(s) fetched successfully.", [
						r.message.length,
					]),
					indicator: "green",
				});
			} else {
				frappe.msgprint({
					title: __("No Employees Found"),
					indicator: "blue",
					message: __(
						"No employees found matching the selected Subcontractor and Operations Site."
					),
				});
			}
		},
	});
}
