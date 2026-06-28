frappe.ui.form.on('ToDo', {
    refresh: function(frm) {
        frm.set_df_property('notify_allocated_to_via_email', 'hidden', 1);
    }
})
