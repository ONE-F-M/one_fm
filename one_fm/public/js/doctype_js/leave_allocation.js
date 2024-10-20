frappe.ui.form.on("Leave Allocation", {
    refresh: function (frm) {
        frm.events.recalculate_annual_leaves(frm);
    },
    recalculate_annual_leaves: function (frm) {
        let {docstatus, leave_type, employee, name, leave_policy_assignment, from_date, to_date, new_leaves_allocated} = frm.doc;
        if(docstatus == 1 && leave_type == "Annual Leave") {
            frappe.db.get_list("Leave Allocation", {
                filters: {
                    "employee": employee, 
                    "leave_type": "Annual Leave"
                }, 
                fields: ["name"], 
                order_by: "to_date desc", 
                limit: 1
            }).then(res => {
                // Check if this is the most current leave policy assignment, then show the Recalculate button
                let today = moment().format("YYYY-MM-DD");
                if(res.length > 0 && res[0].name == name && (from_date <= today && today <= to_date)){
                    frm.add_custom_button(__("Recompute Annual Leave Earned"), function() {
                        frappe.xcall("one_fm.overrides.leave_allocation.update_annual_leave_allocation", 
                        {name, new_leaves_allocated, from_date, leave_policy_assignment, employee})
                        .then(res => {
                            frm.reload_doc();
                        })            
                    })
                }
            })
        }
    }
})