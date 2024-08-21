frappe.ui.form.on('Error Log', {
	refresh: function(frm) {
		frm.trigger('set_buttons');
	},
    set_buttons: function(frm) {
        if (frm.doc.issue_log){
            frm.add_custom_button(__('View Ticket'), () => {
                frappe.set_route('Form', 'HD Ticket', frm.doc.issue_log);
            });
            frm.change_custom_button_type('View Issue Log', null, 'warning');
        } else {
            frm.add_custom_button(__('Create HD Ticket'), () => {
                frappe.confirm('Are you sure you want to proceed?',
                    () => {
                        // action to perform if Yes is selected
                        frappe.call({
                            method: "one_fm.events.error_log.create_issue_log", //dotted path to server method
                            args: {error_log:frm.doc},
                            callback: function(r) {
                                // code snippet
                                frappe.msgprint(`HD Ticket  ${r.message} created successfully.`);
                                frm.reload_doc();
                            }
                        });
                    }, () => {
                        // action to perform if No is selected
                })
            });
            frm.change_custom_button_type('Create HD Ticket', null, 'primary');
        }
    }
});
