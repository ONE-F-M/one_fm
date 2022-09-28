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

frappe.ui.form.on('GRD Renewal Extension Cost', {
	work_permit_amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		caclulate_renewal_extension_cost_total(frm, child);
	},
	medical_insurance_amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		caclulate_renewal_extension_cost_total(frm, child);
	},
	residency_stamp_amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		caclulate_renewal_extension_cost_total(frm, child);
	},
	civil_id_amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		caclulate_renewal_extension_cost_total(frm, child);
	}
});

var caclulate_renewal_extension_cost_total = function(frm, child) {
	var total_cost = 0;
	if(child.work_permit_amount && child.work_permit_amount > 0){
		total_cost += child.work_permit_amount;
	}
	if(child.medical_insurance_amount && child.medical_insurance_amount > 0){
		total_cost += child.medical_insurance_amount;
	}
	if(child.residency_stamp_amount && child.residency_stamp_amount > 0){
		total_cost += child.residency_stamp_amount;
	}
	if(child.civil_id_amount && child.civil_id_amount > 0){
		total_cost += child.civil_id_amount;
	}
	frappe.model.set_value(child.doctype, child.name, 'total_amount', total_cost);
	frm.refresh_field('renewal_extension_cost');
};
