frappe.listview_settings['ToDo'] = {
	onload: function(listview) {
		sync_my_google_tasks(listview)
	}
};

const sync_my_google_tasks = function(listview) {
	listview.page.add_button(__('Sync My Google Tasks'), function() {
        frappe.show_alert({
            message: __('Syncing Google Tasks...'),
            indicator: 'blue'
        }, 3);
        frappe.call({
			method: 'one_bpmn.api.instance_api.start_process',
			args: {
				model_name: 'Sync Google Task to ERPNext ToDo'
			},
			callback: function (r) {
				if (!r.exc) {
					frappe.show_alert({
						message: __('Google Tasks synced successfully'),
						indicator: 'green'
					}, 5);
					listview.refresh();
				}
			}
		});
    }, 'primary');
};