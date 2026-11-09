// Copyright (c) 2021, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fingerprint Appointment', {
    refresh: function(frm) {
        set_field_visibility_and_requirements(frm);
    },
    employee: function(frm){
        set_employee_supervisor(frm);
    },
    pickup_location: function(frm) {
        set_field_visibility_and_requirements(frm);
    },
	
    preparing_documents: function(frm){
        set_preparing_documents_time(frm);
    },
});

var set_employee_supervisor = function(frm){
    if(frm.doc.employee){
        frappe.call({
            method: 'one_fm.utils.get_approver_user',
            args: {
                employee: frm.doc.employee,
                skip_shift_supervisor: true
            },
            callback: function(r) {
                console.log(r.message);
                if (r.message) {
                    frm.set_value('employee_supervisor', r.message);
                } else {
                    frm.set_value('employee_supervisor', '');
                }
            }
        });
    } else {
        frm.set_value('employee_supervisor', '');
    }
};

var set_preparing_documents_time= function(frm){
    if(frm.doc.preparing_documents == "Yes" && !frm.doc.preparing_documents_on){
        frm.set_value('preparing_documents_on',frappe.datetime.now_datetime());
    }
}

function set_field_visibility_and_requirements(frm) {
    if (["Pending Supervisor", "Set Pick-up as Accommodation (Supervisor)"].includes(frm.doc.workflow_state) && 
        frm.doc.required_transportation === "Yes" && 
        !frm.is_new() && frappe.session.user == frm.doc.employee_supervisor) {

        
        frm.set_df_property('pickup_location', 'hidden', 0);
        frm.set_df_property('pickup_location', 'reqd', 1);
        frm.set_df_property('roster_action', 'reqd', 1);
        frm.set_df_property('roster_action', 'hidden', 0);
        
        
        if (frm.doc.pickup_location === "Accommodation") {
            console.log("Accommodation selected");
            frm.set_df_property('accommodation', 'hidden', 0);
            frm.set_df_property('accommodation', 'reqd', 1);
            frm.set_df_property('operations_site', 'hidden', 1);
            frm.set_df_property('operations_site', 'reqd', 0);
        } else if (frm.doc.pickup_location === "Operations Site") {
            frm.set_df_property('operations_site', 'hidden', 0);
            frm.set_df_property('operations_site', 'reqd', 1);
            frm.set_df_property('accommodation', 'hidden', 1);
            frm.set_df_property('accommodation', 'reqd', 0);
        } else {
            frm.set_df_property('accommodation', 'hidden', 1);
            frm.set_df_property('accommodation', 'reqd', 0);
            frm.set_df_property('operations_site', 'hidden', 1);
            frm.set_df_property('operations_site', 'reqd', 0);
        }
    }
}