// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Incentive Tool", {
	refresh: function(frm) {
		frm.disable_save();
		frm.trigger('set_earning_component_filter');
	},
	department: function(frm) {
		load_employees(frm);
	},
	branch: function(frm) {
		load_employees(frm);
	},
	company: function(frm) {
		load_employees(frm);
	},
	rewarded_by: function(frm) {
		frm.trigger('set_wage_factor_label');
	},
	set_earning_component_filter: function(frm) {
		frm.set_query("salary_component", function() {
			return {
				filters: {type: "earning"}
			};
		});
	},
	set_wage_factor_label: function(frm) {
		if(frm.doc.rewarded_by == 'Percentage of Monthly Wage'){
			frm.set_df_property('wage_factor', 'label', 'Percentage of Monthly Wage');
		}
		else if(frm.doc.rewarded_by == 'Number of Daily Wage'){
			frm.set_df_property('wage_factor', 'label', 'Number of Daily Wage');
		}
	},
	calculate_incentive: function(frm) {
		if(frm.doc.employee_incentives && frm.doc.rewarded_by && frm.doc.wage_factor && frm.doc.salary_component){
			frappe.call({
				doc: frm.doc,
				method: 'update_incentive_details',
				callback: function(r) {
					if(!r.exc){
						frm.refresh_field('employee_incentives');
					}
				},
				freaze: true,
				freaze_message: __('Calculating Incentive ...!')
			});
		}
	},
	create_incentive: function(frm) {
		if(frm.doc.employee_incentives && frm.doc.rewarded_by && frm.doc.wage_factor && frm.doc.salary_component){
			frappe.call({
				doc: frm.doc,
				method: 'create_employee_incentive',
				callback: function(r) {
					if(!r.exc && r.message){
						frappe.show_alert(__("Created {0} Employee Incentive(s)", [r.message]));
					}
				},
				freaze: true,
				freaze_message: __('Creating Incentive ...!')
			});
		}
	}
});

var load_employees = function(frm) {
	if(frm.doc.department) {
		frappe.call({
			method: "one_fm.one_fm.doctype.employee_incentive_tool.employee_incentive_tool.get_employees",
			args: {
				department: frm.doc.department,
				branch: frm.doc.branch,
				company: frm.doc.company
			},
			callback: function(r) {
				var data = r.message;
				data.forEach((item, i) => {
					var employee_incentive = frm.add_child('employee_incentives');
					employee_incentive.employee = item.employee;
					employee_incentive.employee_name = item.employee_name;
				});
				frm.refresh_fields();
			}
		});
	}
};
