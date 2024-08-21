frappe.ui.form.on('Attendance Request', {
  refresh: (frm)=>{
    frm.trigger('check_workflow');
<<<<<<< HEAD
  },
	check_workflow: (frm)=>{
=======
    set_update_request_btn(frm);
  },
  validate: (frm) => {
    validate_from_date(frm);
  },
  check_workflow: (frm)=>{
>>>>>>> prod-staging
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
<<<<<<< HEAD
	employee: (frm)=>{
    // fetch approver
    if(frm.doc.employee){
      frappe.call({
        method: 'one_fm.utils.get_approver',
=======
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
>>>>>>> prod-staging
        args:{
          'employee':frm.doc.employee
        },
        callback: function(r) {
<<<<<<< HEAD
          if(r.message){
            frm.set_value("approver", r.message)
          }
        }
      });
    }
=======
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
>>>>>>> prod-staging
  }
});
