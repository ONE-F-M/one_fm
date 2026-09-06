frappe.listview_settings['ToDo'] = {
	onload: function(listview) {
		sync_my_google_tasks(listview)
		listen_for_sync_result(listview)
	}
};

// The button no longer performs the sync. It names the event that happened —
// the user asked for a sync — and the workflow engine decides which process
// answers to that name. What the sync then does lives in the process map, so
// it can change without this file changing.
const GOOGLE_TASK_SYNC_MESSAGE = 'ToDo_SyncGoogleTasks_Action';

const sync_my_google_tasks = function(listview) {
	listview.page.add_button(__('Sync My Google Tasks'), function() {
		frappe.call({
			method: 'one_bpmn.api.instance_api.trigger_process_by_message',
			args: { message_name: GOOGLE_TASK_SYNC_MESSAGE },
			callback: function (r) {
				if (!r.exc) {
					frappe.show_alert({
						message: __(r.message && r.message.message || 'Sync requested'),
						indicator: 'blue'
					});
				}
			},
			freeze: true,
			freeze_message: __('Requesting Google Task sync')
		});
	}, 'primary');
};

// The process runs on a worker, so its outcome cannot come back on the call
// above — it arrives later over the realtime channel the map's script tasks
// publish to. Refresh only on success: there is nothing new to show when the
// sync was refused.
const listen_for_sync_result = function(listview) {
	frappe.realtime.on('gsync_sync_result', function(data) {
		frappe.show_alert({
			message: __(data && data.message || 'Google Task sync finished'),
			indicator: (data && data.indicator) || 'green'
		});
		if (data && data.indicator === 'green') {
			listview.refresh();
		}
	});
};
