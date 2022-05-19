// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('GRD Settings', {
  create_preparation_record_manually: function(frm) {
    frappe.call({
      method: 'one_fm.grd.doctype.preparation.preparation.create_preparation_record',
      callback: function(r) {
        if(!r.exc){
          frappe.msgprint(__("Preparation record created succssefully!"));
          frm.reload_doc();
        }
      },
      freeze: true,
      freeze_message: (__("Creating Preparation..!"))
    });
  }
});
