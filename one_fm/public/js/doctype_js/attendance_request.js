frappe.ui.form.on('Attendance Request', {
    refresh: (frm)=>{
      frm.trigger('check_workflow');
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
