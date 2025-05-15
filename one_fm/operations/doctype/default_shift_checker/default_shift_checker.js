// Copyright (c) 2024, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on("Default Shift Checker", {
    action_type: function(frm){
        reset_new_operations_shift_and_role_allocation(frm)
    },
    new_shift_allocation: function(frm){
        frm.set_query("new_operations_role_allocation", function() {
            return {
                filters: {
                    shift: frm.doc.new_shift_allocation
                }
            };
        });
    }
});

function reset_new_operations_shift_and_role_allocation(frm){
	frm.set_value({
        "new_shift_allocation": "",
        "new_operations_role_allocation": ""
    })
    frm.refresh_fields()
}
