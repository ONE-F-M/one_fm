frappe.listview_settings['ToDo'] = {
	onload: function(listview) {
		sync_my_google_tasks(listview)
	}
};

const sync_my_google_tasks = function(listview) {
	listview.page.add_button(__('Sync My Google Tasks'), function() {
        frappe.call({
			method: 'one_bpmn.api.instance_api.start_process',
			args: {
				model_name: 'Sync Google Task to ERPNext ToDo'
			},
			callback: function (r) {
				if (!r.exc) {
					frappe.msgprint(__('Google Task sync process started'));
					listview.refresh();
				}
			},
			freeze: true,
			freeze_message: __('Syncing My Google Tasks')
		});
    }, 'primary');
};