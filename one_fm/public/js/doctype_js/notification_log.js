frappe.ui.form.on('Notification Log', {
    refresh: function(frm){
        checkin_events(frm);
    },
});


function checkin_events(frm){
    // $('#punch-error.punch-in').on('click', function(e){
    //     console.log(e);
    //     frappe.msgprint(__("Please inform your in-line supervisor in person or via direct call about the issue and confirm attendance."))
    //     make_support_issue(frm, "in");
    // })
    // $('#punch-error.punch-out').on('click', function(e){
    //     console.log(e.target);
    //     frappe.msgprint(__("Please inform your in-line supervisor in person or via direct call about the issue and confirm your exit."))
    //     make_support_issue(frm, "out");
    // })
    $('.early-punch-out').on('click', function(e){
        console.log(e.target);
        let penalty_code = "103";
        issue_penalty(e.target, penalty_code);
    });
    $('.late-punch-in').on('click', function(e){
        console.log(e.target);
        let penalty_code = "102";
        issue_penalty(e.target, penalty_code);
    });
    $('.no-punch-in').on('click', function(e){
        console.log(e.target); 
        let penalty_code = "106";
        issue_penalty(e.target, penalty_code);
    });
}

function issue_penalty(element, penalty_code){
    let [employee,date,shift] = $(element).attr('id').split("_");
    let issuing_user = frappe.session.user;
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            position => {
                let {latitude, longitude} = position.coords;
                let penalty_location = `${latitude},${longitude}`;
                // frappe.model.set_value(frm.doc.doctype, frm.doc.name, "location", `${latitude},${longitude}`);
                frappe.xcall('one_fm.api.tasks.issue_penalty',{
                    employee, date, penalty_code, shift, issuing_user, penalty_location
                })
            },
            error => {
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        frappe.msgprint(__(`
                            <b>Please enable location permissions to proceed further.</b>
                            1. <b>Firefox</b>:
                            <br> Tools > Page Info > Permissions > Access Your Location. Select Always Ask.<br>
                            2. <b>Chrome</b>: 
                            <br> Hamburger Menu > Settings > Show advanced settings.<br> 
                                In the Privacy section, click Content Settings. <br>
                                In the resulting dialog, find the Location section and select Ask when a site tries to... .<br>
                                Finally, click Manage Exceptions and remove the permissions you granted to the sites you are interested in.<br><br>
                            <b>After enabling, click on the <i>Get Location</i> button</b> or <b>Reload</b>.`));
                        break;
                    case error.POSITION_UNAVAILABLE:
                        frappe.msgprint(__("Location information is unavailable."));
                        break;
                    case error.TIMEOUT:
                        frappe.msgprint(__("The request to get user location timed out."));
                        break;
                    case error.UNKNOWN_ERROR:
                        frappe.msgprint(__("An unknown error occurred."));
                        break;
                }
            }
        );
    } else { 
        frappe.msgprint(__("Geolocation is not supported by this browser."));
    }
}
// function make_support_issue(frm, checkin_type){
//     let user = frm.doc.for_user;
//     frappe.call('one_fm.api.doc_methods.notification_log.make_support_issue', {user, checkin_type});
// }   