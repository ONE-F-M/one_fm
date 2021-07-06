// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fingerprint Appointment', {
	onload: function(frm) {
		if (!frm.is_new()){
            set_employee_details(frm);  
        }      
    },
    refresh: function(frm){
        frm.add_custom_button(('Operation Department'),function(){
            let Operations = frm.selected_doc.operations_manager;
            frappe.call({
                method: "one_fm.grd.utils.notify", 
                args: {
                    'name':frm.selected_doc.name,
                    'email':Operations,
                    'civilid':frm.selected_doc.civil_id,
                    'date_time':frm.selected_doc.date_and_time_confirmation,
                },
                callback: function(r) {
                    frm.set_value("notify_operations",1);
                    frappe.msgprint({
                        title: __('Notification'),
                        indicator: 'green',
                        message: __('Notification sent Sucessfully to Operation Department')
                        });
                }
            })

        },("Notify"));

        frm.add_custom_button(('Transport Department'),function(){
            let transportation = frm.selected_doc.transport_user;
            frappe.call({
                
                method: "one_fm.grd.utils.notify", 
                args: {
                    'name':frm.selected_doc.name,
                    'email':transportation,
                    'civilid':frm.selected_doc.civil_id,
                    'date_time':frm.selected_doc.date_and_time_confirmation,
                },
                callback: function(r) {
                    frm.set_value("notify_transport",1);
                    frm.set_value("required_transportation","Yes");
                    frappe.msgprint({
                        title: __('Notification'),
                        indicator: 'green',
                        message: __('Notification sent Sucessfully to Transport Department')
                        });
                }
            })
        
        },("Notify"));
        
    },
    employee: function(frm){
        set_employee_details(frm);  
    },
	
    preparing_documents: function(frm){
        set_preparing_documents_time(frm);
    }
});
var set_employee_details = function(frm){
    if(frm.doc.employee){
        frappe.call({
            method:"frappe.client.get_value",//api calls
            args: {
                doctype:"Employee",
                filters: {
                name: frm.doc.employee
                },
                fieldname:["one_fm_duration_of_work_permit","employee_name","one_fm_nationality","one_fm_civil_id","gender","date_of_birth","work_permit_salary","pam_file_number","employee_id","valid_upto"]
            }, 
            callback: function(r) { 
        
                // set the returned value in a field
                frm.set_value('civil_id', r.message.one_fm_civil_id);
				frm.set_value('first_name_arabic', r.message.one_fm_first_name_in_arabic);
                frm.set_value('second_name_arabic', r.message.one_fm_second_name_in_arabic);
                frm.set_value('third_name_arabic', r.message.one_fm_third_name_in_arabic);
                frm.set_value('last_name_arabic', r.message.one_fm_last_name_in_arabic);
                frm.set_value('employee_id',r.message.employee_id);
                frm.set_value('first_name_english', r.message.first_name);
                frm.set_value('second_name_english', r.message.middle_name);
                frm.set_value('third_name_english', r.message.one_fm_third_name);
                frm.set_value('last_name_english', r.message.last_name);
                frm.set_value('nationality', r.message.one_fm_nationality);
            }
        })
    }
};
var set_preparing_documents_time= function(frm){
    if(frm.doc.preparing_documents == "Yes" && !frm.doc.preparing_documents_on){
        frm.set_value('preparing_documents_on',frappe.datetime.now_datetime());
    }
}