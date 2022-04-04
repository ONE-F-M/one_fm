frappe.listview_settings['Issue'] = {
	onload: function(listview) {
		set_my_issue_filters(listview);
	}
};

var set_my_issue_filters = function(listview) {
	listview.page.add_menu_item(__("Set My Issue Filters"), function() {
		frappe.call({
			method: 'one_fm.utils.set_my_issue_filters',
			callback: function (r) {
				if (!r.exc) {
					listview.refresh();
				}
			},
			freeze: true,
			freeze_message: __('Set my Issue filters!')
		});
	});
}
