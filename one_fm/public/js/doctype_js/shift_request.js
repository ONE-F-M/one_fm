// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Request', {
	refresh: function(frm) {
		set_update_request_btn(frm);
	},
	employee: function(frm) {
		set_approver(frm)
	}
});

function set_update_request_btn(frm) {
	if(frm.doc.docstatus == 1 && frm.doc.workflow_state == 'Approved' && !frm.doc.update_request){
		frappe.db.get_value('Employee', frm.doc.employee, 'user_id', function(r) {
			if((frappe.session.user == frm.doc.approver) || (r.user_id && frappe.session.user == r.user_id)){
				frm.add_custom_button(__('Update Request'), function() {
					update_request(frm);
				});
			}
		});
	}
};

function update_request(frm) {
	var dialog = new frappe.ui.Dialog({
		title: 'Update Request',
		fields: [
			{
				fieldtype: "Date", label: "From Date", fieldname: "from_date",
				onchange: function () {
					dialog.set_values({
						'to_date': dialog.get_value('from_date')
					});
				}
			},
			{fieldtype: "Date", label: "To Date", fieldname: "to_date"},
		],
		primary_action_label: __("Update"),
		primary_action : function(){
			frappe.confirm(
				__('Are you sure to proceed?'),
				function(){
					// Yes
					frappe.call({
						method: 'one_fm.api.doc_methods.shift_request.update_request',
						args: {
							shift_request: frm.doc.name,
							from_date: dialog.get_value('from_date'),
							to_date: dialog.get_value('to_date'),
						},
						callback: function(r) {
							if(!r.exc) {
								frm.reload_doc();
							}
						},
						freaze: true,
						freaze_message: __("Update Request ..")
					});
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
};

function set_approver(frm){
    if(frm.doc.employee){
        frappe.call({
            method: 'one_fm.api.doc_methods.shift_request.fetch_approver',
            args:{
                'employee':frm.doc.employee
            },
            callback: function(r) {
                if(r.message){
                    frm.set_value("approver",r.message)
                }
            }
        });
    }
}
