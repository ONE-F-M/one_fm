frappe.listview_settings['Employee'] = {
	add_fields: ["status", "branch", "department", "designation","image"],
	filters: [["status","=", "Active"]],
	get_indicator: function(doc) {
		var indicator = [__(doc.status), frappe.utils.guess_colour(doc.status), "status,=," + doc.status];
		indicator[1] = {"Active": "green", "Court Case": "warning", "Absconding": "danger", "Left": "darkgrey"}[doc.status];
		return indicator;
	},
	onload: function(listview) {
		if (["HR Manager", "HR Supervisor", "Attendance Manager"].some(role => frappe.user.has_role(role))){
			listview.page.add_actions_menu_item(__('Toggle Auto-Attendance'), function() {
				const selected_docs = listview.get_checked_items();

				if (selected_docs.length > 0) {
					frappe.prompt([
						{
							label: 'Status',
							fieldname: 'status',
							fieldtype: 'Check',
							default: 0 
						}
					],
					function(values) {
						frappe.confirm(
							__('Do you really want to proceed ?'),
							function() {
								frappe.call({
									method: "one_fm.overrides.employee.toggle_auto_attendance",
									args: {
										employee_names: selected_docs.map(doc => doc.name),
										status: values.status,
										method: "POST"
									},
								}).then((response) => {
									if (response.status_code == 201) {
										frappe.msgprint(__(response.message));
										listview.refresh(); 
									} else {
										frappe.throw(response.message);
									}
								});
							},
							function() {
								frappe.msgprint(__('Action cancelled.'));
								listview.refresh();
							}
						);
					},
					__('Set Auto-Attendance Status'),
					__('Submit'));
				} else {
					frappe.msgprint(__('Please select at least one document'));
				}
			});
	}
    }
};

