frappe.ui.form.on('Attendance Request', {
  refresh: (frm)=>{
    frm.trigger('check_workflow');
    set_update_request_btn(frm);
  },
  validate: (frm) => {
    validate_from_date(frm);
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
  },
  employee: (frm)=>{
    // Set approver
    frm.events.set_approver(frm);
  },
  from_date: (frm) =>{
    validate_from_date(frm);
  },
  set_approver: (frm) =>{
    if(frm.doc.employee){
      frappe.call({
        method: 'one_fm.utils.get_approver_user',
        args:{
          'employee':frm.doc.employee
        },
        callback: function(r) {
          let approver = "";
          if(r.message){
            approver = r.message;
          }
          frm.set_value("approver", approver);
          frm.refresh_field("approver");
        }
      });
    }
    else{
      frm.set_value("approver", "");
      frm.refresh_field("approver");
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

validate_from_date = (frm) => {
	if (frm.doc.from_date < frappe.datetime.now_date()){
		frappe.throw("Atendance Request can not be created for past dates.")
	}
}
