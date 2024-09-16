// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('HR and Payroll Additional Settings', {
	refresh: function(frm) {
		set_filters(frm);
		
	},
	all_projects: function(frm) {
		toggle_projects_table(frm);
	},
	enable_missing_checkin_job: function(frm) {
		toggle_projects_functionality(frm);
	}
});


var set_filters = function(frm) {
	frm.set_query("holiday_compensatory_leave_type", function() {
		return {
			filters: {
				"is_compensatory": true
			}
		};
	});
	frm.set_query("holiday_additional_salary_component", function() {
		return {
			filters: {'type': 'Earning'}
		};
	});
	frm.set_query("exclude_salary_component", function() {
		return {
			filters: {'type': 'Deduction'}
		};
	});
};

var toggle_projects_table = (frm) => {
    var showProjects = frm.doc.all_projects === 1;

    frm.toggle_display("missing_checkin_projects", !showProjects);

    if (showProjects) {
        clear_child_table(frm);
    }
};

var toggle_projects_functionality = (frm) => {
    var enableMissingCheckin = frm.doc.enable_missing_checkin_job === 1;

    frm.toggle_display("missing_checkin_projects", enableMissingCheckin);
    frm.toggle_display("all_projects", enableMissingCheckin);
};


var clear_child_table = (frm) => {
	frm.doc.missing_checkin_projects = [];
}