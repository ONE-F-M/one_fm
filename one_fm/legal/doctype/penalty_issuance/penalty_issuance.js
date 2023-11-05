// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Penalty Issuance', {
	refresh: function(frm) {
        // get_penalty_list(frm);
		if(frm.doc.__islocal){
			get_location(frm);
            set_issuing_employee(frm);
        }	
        frm.fields_dict["penalty_issuance_details"].grid.set_column_disp(["penalty_levied"], 0);
        frm.fields_dict["penalty_issuance_details"].grid.set_column_disp(["occurence_number"], 0);
    },
    penalty_category: function(frm){
        let {penalty_category} = frm.doc;
        if(penalty_category == "Performance"){
            frm.set_df_property('shift', 'reqd', true);
            frm.set_df_property('site', 'reqd', true);
            console.log("1");
            set_employee_filters(frm);
        } else {
            frm.set_df_property('shift', 'reqd', false);
            frm.set_df_property('site', 'reqd', false); 
        }
    },
    pull_as_current: function(frm){
        if(frm.doc.docstatus < 1){
            let {penalty_occurence_time, location} = frm.doc;
            location && penalty_occurence_time && get_current_penalty_location(frm);
        }
    },
    penalty_occurence_time: function(frm){
        //Add 10 days validation
        let {penalty_occurence_time, doctype, name, shift} = frm.doc;
        frm.clear_table('employees');
        console.log("2");
        set_employee_filters(frm);
        if(penalty_occurence_time !== undefined){
            let now = moment();
            let threshold_datetime = moment();
            threshold_datetime.subtract(10, 'days');
            let penalty_datetime = moment(penalty_occurence_time);
            if(penalty_datetime < threshold_datetime){
                frappe.model.set_value(doctype, name, "penalty_occurence_time", moment().tz('Asia/Kuwait').format('YYYY-MM-DD HH:mm:ss'));
                frappe.throw(__("Penalty can only be issued for the previous 10 days."));
            }
            if(penalty_datetime > now){
                frappe.model.set_value(doctype, name, "penalty_occurence_time", moment().tz('Asia/Kuwait').format('YYYY-MM-DD HH:mm:ss'));
                frappe.throw(__("Penalty time cannot be in future."));    
            }
        }
    },
    shift: function(frm){
        frm.clear_table('employees');
        frappe.model.set_value(frm.doctype, frm.docname, "different_location", 1);
        console.log("3");
        set_employee_filters(frm);
    }

});

function get_location(frm){
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            position => {
				let {latitude, longitude} = position.coords;
				frappe.model.set_value(frm.doc.doctype, frm.doc.name, "location", `${latitude},${longitude}`);
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

function get_current_penalty_location(frm){
    let {penalty_occurence_time, location} = frm.doc;
    frappe.xcall('one_fm.legal.doctype.penalty_issuance.penalty_issuance.get_current_penalty_location', {
        location, penalty_occurence_time
    }).then(res => {
        if(res){
            let {shift, site, site_location, project} = res;
            frappe.model.set_value(frm.doctype, frm.docname, "site", site);
            frappe.model.set_value(frm.doctype, frm.docname, "site_location", site_location);
            frappe.model.set_value(frm.doctype, frm.docname, "project", project);
            frappe.model.set_value(frm.doctype, frm.docname, "shift", shift);
        }
    }).catch(err => {
        frappe.model.set_value(frm.doctype, frm.docname, "different_location", 1);  
    })
}

function set_employee_filters(frm){
    let {shift, penalty_occurence_time} = frm.doc;
    frm.refresh_field('employees');
    if(shift && penalty_occurence_time){
        frm.set_query("employee_id", "employees" ,function() {
            return {
                query: "one_fm.legal.doctype.penalty_issuance.penalty_issuance.filter_employees",
                filters: {shift, penalty_occurence_time}
            }
        });	
    }
}

function set_issuing_employee(frm){
    frappe.db.get_value("Employee", {"user_id": frappe.session.user}, ["name", "employee_name","designation"])
    .then(res => {
        if(res.message){
            console.log(res);
            frappe.model.set_value(frm.doctype, frm.docname, "issuing_employee", res.message.name);
            frappe.model.set_value(frm.doctype, frm.docname, "employee_name", res.message.employee_name);
            frappe.model.set_value(frm.doctype, frm.docname, "designation", res.message.designation);
            frm.refresh_fields('issuing_employee');
        }
    })
}
// function get_penalty_list(frm){
//     frappe.xcall('one_fm.legal.doctype.penalty_issuance.penalty_issuance.get_penalty_list')
//     .then(res => {
//         console.log(res);
//     }) 
// }