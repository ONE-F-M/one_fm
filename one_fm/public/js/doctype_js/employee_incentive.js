frappe.ui.form.on('Employee Incentive', {
	refresh: function(frm) {
		frm.set_df_property('incentive_amount', 'read_only', true);
		frm.trigger('set_earning_component_filter');
	},
	set_earning_component_filter: function(frm) {
		frm.set_query("salary_component", function() {
			return {
				filters: {type: "earning"}
			};
		});
	},
	employee: function(frm) {
		frm.trigger('set_wage');
	},
	rewarded_by: function(frm) {
		frm.trigger('set_earning_component_filter');
		frm.trigger('set_wage_and_wage_factor_label');
		frm.trigger('set_wage');
		frm.trigger('calculate_incentive_amount');
	},
	wage_factor: function(frm) {
		frm.trigger('calculate_incentive_amount');
	},
	wage: function(frm) {
		frm.trigger('calculate_incentive_amount');
	},
	payroll_date: function(frm) {
		frm.trigger('set_wage');
	},
	set_wage: function(frm) {
		if(frm.doc.rewarded_by && frm.doc.employee){
			frappe.call({
				method: 'one_fm.one_fm.payroll_utils.get_wage_for_employee_incentive',
				args: {
					employee: frm.doc.employee,
					rewarded_by: frm.doc.rewarded_by,
					on_date: frm.doc.payroll_date
				},
				callback: function(r) {
					if(r.message && r.message > 0){
						frm.set_value('wage', r.message);
					}
				},
				freaze: true,
				freaze_message: __("Get Wage ..")
			});
		}
	},
	calculate_incentive_amount: function(frm) {
		var incentive_amount = 0;
		if(frm.doc.rewarded_by && frm.doc.wage_factor && frm.doc.wage){
			incentive_amount = frm.doc.wage * frm.doc.wage_factor;
			if (frm.doc.rewarded_by == 'Percentage of Monthly Wage'){
				incentive_amount = incentive_amount / 100;
			}
		}
		frm.set_value('incentive_amount', incentive_amount);
	},
	set_wage_and_wage_factor_label: function(frm) {
		if(frm.doc.rewarded_by == 'Percentage of Monthly Wage'){
			frm.set_df_property('wage', 'label', 'Monthly Wage');
			frm.set_df_property('wage_factor', 'label', 'Percentage of Monthly Wage');
		}
		else if(frm.doc.rewarded_by == 'Number of Daily Wage'){
			frm.set_df_property('wage', 'label', 'Daily Wage');
			frm.set_df_property('wage_factor', 'label', 'Number of Daily Wage');
		}
	}
});
