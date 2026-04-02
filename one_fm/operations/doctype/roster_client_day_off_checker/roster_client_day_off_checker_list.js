// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.listview_settings['Roster Client Day Off Checker'] = {
	onload: function(listview) {
		const allowed_roles = ['Operation Admin', 'Operations Manager', 'Projects Manager', 'System Manager'];
		if (frappe.user.has_role(allowed_roles)) {
			listview.page.add_inner_button(__('Create Checker for Today'), function() {
				frappe.call({
					method: 'one_fm.operations.doctype.roster_client_day_off_checker.roster_client_day_off_checker.generate_client_day_off_checker',
					callback: function(r) {
						frappe.show_alert({
							message: __('Client Day Off Checker generation started. This may take a few minutes.'),
							indicator: 'green'
						});
						setTimeout(function() {
							listview.refresh();
						}, 3000);
					},
					error: function(r) {
						frappe.show_alert({
							message: __('Failed to start checker generation'),
							indicator: 'red'
						});
					}
				});
			});
		}
	}
};
