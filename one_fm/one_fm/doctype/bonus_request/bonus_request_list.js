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
			// ---- Filters Section ----
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
							// Fetch employees silently and store count for the confirm dialog
							frappe.call({
								method: "one_fm.one_fm.doctype.bonus_request.bonus_request.get_employees_for_bulk",
								args: { department: dept },
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
				reqd: 1
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

			// ---- Performance Criteria Section ----
			{
				fieldtype: "Section Break",
				label: __("Performance Criteria")
			},
			{
				fieldname: "increased_productivity",
				fieldtype: "Check",
				label: __("Increased Productivity"),
				description: __("Contribution to increased organizational productivity.")
			},
			{
				fieldname: "improved_work_processes",
				fieldtype: "Check",
				label: __("Improved Work Processes"),
				description: __("Development and/or implementation of improved work processes.")
			},
			{
				fieldname: "significant_effort",
				fieldtype: "Check",
				label: __("Significant Effort"),
				description: __("Significant effort well beyond a position's defined scope or working hours.")
			},
			{
				fieldtype: "Column Break"
			},
			{
				fieldname: "star_performer",
				fieldtype: "Check",
				label: __("Star Performer"),
				description: __("The employee must be a star performer or extraordinary in nature.")
			},
			{
				fieldname: "others",
				fieldtype: "Check",
				label: __("Others"),
				description: __("Extra explanation required"),
				change() {
					let is_others = dialog.get_value("others");
					dialog.set_df_property("justification", "hidden", !is_others);
					dialog.set_df_property("justification", "reqd", is_others);
					if (!is_others) {
						dialog.set_value("justification", "");
					}
				}
			},
			{
				fieldname: "justification",
				fieldtype: "Small Text",
				label: __("Justification"),
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
						// Fetch count and store employees
						frappe.call({
							method: "one_fm.one_fm.doctype.bonus_request.bonus_request.get_employees_for_bulk",
							args: { department: dept },
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

			// Validate at least one performance criteria
			if (!values.increased_productivity && !values.improved_work_processes &&
				!values.significant_effort && !values.star_performer && !values.others) {
				frappe.msgprint(__("Please select at least one Performance Criteria."));
				return;
			}

			frappe.confirm(
				__("This will create {0} individual Bonus Request record(s) in Draft state. Continue?", [employees.length]),
				function () {
					frappe.call({
						method: "one_fm.one_fm.doctype.bonus_request.bonus_request.create_bulk_bonus_requests",
						args: {
							employees: JSON.stringify(employees),
							bonus_amount: values.bonus_amount,
							effective_month: values.effective_month,
							effective_year: values.effective_year,
							posting_date: frappe.datetime.nowdate(),
							increased_productivity: values.increased_productivity || 0,
							improved_work_processes: values.improved_work_processes || 0,
							significant_effort: values.significant_effort || 0,
							star_performer: values.star_performer || 0,
							others: values.others || 0,
							justification: values.justification || ""
						},
						freeze: true,
						freeze_message: __("Queuing Bonus Request generation..."),
						callback: function () {
							dialog.hide();
							listview.refresh();
						}
					});
				}
			);
		}
	});

	dialog.show();
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
