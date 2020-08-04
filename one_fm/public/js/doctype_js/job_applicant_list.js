frappe.listview_settings['Job Applicant'] = {
	filters:[["status","!=","Rejected"]],
	onload: function(listview) {
		short_list_applicant(listview);
		reject_applicat_directly(listview);
	}
};

var short_list_applicant = function(listview) {
	listview.page.add_action_item(__("Shortlist"), function() {
		const docnames = listview.get_checked_items(true).map(docname => docname.toString());
		frappe.confirm(
			__('Shortlist {0} applicants ?', [docnames.length]),
			function(){
				// Yes
				listview.call_for_selected_items('one_fm.hiring.utils.update_applicant_status', { status_field: 'one_fm_applicant_status', status: "Shortlisted" });
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
