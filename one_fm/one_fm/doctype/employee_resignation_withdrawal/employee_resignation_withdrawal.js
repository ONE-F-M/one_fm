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

                    // AUTO-FETCH Supervisor logic (Same as Resignation)
                    if (doc.site) {
                        frappe.db.get_value('Operations Site', doc.site, ['site_supervisor', 'operations_manager'])
                            .then(site_data => {
                                if (site_data && site_data.message) {
                                    if (site_data.message.operations_manager) {
                                        frm.set_value('operations_manager', site_data.message.operations_manager);
                                    }
                                    
                                    // Always prioritize Line Manager from the resignation itself if it was set
                                    if (doc.supervisor) {
                                        frm.set_value('supervisor', doc.supervisor);
                                    } else if (site_data.message.site_supervisor) {
                                        frappe.db.get_value('Employee', site_data.message.site_supervisor, 'user_id')
                                            .then(user_data => {
                                                if (user_data && user_data.message && user_data.message.user_id) {
                                                    frm.set_value('supervisor', user_data.message.user_id);
                                                }
                                            });
                                    }
                                }
                            });
                    } else if (doc.supervisor) {
                         frm.set_value('supervisor', doc.supervisor);
                    }
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

		if (!frm.doc.__islocal && frm.doc.employees && frm.doc.employees.length > 0) {
			let view_exit_tab = function(employee_id) {
				frappe.route_options = {"scroll_to": "exit"};
				frappe.set_route('Form', 'Employee', employee_id).then(() => {
					let ticks = 0;
					let focus_tab = setInterval(() => {
						ticks++;
						if (frappe.get_route()[0] === "Form" && frappe.get_route()[1] === "Employee" && cur_frm && cur_frm.docname === employee_id && cur_frm.layout) {
							
							// Trigger standard scroll mechanism which natively maps and activates Tab Breaks
							try {
								cur_frm.scroll_to_field("exit");
							} catch(e) {}
							
							// Directly target the framework's internal tab link reference for Bulletproof v14/v15 Bootstrap triggering
							if (cur_frm.fields_dict.exit && cur_frm.fields_dict.exit.$tab) {
								let $tab = cur_frm.fields_dict.exit.$tab;
								if (!$tab.hasClass("active") || !$tab.parent().hasClass("active")) {
									if (typeof $tab.tab === "function") {
										$tab.tab("show");
									}
									$tab[0].click();
								}
							}
						}
						// Secure the transition against Frappe's post-render jitter over 1.5 seconds
						if (ticks > 15) {
							clearInterval(focus_tab);
						}
					}, 100);
				});
			};

			if (frm.doc.employees.length === 1) {
				frm.remove_custom_button(__('Employee Exit Tab'), __('Employee Profiles'));
				frm.add_custom_button(__('Employee Exit Tab'), function() {
					view_exit_tab(frm.doc.employees[0].employee);
				}, __('Employee Profiles'));
			} else {
				frm.doc.employees.forEach(row => {
					let btn_label = row.employee_name || row.employee;
					frm.remove_custom_button(btn_label, __('Employee Profiles'));
					frm.add_custom_button(btn_label, function() {
						view_exit_tab(row.employee);
					}, __('Employee Profiles'));
				});
			}
		}

		if (frm.doc.employee_resignation) {
			frappe.db.get_value('Employee Resignation', frm.doc.employee_resignation, ['project_allocation', 'site_allocation', 'department'])
			.then(r => {
				if (r && r.message) {
					let project = r.message.project_allocation || "";
					let site = r.message.site_allocation || "";
					let dept = r.message.department || "";
					let is_corporate = (project.includes("Head Office") || site.includes("Head Office") || dept.includes("Head Office"));
					
					// Set dynamic property for Frappe's native Depends On engine
					frm.doc.is_corporate = is_corporate ? 1 : 0;
					
					// Force native re-evaluation
                    frm.refresh_fields();
				}
			});
		}
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
