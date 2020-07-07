frappe.ui.form.on('Notification Log', {
    refresh: function(frm){
        checkin_events(frm);
    },
});


function checkin_events(frm){
    $('#punch-error.punch-in').on('click', function(e){
        console.log(e);
        frappe.msgprint(__("Please inform your in-line supervisor in person or via direct call about the issue and confirm attendance."))
        make_support_issue(frm, "in");
    })
    $('#punch-error.punch-out').on('click', function(e){
        console.log(e.target);
        frappe.msgprint(__("Please inform your in-line supervisor in person or via direct call about the issue and confirm your exit."))
        make_support_issue(frm, "out");
    })
    $('.no-punch-out').on('click', function(e){
        console.log(e.target);
        
    })
    $('.no-punch-in').on('click', function(e){
        console.log(e.target);
        
    })
}


function make_support_issue(frm, checkin_type){
    let user = frm.doc.for_user;
    frappe.call('one_fm.api.doc_methods.notification_log.make_support_issue', {user, checkin_type});
}   