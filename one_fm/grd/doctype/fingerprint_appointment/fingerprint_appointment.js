// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fingerprint Appointment', {
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
                fieldname:["employee_name","one_fm_duration_of_work_permit","employee_name","one_fm_nationality","one_fm_civil_id","gender","date_of_birth","work_permit_salary","pam_file_number","employee_id","valid_upto"]
            }, 
            callback: function(r) { 
        
                // set the returned value in a field
                frm.set_value('civil_id', r.message.one_fm_civil_id);
                frm.set_value('full_name', r.message.employee_name);
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