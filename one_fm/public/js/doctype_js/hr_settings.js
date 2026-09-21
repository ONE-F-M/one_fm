// Copyright (c) 2020, ONE FM and contributors
// For license information, please see license.txt

// WI-002601: Visa Costing is a flat 20 KWD work permit fee, so picking the Action fills
// the amount in rather than leaving the operator to remember a figure that never varies.
const VISA_COSTING_ACTION = 'Visa Costing';
const VISA_COSTING_WORK_PERMIT_AMOUNT = 20;

frappe.ui.form.on('GRD Renewal Extension Cost', {
	renewal_or_extend: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		// Only when the amount is empty: this is a default for a fresh row, not an
		// override of a rate somebody has deliberately set to something else.
		if(child.renewal_or_extend === VISA_COSTING_ACTION && !child.work_permit_amount){
			// set_value fires the work_permit_amount handler below, which totals the row.
			frappe.model.set_value(cdt, cdn, 'work_permit_amount', VISA_COSTING_WORK_PERMIT_AMOUNT);
		}
	},
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
