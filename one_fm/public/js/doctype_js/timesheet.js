frappe.ui.form.on('Timesheet', {
    employee: function(frm) {
        set_approver(frm)
    }
})

function set_approver(frm){
<<<<<<< HEAD
  frm.set_value("approver", "");
  if(frm.doc.employee && frm.doc.attendance_by_timesheet){
    frappe.call({
      method: 'one_fm.overrides.timesheet.fetch_approver',
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
=======
    if(frm.doc.employee){
        frappe.call({
            method: 'one_fm.overrides.timesheet.fetch_approver',
            args:{
                'employee':frm.doc.employee
            },
            callback: function(r) {
                if(r.message){
                    frm.set_value("approver", r.message);
                }
                else{
                  frm.set_value("approver", "");
                }
                frm.refresh_field("approver");
            },
            freeze: true
        });
    }
    else{
      frm.set_value("approver", "");
      frm.refresh_field("approver");
    }
>>>>>>> prod-staging
}
