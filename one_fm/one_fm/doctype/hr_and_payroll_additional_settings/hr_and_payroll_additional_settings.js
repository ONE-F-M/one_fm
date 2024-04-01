// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('HR and Payroll Additional Settings', {
	refresh: function(frm) {
		set_filters(frm);
		
	},
	default_payroll_start_day: function(frm) {
		var payroll_end_day = ""
		if(frm.doc.default_payroll_start_day){
			payroll_end_day = get_payroll_end_day(frm.doc.default_payroll_start_day);
		}
		frm.set_value('default_payroll_end_day', payroll_end_day);
	},
	get_projects_not_configured_in_payroll_cycle: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'get_projects_not_configured_in_payroll_cycle_but_linked_in_employee',
			callback: function(r) {
				var message = "There is no project linked in employee but not configured"
				if(r && r.message && r.message.length > 0){
					if (r.message.length > 1){
						message = `${r.message.length} projects not configured in the cycle but linked in employee record:
						<ul style="padding-left: 20px; padding-top: 5px;">
							${r.message.map(d => `<li>${d.project}</li>`).join('')}
						</ul>`
					}
					else{
						message = `Project ${r.message.map(d => `${d.project}`).join('')} is not configured in the payroll cycle`
					}
				}
				frappe.msgprint(message);
			},
			freeze: true,
			freeze_message: __("Fetching the projects ..!")
		});
	},
	all_projects: function(frm) {
		toggle_projects_table(frm);
	},
	enable_missing_checkin_job: function(frm) {
		toggle_projects_functionality(frm);
	}
});

frappe.ui.form.on("Project Payroll Cycle", {
	payroll_start_day: function(frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		var payroll_end_day = ""
		if(row.payroll_start_day){
			payroll_end_day = get_payroll_end_day(row.payroll_start_day);
		}
		frappe.model.set_value(row.doctype, row.name, 'payroll_end_day', payroll_end_day);
	},
	project_payroll_cycle_add: function(frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		frm.script_manager.copy_from_first_row("project_payroll_cycle", row, ["payroll_start_day"]);
		if(!row.payroll_start_day){
			frappe.model.set_value(row.doctype, row.name, 'payroll_start_day', frm.doc.default_payroll_start_day);
		}
	}
});

var get_payroll_end_day = function(payroll_start_day) {
	if(payroll_start_day == 'Month Start'){
		return 'Month End';
	}
	if(payroll_start_day == 'Month End'){
		return '29 of Next Month';
	}
	else{
		return (parseInt(payroll_start_day) - 1).toString() + ' of Next Month'
	}
};

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
	frm.set_query("project", "project_payroll_cycle", function() {
		var project_added = [];
		if(frm.doc.project_payroll_cycle){
			frm.doc.project_payroll_cycle.forEach((item, i) => {
				if(item.project){
					project_added.push(item.project);
				}
			});
		}
		return {
			filters: {'name': ['not in', project_added]}
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