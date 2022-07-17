frappe.ui.form.on('Attendance Request', {
    refresh: (frm)=>{
      frm.trigger('check_workflow');
			set_update_request_btn(frm);
    },
    check_workflow: (frm)=>{
      if(frm.doc.workflow_state=='Pending Approval'){
        // Disable action button/worklow if not approver
        frm.call('reports_to').then(res=>{
          if(!res.message){
            $('.actions-btn-group').hide();
            frm.disable_form();
          }
        })
      }
    }
});

function set_update_request_btn(frm) {
	if(frm.doc.docstatus == 1 && frm.doc.workflow_state == 'Approved' && !frm.doc.update_request){
		if(frappe.user.has_role('Shift Supervisor')){
			frm.add_custom_button(__('Update Request'), function() {
				update_request(frm);
			});
		}
	}
};

function update_request(frm) {
	var dialog = new frappe.ui.Dialog({
		title: 'Update Request',
		fields: [
			{fieldtype: "Date", label: "From Date", fieldname: "from_date", reqd: true},
			{fieldtype: "Date", label: "To Date", fieldname: "to_date", reqd: true},
		],
		primary_action_label: __("Update"),
		primary_action : function(){
			frappe.confirm(
				__('Are you sure to proceed?'),
				function(){
					// Yes
					frappe.call({
						method: 'one_fm.overrides.attendance_request.update_request',
						args: {
							attendance_request: frm.doc.name,
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
