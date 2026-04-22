// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Resignation Withdrawal", {
	onload: function(frm) {
		let show_date = !frm.doc.__islocal && frm.doc.workflow_state && frm.doc.workflow_state !== "Draft";
		frm.toggle_display("relieving_date", show_date);
	},

	refresh: function(frm) {
		let show_date = !frm.doc.__islocal && frm.doc.workflow_state && frm.doc.workflow_state !== "Draft";
		frm.toggle_display("relieving_date", show_date);

	    // Automatically fetch and map all employees from the parent resignation batch into the grid
		if (frm.doc.employee_resignation && frm.doc.__islocal) {
			// Ensure it only overrides on creation
			frappe.db.get_doc("Employee Resignation", frm.doc.employee_resignation)
				.then(doc => {
					frm.clear_table("employees");
					(doc.employees || []).forEach(row => {
					    // Only map employees who haven't already been seamlessly withdrawn
					    if (row.withdrawal_status !== "Approved") {
						    let child = frm.add_child("employees");
						    child.employee = row.employee;
						    child.employee_name = row.employee_name || "";
						}
					});
					frm.refresh_field("employees");
				});
		}

		// Bring the standard workflow button to the front
		setTimeout(() => {
			if (frm.page.custom_buttons) {
				let btn = frm.page.custom_buttons['Submit to Supervisor'];
				if (btn) {
					frm.page.change_custom_button_type('Submit to Supervisor', null, 'primary');
				}
			}
		}, 200);
	},

	validate: function(frm) {
	    // Robust UI validator catch to ensure missing attachments strictly block saving
	    let interacting = false;
	    if (frm.doc.employees && frm.doc.employees.length > 0) {
	        for (let row of frm.doc.employees) {
	            if (row.reason || row.attachment) {
	                interacting = true;
	                if (!row.reason || !row.attachment) {
	                    let emp_name = row.employee_name || row.employee;
	                    frappe.msgprint({
	                        title: __('Missing Elements'),
	                        message: __('You initiated a withdrawal for <b>{0}</b> but forgot something! You must provide BOTH a Reason and an Attachment to properly withdraw them.', [emp_name]),
	                        indicator: 'red'
	                    });
	                    frappe.validated = false;
	                    return;
	                }
	            }
	        }
	    }
	    
	    if (!interacting) {
	        frappe.msgprint({
                title: __('No Candidates'),
                message: __('You must provide a Reason and an Attachment for at least one candidate in the grid to submit a withdrawal.'),
                indicator: 'red'
            });
            frappe.validated = false;
	    }
	},

	before_workflow_action: function(frm) {
	    // Blanket catch for any active workflow traversal
	    let interacting = false;
		if (frm.doc.employees && frm.doc.employees.length > 0) {
			for (let row of frm.doc.employees) {
				if (row.reason || row.attachment) {
				    interacting = true;
    				if (!row.reason || !row.attachment) {
    					let emp_name = row.employee_name || row.employee;
    					
    					frappe.msgprint({
    						title: __('Missing Elements'),
    						message: __('You initiated a withdrawal for <b>{0}</b> but forgot something! You must provide BOTH a Reason and an Attachment to formally proceed.', [emp_name]),
    						indicator: 'red'
    					});
    
    					// Absolute guarantee to unlock the Frappe UI freeze right after Promise rejection
    					setTimeout(() => {
    						frappe.dom.unfreeze();
    					}, 100);
    
    					return Promise.reject("Missing Elements");
    				}
				}
			}
		}
		
		if (!interacting) {
		    frappe.msgprint({
                title: __('No Candidates'),
                message: __('You must provide a Reason and an Attachment for at least one candidate in the grid to proceed.'),
                indicator: 'red'
            });
            setTimeout(() => {
				frappe.dom.unfreeze();
			}, 100);
            return Promise.reject("No Candidates");
		}
	}
});
