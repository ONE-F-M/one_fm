// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Medical Insurance', {
    refresh: function(frm){
        // set_css(frm);
    },
    onload: function(frm) {
		if (!frm.is_new()){
            set_employee_details(frm);
            set_insurance_type(frm);
        }
        if(frm.is_new()){
            set_insurance_type(frm);
        }
    },
    work_permit: function(frm){
        set_employee_details(frm);
        set_insurance_type(frm);
    },
    civil_id: function(frm) {
        if(frm.doc.civil_id){
            frappe.call({
                method: 'one_fm.grd.doctype.medical_insurance.medical_insurance.get_employee_data_from_civil_id',
                args:{'civil_id': frm.doc.civil_id},
                callback: function(r) {
                    if(r && r.message){
                        var data = r.message;
                        // frm.set_value('employee_name', data.employee_name);
                        frm.set_value('gender', data.gender);
                        frm.set_value('nationality', data.one_fm_nationality);
                        //frm.set_value('passport_expiry_date', data.valid_upto);
                    }
                    frm.refresh_fields();
                },
                freaze: true,
                freaze_message: __("Fetching Data with CIVIL ID")
            });
        }
    },
    apply_medical_insurance_online: function(frm){
        set_apply_medical_insurance_online_date(frm);

    },
    // submission_of_application: function(frm){
    //     set_submission_of_application(frm);

    // },
    upload_medical_insurance: function(frm){
        set_upload_medical_insurance(frm);

    },
    upload_payment_invoice: function(frm){
        set_upload_payment_invoice(frm);
    }
});

frappe.ui.form.on('Medical Insurance Item', {
    civil_id: function(frm, cdt, cdn) {
        var child = locals[cdt][cdn];
        if(child.civil_id){
            frappe.call({
                method: 'one_fm.grd.doctype.medical_insurance.medical_insurance.get_employee_data_from_civil_id',
                args:{'civil_id': child.civil_id},
                callback: function(r) {
                    if(r && r.message){
                        var data = r.message;
                        frappe.model.set_value(cdt, cdn, 'employee_name', data.employee_name);
                        frappe.model.set_value(cdt, cdn, 'gender', data.gender);
                        frappe.model.set_value(cdt, cdn, 'nationality', data.one_fm_nationality);
                        //frappe.model.set_value(cdt, cdn, 'passport_expiry_date', data.valid_upto);
                    }
                    frm.refresh_fields();
                },
                freaze: true,
                freaze_message: __("Fetching Data with CIVIL ID")
            });
        }
    }
});
var set_css = function (frm) {
    $('input[data-fieldname="work_permit"]').css("color","green")
    //let el = document.querySelectorAll("[data-fieldname=‘work_permit’]")[1].style.backgroundColor =“green”;
    //let fl = document.querySelectorAll("[data-fieldname=‘phone’]")[1].style.backgroundColor =“mediumaquamarine”;
    };

var set_apply_medical_insurance_online_date = function(frm) //1
{
	if(((frm.doc.apply_medical_insurance_online == "Yes")&&(!frm.doc.apply_medical_insurance_online_date)))
    {
		
        frm.set_value('apply_medical_insurance_online_date',frappe.datetime.now_datetime())
    }
};
var set_upload_payment_invoice = function(frm){
    
    if(((frm.doc.upload_payment_invoice)&&(!frm.doc.upload_payment_invoice_on)))
    {
        frm.set_value('upload_payment_invoice_on',frappe.datetime.now_datetime())
    }
};
var set_upload_medical_insurance = function(frm) //3
{
	if(((frm.doc.upload_medical_insurance)&&(!frm.doc.upload_medical_insurance_date)))
    {
		
        frm.set_value('upload_medical_insurance_date',frappe.datetime.now_datetime())
    }
};
var set_employee_details = function(frm){
    if(frm.doc.work_permit){
        frappe.call({
            method:"frappe.client.get_value",//api calls
            args: {
                doctype:"Work Permit",
                filters: {
                name: frm.doc.work_permit
                },
                fieldname:["civil_id","pam_file_number","gender","nationality","duration_of_work_permit","passport_expiry_date"]
            }, 
            callback: function(r) { 
        
                // set the returned value in a field
                frm.set_value('civil_id', r.message.civil_id);
                frm.set_value('gender', r.message.gender);
                frm.set_value('nationality',r.message.nationality);
                frm.set_value('no_of_years', r.message.duration_of_work_permit);
                frm.set_value('passport_expiry_date',r.message.passport_expiry_date);
            }
        });
    }
};
var set_insurance_type = function(frm){
    if(frm.doc.work_permit){
        frappe.call({
            method:"frappe.client.get_value",//api calls
            args: {
                doctype:"Work Permit",
                filters: {
                name: frm.doc.work_permit
                },
                fieldname:["pam_file_number"]
            }, 
            callback: function(r) { 
                if(r.message.pam_file_number == "20201800005" || r.message.pam_file_number == "15201800010"){
                    frm.set_value('insurance_type', "18 - Govt Project Visa (Private)");
                }
                if(r.message.pam_file_number == "100068481"){
                    frm.set_value('insurance_type', "18 - Work Visa Private");
                }
            }
        })
    }

};

