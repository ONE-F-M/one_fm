frappe.listview_settings['Job Applicant'] = {
	filters:[["status","!=","Rejected"]],
	onload: function(listview) {
		update_applicant_status(listview, 'Filter Applicants', 'Filter {0} applicants ?', 'Applicant Filtered');
		update_applicant_status(listview, 'Schedule Interview', 'Schedule Interview for {0} applicants ?', 'Interview Scheduled');
		update_applicant_status(listview, 'Shortlist', 'Shortlist {0} applicants ?', 'Shortlisted');
		update_applicant_status(listview, 'Select Applicant', 'Selected {0} applicants ?', 'Selected');
		reject_applicat_directly(listview);
		send_magic_link_to_selected_applicants(listview, 'Career History')
		send_magic_link_to_selected_applicants(listview, 'Applicant Doc')
	}
};

var update_applicant_status = function(listview, btn_label, confirm_msg, status) {
	listview.page.add_action_item(__(btn_label), function() {
		const docnames = listview.get_checked_items(true).map(docname => docname.toString());
		frappe.confirm(
			__(confirm_msg, [docnames.length]),
			function(){
				// Yes
				listview.call_for_selected_items('one_fm.hiring.utils.update_applicant_status', { status_field: 'one_fm_applicant_status', status: status });
				listview.refresh();
			},
			function(){
				// No
			}
		);
	});
};

var send_magic_link_to_selected_applicants = function(listview, magic_link) {
	listview.page.add_action_item(__('Send '+magic_link), function() {
		const docnames = listview.get_checked_items(true).map(docname => docname.toString());
		frappe.confirm(
			__('Send {0} magic link to {1} applicants?', [magic_link, docnames.length]),
			function(){
				// Yes
				listview.call_for_selected_items('one_fm.hiring.utils.send_magic_link_to_selected_applicants', { magic_link: magic_link });
				listview.refresh();
			},
			function(){
				// No
			}
		);
	});
};

var reject_applicat_directly = function(listview) {
	listview.page.add_action_item(__("Reject"), function() {
		var dialog = new frappe.ui.Dialog({
			title: 'Reject Applicant',
			fields: [
				{fieldtype: "Data", label: "Reason for Rejection", fieldname: "reason_for_rejection", reqd: 1},
			],
			primary_action_label: __("Reject"),
			primary_action : function(){
				const docnames = listview.get_checked_items(true).map(docname => docname.toString());
				frappe.confirm(
					__('Reject {0} applicants ?', [docnames.length]),
					function(){
						// Yes
						listview.call_for_selected_items('one_fm.hiring.utils.update_applicant_status',
							{ status_field: 'status', status: "Rejected", reason_for_rejection: dialog.get_value('reason_for_rejection')});
						listview.refresh();
						dialog.hide();
					},
					function(){
						// No
						dialog.hide();
					}
				);
			}
		});
		dialog.show();
	});
}
