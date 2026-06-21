frappe.listview_settings['ToDo'] = {
	onload: function(listview) {
		sync_my_google_tasks(listview)
	}
};

const sync_my_google_tasks = function(listview) {
	listview.page.add_button(__('Sync My Google Tasks'), function() {
        frappe.call({
			method: 'one_bpmn.api.instance_api.start_process_async',
			args: {
				model_name: 'Sync Google Task to ERPNext ToDo'
			},
			callback: function (r) {
				if (!r.exc) {
					frappe.show_alert({
						message: __('Google Task sync started in background'),
						indicator: 'green'
					}, 5);
				}
			}
		});
    }, 'primary');
};