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
				var erf_btn = frm.add_custom_button(__('Create ERF'), function() {
	        create_erf(frm);
	      });
				erf_btn.addClass('btn-primary');
			}
			frm.add_custom_button(__('View ERF'), function() {
        view_erf(frm);
      });
			if(!frm.doc.erf_created){
				frm.add_custom_button(__('Create Project'), function() {
					create_project(frm);
				}).addClass('btn-primary');
			}
    }
	},
	reason_for_request: function(frm) {
		if(frm.doc.reason_for_request == 'UnPlanned'){
			frm.set_value('number_of_candidates_required', 1);
		}
		else{
			frm.set_value('total_salary_componsation', '');
		}
	},
	urgency_of_deployment: function(frm) {
		validate_date(frm);
	}
});

var create_project = function(frm) {
	var doc = frm.doc;
	var dialog = new frappe.ui.Dialog({
		title: __("Create Project"),
		fields: [
			{
				"fieldtype": "Data",
				"label": __("Project Name"),
				"fieldname": "project_name",
				"reqd": 1
			},
			{
				"fieldtype": "Link",
				"label": __("Project Template"),
				"fieldname": "project_template",
				"options": "Project Template"
			},
			{"fieldtype": "Column Break"},
			{
				"fieldtype": "Date",
				"label": __("Expected Start Date"),
				"fieldname": "expected_start_date"
			}
		]
	});
	dialog.set_primary_action(__('Create'), function() {
		var data = dialog.get_values();
		if(!data) return;
		frappe.call({
			method: "frappe.client.save",
			args: {
				doc: {
					doctype: 'Project',
					project_name: data.project_name,
					project_template: data.project_template,
					expected_start_date: data.expected_start_date
				}
			},
			callback:function(r){
				if(r.message){
					dialog.hide();
					frappe.show_alert(__("Project {0} Created.", [r.message.name]));
				}
			},
			freeze: true,
			freeze_message: __("Creating Project..")
		});
	})
	dialog.show();
};

var validate_date = function(frm) {
	if(frm.doc.urgency_of_deployment < frappe.datetime.now_date()){
		frm.set_value('urgency_of_deployment', '');
		frappe.throw(__("Urgency of Deployment cannot be before Today"));
	}
};

var create_erf = function(frm) {
  frappe.route_options = {"erf_request": frm.doc.name};
	frappe.new_doc("ERF");
};

var view_erf = function(frm) {
	frappe.route_options = {"erf_request": frm.doc.name};
	frappe.set_route("List", "ERF");
};
