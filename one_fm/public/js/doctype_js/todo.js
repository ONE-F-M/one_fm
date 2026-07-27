frappe.ui.form.on('ToDo', {
    refresh: function(frm) {
      if (frm.is_new()) {
        frm.set_value("notify_allocated_to_via_email", 1);
        console.log("DDD");
      }
    }
})
