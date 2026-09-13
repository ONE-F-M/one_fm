frappe.listview_settings['ToDo'] = {
	onload: function(listview) {
		sync_my_google_tasks(listview)
	}
};

const sync_my_google_tasks = function(listview) {
	listview.page.add_button(__('Sync My Google Tasks'), function() {
        frappe.call({
			method: 'one_fm.overrides.todo.sync_my_google_tasks_with_todos',
			callback: function (r) {
				if (!r.exc) {
					frappe.msgprint(__(r.message || "Tasks Synched!"));
					listview.refresh();
				}
			},
			freeze: true,
			freeze_message: __('Syncing My Google Tasks')
		});
    }, 'primary');
};