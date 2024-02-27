const USER_PERMS = {
    status: ["Open", "Working", "Pending Review"],
    priority: true,
    completed_by: false,
    completed_on: true,
    exp_start_date: false,
    exp_end_date: false,
    //due date - no such field
}

frappe.ui.form.on("Task", {
    refresh: function (frm) {
        set_perms(frm);  
        }
})

function set_perms(frm){
    frappe.xcall('one_fm.api.api.get_user_roles')
    .then(roles => {
        if (roles.includes("Projects User") && !roles.includes("Projects Manager")){
            // If task status is one of ["Open", "Working", "Pending Review"], keep the status field editable.
            // If task status is one of ["Overdue", "Template", "Completed", "Canceled"], make the status field read_only for Projects User.
            if(USER_PERMS["status"].includes(frm.doc.status)){
                frm.set_df_property("status", "options", USER_PERMS["status"]);
            } else {
                frm.set_df_property("status", "read_only", 1);
            }
            frm.set_df_property("priority", "read_only", USER_PERMS["priority"]);
            frm.set_df_property("completed_by", "read_only", USER_PERMS["completed_by"]);
            frm.set_df_property("completed_on", "read_only", USER_PERMS["completed_on"]);
            frm.set_df_property("exp_start_date", "read_only", USER_PERMS["exp_start_date"]);
            frm.set_df_property("exp_end_date", "read_only", USER_PERMS["exp_end_date"]);                
        } 
    })
}


