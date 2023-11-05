frappe.listview_settings['Job Offer'] = {
	filters:[["status","!=","Rejected"]],
	onload: function(listview) {
		add_remove_salary_advance(listview);
	}
};

var add_remove_salary_advance = function(listview) {
	listview.page.add_action_item(__("Add/Remove Salary Advance"), function() {
		var dialog = new frappe.ui.Dialog({
			title: 'Add/Remove Salary Advance',
			fields: [
				{fieldtype: "Check", label: "Provide Salary Advance", fieldname: "one_fm_provide_salary_advance"},
				{fieldtype: "Currency", label: "Amount", fieldname: "one_fm_salary_advance_amount" , depends_on: "one_fm_provide_salary_advance"},
				{fieldtype: "Check", label: "Notify Finance Department", fieldname: "notify_finance_department" , depends_on: "one_fm_provide_salary_advance"}
			],
			primary_action_label: __("Submit"),
			primary_action : function(){
				const docnames = listview.get_checked_items(true).map(docname => docname.toString());
				frappe.confirm(
					__('Are you sure to proceed for {0} Job Offer(s)?', [docnames.length]),
					function(){
						// Yes
						var args = {
							one_fm_provide_salary_advance: dialog.get_value('one_fm_provide_salary_advance') || false,
							one_fm_salary_advance_amount: dialog.get_value('one_fm_salary_advance_amount') || 0,
							notify_finance_department: dialog.get_value('notify_finance_department') || false
						}
						listview.call_for_selected_items('one_fm.hiring.utils.add_remove_salary_advance',{dialog: args});
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
