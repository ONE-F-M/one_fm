// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('OKR Performance Profile', {
	refresh: function(frm) {
    set_objective_option_to_kr(frm);
	}
});

frappe.ui.form.on('OKR Performance Profile Objective', {
	objective: function(frm) {
    set_objective_option_to_kr(frm);
	}
});

var set_objective_option_to_kr = function(frm) {
  var options = [''];
  frm.doc.objectives.forEach((item, i) => {
    options[i+1] = item.objective
  });
  frappe.meta.get_docfield("OKR Performance Profile Key Result", "objective", frm.doc.name).options = options;
  frm.refresh_field('key_results');
};
