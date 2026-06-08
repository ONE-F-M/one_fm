// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.listview_settings["Bonus Request"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Bulk Bonus Request"), function () {
			show_bulk_bonus_request_dialog(listview);
		});
	}
};


function show_bulk_bonus_request_dialog(listview) {
	let current_year = new Date().getFullYear();

	let dialog = new frappe.ui.Dialog({
		title: __("Bulk Bonus Request"),
		size: "large",
		fields: [
			// ---- Filters & Bonus Details Section ----
			{
				fieldtype: "Section Break",
				label: __("Filters & Bonus Details")
			},
			{
				fieldname: "department",
				fieldtype: "Link",
				label: __("Department"),
				options: "Department",
				reqd: 1,
				change() {
					let dept = dialog.get_value("department");
					let applicable_for_all = dialog.get_value("applicable_for_all");
					if (dept) {
						if (applicable_for_all) {
							fetch_employee_count(dialog, dept);
						} else {
							fetch_and_render_employees(dialog, dept);
						}
					} else {
						dialog._all_employees = [];
						dialog.fields_dict.employee_selection_html.$wrapper.html("");
					}
				}
			},
			{
				fieldname: "bonus_amount",
				fieldtype: "Currency",
				label: __("Bonus Amount"),
				reqd: 1,
				description: __("This amount will be applied to each selected employee.")
			},
			{
				fieldtype: "Column Break"
			},
			{
				fieldname: "effective_month",
				fieldtype: "Select",
				label: __("Effective Month"),
				options: "January\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
				reqd: 1
			},
			{
				fieldname: "effective_year",
				fieldtype: "Int",
				label: __("Effective Year"),
				default: current_year,
				reqd: 1
			},

			// ---- Justification Section ----
			{
				fieldtype: "Section Break",
				label: __("Justification")
			},
			{
				fieldname: "justification",
				fieldtype: "Select",
				label: __("Justification"),
				options: "\nExcellent Performance\nGrooming reward\nPerfect Attendance\nClient Appreciation\nLong Service\nSeasonal Bonus\nSpecial Recognition\nOther",
				reqd: 1,
				change() {
					let is_other = dialog.get_value("justification") === "Other";
					dialog.set_df_property("description", "hidden", !is_other);
					dialog.set_df_property("description", "reqd", is_other);
					if (!is_other) {
						dialog.set_value("description", "");
					}
				}
			},
			{
				fieldname: "description",
				fieldtype: "Small Text",
				label: __("Description"),
				hidden: 1
			},

			// ---- Employee Selection Section ----
			{
				fieldtype: "Section Break",
				label: __("Employee Selection")
			},
			{
				fieldname: "applicable_for_all",
				fieldtype: "Check",
				label: __("Applicable for all employees based on the filter"),
				description: __("If checked, all active employees in the selected department will be included."),
				change() {
					let applicable_for_all = dialog.get_value("applicable_for_all");
					let dept = dialog.get_value("department");
					if (applicable_for_all && dept) {
						fetch_employee_count(dialog, dept);
					} else if (applicable_for_all && !dept) {
						dialog._all_employees = [];
						dialog.fields_dict.employee_selection_html.$wrapper.html(
							`<div class="text-muted small p-3">
								<i class="fa fa-info-circle"></i>
								${__("Please select a Department first.")}
							</div>`
						);
					} else if (!applicable_for_all && dept) {
						dialog._all_employees = [];
						fetch_and_render_employees(dialog, dept);
					} else {
						dialog._all_employees = [];
						dialog.fields_dict.employee_selection_html.$wrapper.html("");
					}
				}
			},
			{
				fieldname: "employee_selection_html",
				fieldtype: "HTML",
				label: __("Employees")
			}
		],
		primary_action_label: __("Generate Draft Records"),
		primary_action(values) {
			let employees = get_selected_employees(dialog, values);
			if (!employees || employees.length === 0) {
				frappe.msgprint(__("No employees selected. Please select at least one employee or check 'Applicable for all'."));
				return;
			}

			frappe.call({
				method: "one_fm.one_fm.doctype.bonus_request.bonus_request.create_consolidated_bonus_request",
				args: {
					employees: JSON.stringify(employees),
					bonus_amount: values.bonus_amount,
					effective_month: values.effective_month,
					effective_year: values.effective_year,
					justification: values.justification,
					description: values.description || ""
				},
				freeze: true,
				freeze_message: __("Creating Bonus Request..."),
				callback: function (r) {
					dialog.hide();
					if (r.message) {
						frappe.set_route("Form", "Bonus Request", r.message);
					} else {
						listview.refresh();
					}
				}
			});
		}
	});

	dialog.show();
}


function fetch_employee_count(dialog, department) {
	frappe.call({
		method: "one_fm.one_fm.doctype.bonus_request.bonus_request.get_employees_for_bulk",
		args: { department: department },
		callback: function (r) {
			let count = (r.message || []).length;
			dialog._all_employees = (r.message || []).map(e => e.employee);
			dialog.fields_dict.employee_selection_html.$wrapper.html(
				`<div class="text-muted small p-3">
					<i class="fa fa-info-circle"></i>
					${__("{0} active employee(s) in this department will be included.", [count])}
				</div>`
			);
		}
	});
}


function fetch_and_render_employees(dialog, department) {
	frappe.call({
		method: "one_fm.one_fm.doctype.bonus_request.bonus_request.get_employees_for_bulk",
		args: { department: department },
		callback: function (r) {
			let employees = r.message || [];
			if (employees.length === 0) {
				dialog.fields_dict.employee_selection_html.$wrapper.html(
					`<div class="text-muted small p-3">
						<i class="fa fa-exclamation-circle"></i>
						${__("No active employees found in this department.")}
					</div>`
				);
				return;
			}

			let html = `
				<div class="mb-2 d-flex justify-content-between align-items-center">
					<span class="text-muted small">${__("{0} employee(s) found", [employees.length])}</span>
					<label class="small" style="cursor: pointer;">
						<input type="checkbox" class="bulk-select-all" checked> ${__("Select All")}
					</label>
				</div>
				<div style="max-height: 250px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: var(--border-radius);">
					<table class="table table-sm table-borderless mb-0">
						<thead>
							<tr class="text-muted small">
								<th style="width: 30px;"></th>
								<th>${__("Employee")}</th>
								<th>${__("Name")}</th>
								<th>${__("Designation")}</th>
							</tr>
						</thead>
						<tbody>
			`;

			employees.forEach(function (emp) {
				html += `
					<tr>
						<td><input type="checkbox" class="bulk-emp-check" data-employee="${emp.employee}" checked></td>
						<td class="small">${emp.employee}</td>
						<td class="small">${emp.employee_name || ""}</td>
						<td class="small">${emp.designation || ""}</td>
					</tr>
				`;
			});

			html += `</tbody></table></div>`;

			dialog.fields_dict.employee_selection_html.$wrapper.html(html);

			// Wire up Select All checkbox
			dialog.fields_dict.employee_selection_html.$wrapper
				.find(".bulk-select-all")
				.on("change", function () {
					let checked = $(this).prop("checked");
					dialog.fields_dict.employee_selection_html.$wrapper
						.find(".bulk-emp-check")
						.prop("checked", checked);
				});
		}
	});
}


function get_selected_employees(dialog, values) {
	if (values.applicable_for_all) {
		// Return stored employees from the background fetch
		if (dialog._all_employees && dialog._all_employees.length > 0) {
			return dialog._all_employees;
		}
		// Fallback: try checkboxes
		let all_employees = [];
		dialog.fields_dict.employee_selection_html.$wrapper
			.find(".bulk-emp-check")
			.each(function () {
				all_employees.push($(this).data("employee"));
			});
		return all_employees;
	}

	// Collect only checked employees
	let selected = [];
	dialog.fields_dict.employee_selection_html.$wrapper
		.find(".bulk-emp-check:checked")
		.each(function () {
			selected.push($(this).data("employee"));
		});
	return selected;
}
