// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.listview_settings["Employee Resignation"] = {
	add_fields: ["project_allocation", "designation"],
	onload: function(listview) {
		listview.page.add_actions_menu_item(__('Create PR'), function() {
			let selected = listview.get_checked_items();
			if (selected.length === 0) {
				frappe.msgprint(__('Please select at least one Employee Resignation.'));
				return;
			}
			
			// Validate if all belong to the same project and designation
			let unique_projects = [...new Set(selected.map(row => row.project_allocation).filter(Boolean))];
			let unique_designations = [...new Set(selected.map(row => row.designation).filter(Boolean))];
			
			if (unique_projects.length > 1) {
				frappe.throw(__('All selected resignations MUST belong to the exact same Project! You selected mixed projects: ' + unique_projects.join(', ')));
			}
			if (unique_designations.length > 1) {
				frappe.throw(__('All selected resignations MUST belong to the exact same Designation! You selected mixed designations: ' + unique_designations.join(', ')));
			}
			
			let resignations = selected.map(row => row.name).join(",");
			
			frappe.route_options = {
				'reason': 'Exit',
				'designation': unique_designations[0] || '',
				'project_allocation': unique_projects[0] || ''
			};
			
			// Use local storage to seamlessly pass the bundled list to the child table because route_options struggles with JSON child tables natively
			localStorage.setItem('__bundled_resignations', resignations);
			
			frappe.set_route('Form', 'Project Manpower Request', 'new-project-manpower-request');
		});
	}
};
