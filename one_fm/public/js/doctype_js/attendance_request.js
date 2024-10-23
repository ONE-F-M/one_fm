frappe.ui.form.on('Attendance Request', {
  refresh: (frm)=>{
    frm.trigger('check_workflow');
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
  from_date: (frm) =>{
    validate_from_date(frm);
  },
});

validate_from_date = (frm) => {
	if (frm.doc.from_date < frappe.datetime.now_date()){
    if (frm.is_new()){
      frappe.throw("Atendance Request can not be created for past dates.")
    }else {
      frappe.throw("Atendance Request can not be updated to a past date.")
    }
	}
}