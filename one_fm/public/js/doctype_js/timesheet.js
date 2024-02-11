frappe.ui.form.on('Timesheet', {
    employee: function(frm) {
        set_approver(frm)
    },
    attendance_by_timesheet: function(frm) {
        set_approver(frm)
    }
})

function set_approver(frm){
    if(frm.doc.employee && frm.doc.attendance_by_timesheet){
        frappe.call({
            method: 'one_fm.overrides.timesheet.fetch_approver',
            args:{
                'employee':frm.doc.employee
            },
            callback: function(r) {
                if(r.message){
                    frm.set_value("approver",r.message)
                }
            }
        });
    }
}


frappe.ui.form.on('Timesheet Detail', {
    from_time: function(frm, cdt, cdn) {
        var child = locals[cdt][cdn];
        if(!frm.doc.__islocal){
            frappe.xcall('one_fm.utils.get_user_timezone').then(tz => {
                // Convert from_time from User Timezone to AST("Asia/Kuwait")
                let from_time = moment.tz(child.from_time, tz);
                let from_time_in_ast = moment().tz(from_time, "Asia/Kuwait");

                let today = `${moment().format("YYYY-MM-DD")} 00:00:00`; 
                let now_time = moment.tz(today, "Asia/Kuwait");
                if(from_time_in_ast < now_time){
                    frappe.throw(__("Please note that timesheets cannot be created for a previous date."));
                }    
            })
        }
    },
    to_time: function(frm, cdt, cdn) {
        var child = locals[cdt][cdn];
        if(!frm.doc.__islocal){
            frappe.xcall('one_fm.utils.get_user_timezone').then(tz => {
                // Convert to_time from User Timezone to AST("Asia/Kuwait")
                let to_time = moment.tz(child.to_time, tz);
                let to_time_in_ast = moment().tz(to_time, "Asia/Kuwait");

                let today = `${moment().format("YYYY-MM-DD")} 00:00:00`; 
                let now_time = moment.tz(today, "Asia/Kuwait");
                if(to_time_in_ast < now_time){
                    frappe.throw(__("Please note that timesheets cannot be created for a previous date."));                
                }
            })              
        }
    }
})
