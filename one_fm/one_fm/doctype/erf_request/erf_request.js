// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('ERF Request', {
	onload: function(frm) {
		if(frm.is_new()){
			frm.set_value('department_manager', frappe.session.user);
		}
	},
	refresh: function(frm) {
    if(frm.doc.docstatus == 1 && frm.doc.status == 'Accepted'){
			if(frappe.user.name == frm.doc.department_manager){
				frm.add_custom_button(__('Create ERF'), function() {
	        create_erf(frm);
	      });
			}
			frm.add_custom_button(__('View ERF'), function() {
        view_erf(frm);
      });
    }
	},
	reason_for_request: function(frm) {
		if(frm.doc.reason_for_request == 'UnPlanned'){
			frm.set_value('number_of_candidates_required', 1);
			frm.set_df_property('number_of_candidates_required', 'read_only', true);
		}
		else{
			frm.set_df_property('number_of_candidates_required', 'read_only', false);
			frm.set_value('total_salary_componsation', '');
			frm.set_value('other_cost_to_company', '');
		}
	}
});

var create_erf = function(frm) {
  frappe.route_options = {"erf_request": frm.doc.name};
	frappe.new_doc("ERF");
};

var view_erf = function(frm) {
	frappe.route_options = {"erf_request": frm.doc.name};
	frappe.set_route("List", "ERF");
};
