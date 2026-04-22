frappe.ui.form.on('Project Manpower Request', {
	onload: function(frm) {
		// Catch bundled multiple resignations from list view
		let bundled = localStorage.getItem('__bundled_resignations');
		if (frm.is_new() && bundled) {
			let names = bundled.split(",");
			frm.clear_table('resignation_links');
			names.forEach(name => {
				let row = frm.add_child('resignation_links');
				row.employee_resignation = name;
			});
			localStorage.removeItem('__bundled_resignations');
			// Defer refresh and trigger until after standard UI elements load
			setTimeout(() => {
			    frm.refresh_field('resignation_links');
			    frm.set_value('count', names.length);
			    frm.set_df_property('count', 'read_only', true);
			}, 500);
		}
	},
	
	refresh: function(frm) {
		setup_status_indicator(frm);
		
		// Hide the individual backend quantity fields to keep the form clean
		frm.toggle_display([
			'cancelled_qty',
			'managed_by_ot_qty',
			'managed_by_subcontractor_qty',
			'internal_transfer_qty',
			'resignation_withdrawal_qty',
			'historically_joined_qty'
		], false);

		// Set ERF filter
		frm.set_query('erf', function() {
			return {
				filters: {
					designation: frm.doc.designation,
					docstatus: 1,
					status: ['not in', ['Cancelled', 'Closed']]
				}
			};
		});

		// Restrict closed-by employee selection to active employees with matching designation
		frm.set_query('employee', 'fulfilled_by_employees', function() {
			return {
				filters: {
					designation: frm.doc.designation,
					status: 'Active'
				}
			};
		});
		
		// Track old state for reverting if needed
		frm.doc.__old_status = frm.doc.workflow_state;
		
		// Enforce Exit count read-only lock based purely on having records or reason	
		if (frm.doc.reason === 'Exit' && frm.doc.resignation_links && frm.doc.resignation_links.length > 0) {
		    frm.set_df_property('count', 'read_only', true);
		} else {
		    frm.set_df_property('count', 'read_only', false);
		}
		
		// Add Resignation Withdrawal button dynamically if applicable
		if (!frm.is_new() && frm.doc.employee_resignation && frm.doc.docstatus < 2) {
		    frm.add_custom_button(__("Resignation Withdrawal"), function () {
		        frappe.new_doc("Employee Resignation Withdrawal", {
		            employee_resignation: frm.doc.employee_resignation
		        });
		    });
		}
	},

	workflow_state: function(frm) {
		if (frm.doc.workflow_state === 'Completed') {
			let hired_count = frm.doc.fulfilled_by_employees ? frm.doc.fulfilled_by_employees.length : 0;
			let required = frm.doc.remaining_qty || 0;
			if (hired_count !== required) {
				frappe.msgprint({
					title: 'Action Blocked',
					indicator: 'red',
					message: `You cannot change the state to Completed. You must first link exactly <b>${required}</b> Employee(s) in the Closed By Employees table below.`
				});
				setTimeout(() => {
					frm.set_value('workflow_state', frm.doc.__old_status || 'In Process');
					setup_status_indicator(frm);
				}, 10);
				return;
			}
		}
		frm.doc.__old_status = frm.doc.workflow_state;
		setup_status_indicator(frm);
	},

	designation: function(frm) {
		frm.set_value('erf', '');
	},

	reason: function(frm) {
		if (frm.doc.reason === 'Exit') {
		    if (!frm.doc.count && (!frm.doc.resignation_links || frm.doc.resignation_links.length === 0)) {
			    frm.set_value('count', 1);
			}
		}
	},



	fulfilled_by_employees_add: function(frm) {
		calculate_hired_dynamically(frm);
	},
	fulfilled_by_employees_remove: function(frm) {
		calculate_hired_dynamically(frm);
	}
});

frappe.ui.form.on('PMR Resignation Link', {
    employee_resignation: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.project_allocation) {
            let projects = [];
            (frm.doc.resignation_links || []).forEach(r => {
                if (r.project_allocation) projects.push(r.project_allocation);
            });
            let unique_projects = [...new Set(projects)];
            
            if (unique_projects.length > 1) {
                frappe.msgprint({
                    title: 'Project Mismatch',
                    message: `All multiple resignations must strictly belong to the exact same Project! You cannot mix resignations from ${unique_projects.join(' and ')}.`,
                    indicator: 'red'
                });
                frappe.model.set_value(cdt, cdn, 'employee_resignation', '');
                return;
            }
            
            if (unique_projects.length === 1 && frm.doc.project_allocation !== unique_projects[0]) {
                frm.set_value('project_allocation', unique_projects[0]);
            }
        }
        
        let count = frm.doc.resignation_links ? frm.doc.resignation_links.length : 0;
        if (count > 0) {
            frm.set_value('count', count);
            frm.set_df_property('count', 'read_only', true);
        } else {
            frm.set_df_property('count', 'read_only', false);
        }
    },
    resignation_links_remove: function(frm) {
        let count = frm.doc.resignation_links ? frm.doc.resignation_links.length : 0;
        if (count > 0) {
            frm.set_value('count', count);
        } else {
            frm.set_df_property('count', 'read_only', false);
        }
    }
});

frappe.ui.form.on('PMR Fulfillment Action', {
	qty: function(frm, cdt, cdn) {
		validate_and_calculate_fulfillment(frm, cdt, cdn);
	},
	fulfillment_actions_remove: function(frm) {
		validate_and_calculate_fulfillment(frm);
	}
});

function validate_and_calculate_fulfillment(frm, cdt, cdn) {
	let count = frm.doc.count || 0;
	
	let fulfilled = 0;
	(frm.doc.fulfillment_actions || []).forEach(row => {
		fulfilled += (row.qty || 0);
	});

	if (fulfilled > count) {
		frappe.msgprint({
			title: 'Exceeds Allowed', 
			indicator: 'red', 
			message: `The total allocated fulfillment quantity (${fulfilled}) exceeds the original PMR count (${count}).`
		});
		
		if (cdt && cdn) {
			setTimeout(() => {
				frappe.model.set_value(cdt, cdn, 'qty', 0);
			}, 100);
			return; 
		}
	}
	
	let expected_remaining = Math.max(0, count - fulfilled);
	if (frm.doc.remaining_qty !== expected_remaining) {
		frm.set_value('remaining_qty', expected_remaining);
	}

	calculate_hired_dynamically(frm);
}

function calculate_hired_dynamically(frm) {
	let hired_count = frm.doc.fulfilled_by_employees ? frm.doc.fulfilled_by_employees.length : 0;
	let historically_joined = frm.doc.historically_joined_qty || 0;
	let expected_to_hire = Math.max(0, (frm.doc.remaining_qty || 0) - hired_count - historically_joined);
	frm.set_value('number_to_hire', expected_to_hire);
}

function setup_status_indicator(frm) {
	const status_colors = {
		"Draft": "red",
		"Pending OM Approval": "orange",
		"Awaiting Recruiter Approval": "light-blue",
		"In Process": "green",
		"Completed": "green",
		"Rejected": "red",
		"Cancelled": "red"
	};
	if (frm.doc.workflow_state) {
		frm.page.set_indicator(__(frm.doc.workflow_state), status_colors[frm.doc.workflow_state] || "gray");
	}
}

frappe.ui.form.on("Project Manpower Request", {
	setup: function(frm) {
		frm.set_query("erf", function() {
			return {
				filters: {
					docstatus: 1
				}
			};
		});
	},

});
