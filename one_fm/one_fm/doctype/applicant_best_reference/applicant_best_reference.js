// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Applicant Best Reference', {
	refresh: function(frm) {
    if(frm.is_new()){
      frm.clear_table('best_references');
      var options = ['Best Boss', 'Best Colleague', 'Best Employee', 'Worst Boss', 'Worst Colleague', 'Worst Employee'];
      options.forEach((item) => {
        let reference = frappe.model.add_child(frm.doc, 'Applicant Best Reference Item', 'best_references');
        frappe.model.set_value(reference.doctype, reference.name, 'reference', item);
      });
      frm.refresh_field('best_references');
    }
	}
});
