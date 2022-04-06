// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt
frappe.ui.form.on('PACI', {
	// onload: function(frm){
    //     set_employee_details(frm);
    // },
    employee: function(frm){
        set_employee_details(frm);
    },
	upload_civil_id_payment: function(frm){
		set_upload_civil_id_payment(frm);
        set_status(frm);
	},
	upload_civil_id: function(frm){
		set_upload_civil_id(frm);
	},

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
                fieldname:["one_fm_first_name_in_arabic","one_fm_second_name_in_arabic","one_fm_third_name_in_arabic","one_fm_last_name_in_arabic",
				"first_name","middle_name","one_fm_third_name","last_name","one_fm_civil_id",
				"passport_number","one_fm_pam_designation","one_fm_nationality","employee_id","residency_expiry_date"]
            }, 
            callback: function(r) { 
        
                // set the returned value in a field
                frm.set_value('first_name_arabic', r.message.one_fm_first_name_in_arabic);
                frm.set_value('second_name_arabic', r.message.one_fm_second_name_in_arabic);
                frm.set_value('third_name_arabic', r.message.one_fm_third_name_in_arabic);
                frm.set_value('last_name_arabic', r.message.one_fm_last_name_in_arabic);
                frm.set_value('first_name_english',r.message.first_name);
                frm.set_value('second_name_english', r.message.middle_name);
                frm.set_value('third_name_english', r.message.one_fm_third_name);
                frm.set_value('last_name_english',r.message.last_name);
                frm.set_value('civil_id', r.message.one_fm_civil_id);
                frm.set_value('passport_number', r.message.passport_number);
                frm.set_value('pam_designation', r.message.one_fm_pam_designation);
                frm.set_value('nationality', r.message.one_fm_nationality);
				frm.set_value('employee_id',r,message.employee_id);
                frm.set_value('residency_expiry_date',r.message.residency_expiry_date);
               
            }
        })
    }
};
var set_upload_civil_id_payment = function(frm)
{//2
	if((frm.doc.upload_civil_id_payment) && (!frm.doc.upload_civil_id_payment_datetime))
	{ 
		frm.set_value('upload_civil_id_payment_datetime',frappe.datetime.now_datetime());
	}if((!frm.doc.upload_civil_id_payment) && (frm.doc.upload_civil_id_payment_datetime))
	{
		frm.set_value('upload_civil_id_payment_datetime',null);
	}
};
var set_upload_civil_id = function(frm)
{//3
	if((frm.doc.upload_civil_id) && (!frm.doc.upload_civil_id_datetime))
	{
		frm.set_value('upload_civil_id_datetime',frappe.datetime.now_datetime());
	}if((!frm.doc.upload_civil_id) && (frm.doc.upload_civil_id_datetime))
	{
		frm.set_value('upload_civil_id_datetime',null);
	}
};
var set_status = function(frm)
{
    if (frm.doc.upload_civil_id_payment){
        frm.set_value('paci_status',"Under-Process");
    }
};