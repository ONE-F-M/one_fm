// Copyright (c) 2024, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Default Shift Checker", {
    action_type: function(frm){
        if(frm.doc.action_type === "Update Employee's Roster"){
            reset_new_operations_shift_and_role_allocation(frm);
        }
    },
    new_shift_allocation: function(frm){
        frm.set_query("new_operations_role_allocation", function() {
            return {
                filters: {
                    shift: frm.doc.new_shift_allocation
                }
            };
        });
    },
    go_to_employees_roster: function(frm){
        if(frm.doc.action_type !== "Update Employee's Roster") return;

        const shiftsData = (frm.doc.is_day_off_reliever || frm.doc.is_weekend_reliever) ? frm.doc.reliever_assigned_to_the_same_shift : frm.doc.assigned_shifts_outside_default_shift;
        if(!Array.isArray(shiftsData) || !shiftsData.length) return;

        const targetShift = shiftsData[0] && shiftsData[0].operations_shift;
        if (!targetShift) return;

        frappe.db.get_value("Employee", { name: frm.doc.employee }, "employee_id", (r) => {
            if (r && r.employee_id) {
                const selectedDate = frm.doc.start_date ? new Date(frm.doc.start_date) : new Date();
                const targetMonth = selectedDate.getMonth() + 1; // Months are zero-based
                const targetYear = selectedDate.getFullYear();
                const url = `/app/roster?main_view=roster&sub_view=basic&roster_type=basic&employee_id=${r.employee_id}&shift=${targetShift}&month=${targetMonth}&year=${targetYear}`;
                window.open(url, '_blank');
            }
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
