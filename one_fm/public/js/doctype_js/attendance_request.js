frappe.ui.form.on('Attendance Request', {
  refresh: (frm)=>{
    frm.trigger('check_workflow');
  },
  validate: (frm) => {
    validate_from_date(frm);
  },
  onload: function(frm) {
    if (frm.is_new()) {
        // Set employee field based on current user
        if (!frm.doc.employee) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: {
                        user_id: frappe.session.user
                    },
                    fieldname: "name"
                },
                callback: function(response) {
                    if (response.message) {
                        frm.set_value("employee", response.message.name);
                    }
                }
            });
        }

      // Set from_date and to_date to today's date
      const today = frappe.datetime.get_today();
      if (!frm.doc.from_date) frm.set_value("from_date", today);
      if (!frm.doc.to_date) frm.set_value("to_date", today);
  }
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