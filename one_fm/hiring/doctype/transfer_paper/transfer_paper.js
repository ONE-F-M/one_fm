
// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transfer Paper', {
    onload: function(frm){
        set_wp_status(frm);
    },
    refresh: function(frm) {
        let doc_name = frm.doc.name;
        // console.log(doc_name)
        if(frm.doc.docstatus==1) {
                frm.add_custom_button(__('Re-Send'), function() { 
                    frappe.xcall('one_fm.hiring.doctype.transfer_paper.transfer_paper.resend_new_wp_record',{doc_name})
                    frappe.msgprint({
                        title: __('Notification'),
                        indicator: 'green',
                        message: __('Old Work Permit Record is rejected / created new record Sucessfully')
                    });
                })
                frm.add_custom_button(__('Close'), function() {
                    frappe.xcall('one_fm.hiring.doctype.transfer_paper.transfer_paper.closed_old_wp_record',{doc_name})
                
                frappe.msgprint({
                    title: __('Notification'),
                    indicator: 'green',
                    message: __('Previous Work Permit Record is Closed Sucessfully')
                    });
                })
            
        }
    if(frm.doc.pas){
        frappe.call({
            method:"frappe.client.get_value",//api calls
            args: {
                doctype:"PAM Authorized Signatory List",
                filters: {
                name: frm.doc.pas
                },
                fieldname:["company_name_arabic","pam_issuer_number","pam_file_number"]
            }, 
            callback: function(r) { 
        
                // set the returned value in a field
                frm.set_value('company_trade_name_arabic', r.message.company_name_arabic);
                frm.set_value('issuer_number', r.message.pam_issuer_number);
                frm.set_value('pam_file_number', r.message.pam_file_number);

            }
        })
    }
    if(frm.doc.applicant){
        frappe.call({
            method:"frappe.client.get_value",//api calls
            args: {
                doctype:"Job Applicant",
                filters: {
                name: frm.doc.applicant
                },
                fieldname:["one_fm_pam_file_number","one_fm_previous_company_trade_name_in_arabic","one_fm__previous_company_authorized_signatory_name_arabic","one_fm_previous_designation","one_fm_previous_company_contract_file_number","one_fm_previous_company_issuer_number","one_fm_previous_company_pam_file_number","one_fm_last_working_date","one_fm_work_permit_salary","one_fm_duration_of_work_permit","one_fm_first_name","one_fm_second_name","one_fm_third_name","one_fm_last_name","one_fm_first_name_in_arabic","one_fm_second_name_in_arabic","one_fm_third_name_in_arabic","one_fm_last_name_in_arabic","one_fm_date_of_birth","one_fm_gender","one_fm_marital_status","one_fm_religion","one_fm_nationality","one_fm_passport_type","one_fm_passport_number","one_fm_educational_qualification","one_fm_passport_expire","one_fm_cid_number","one_fm_pam_designation","one_fm_work_permit_salary","one_fm_date_of_entry"]
            }, 
            callback: function(r) { 
        
                // set the returned value in a field
                frm.set_value('pam_file_number', r.message.one_fm_pam_file_number);
                frm.set_value('previous_company_trade_name_in_arabic', r.message.one_fm_previous_company_trade_name_in_arabic);
                frm.set_value('company_trade_name_arabic', r.message.company_name_arabic);
                frm.set_value('previous_company_authorized_signatory_name_arabic', r.message.one_fm__previous_company_authorized_signatory_name_arabic);
                frm.set_value('previous_company_pam_designation', r.message.one_fm_previous_designation);
                frm.set_value('previous_company_contract_file_number', r.message.one_fm_previous_company_contract_file_number);   
                frm.set_value('previous_company_issuer_number', r.message.one_fm_previous_company_issuer_number);               
                frm.set_value('previous_company_pam_file_number', r.message.one_fm_previous_company_pam_file_number);
                frm.set_value('end_work_date', r.message.one_fm_last_working_date);
                frm.set_value('previous_company_work_permit_salary', r.message.one_fm_work_permit_salary);
                frm.set_value('previous_company_duration_of_work_permit', r.message.one_fm_duration_of_work_permit);
                frm.set_value('first_name', r.message.one_fm_first_name);
                frm.set_value('second_name', r.message.one_fm_second_name);
                frm.set_value('third_name', r.message.one_fm_third_name);
                frm.set_value('last_name', r.message.one_fm_last_name);
                frm.set_value('first_name_in_arabic', r.message.one_fm_first_name_in_arabic);
                frm.set_value('second_name_in_arabic', r.message.one_fm_second_name_in_arabic);
                frm.set_value('third_name_in_arabic', r.message.one_fm_third_name_in_arabic);
                frm.set_value('last_name_in_arabic', r.message.one_fm_last_name_in_arabic);
                frm.set_value('date_of_birth', r.message.one_fm_date_of_birth);
                frm.set_value('gender', r.message.one_fm_gender);
                frm.set_value('religion', r.message.one_fm_religion);
                frm.set_value('marital_status', r.message.one_fm_marital_status);
                frm.set_value('nationality', r.message.one_fm_nationality);
                frm.set_value('passport_type', r.message.one_fm_passport_type);
                frm.set_value('passport_number', r.message.one_fm_passport_number);
                frm.set_value('pratical_qualification', r.message.one_fm_educational_qualification);
                frm.set_value('passport_expiry_date', r.message.one_fm_passport_expire);
                frm.set_value('civil_id', r.message.one_fm_cid_number);
                frm.set_value('pam_designation', r.message.one_fm_pam_designation);
                frm.set_value('civil_id', r.message.one_fm_cid_number);
                // frm.set_value('work_permit_salary', r.message.one_fm_work_permit_salary);
                // frm.set_value('date_of_entry_in_kuwait', r.message.one_fm_date_of_entry);
            }
        })
    }

    },
    // new_page_preview: function(printit) {
    //     var me = this;
    //     //var doc = frappe.get_doc(me.frm.doc.doctype, me.frm.doc.name)
    
    //     if (me.frm.doc.print < 1){
    //         frappe.call({
    //                 "method": "frappe.client.set_value",
    //                 "args": {
    //                             "doctype": me.frm.doc.doctype,
    //                             "name": me.frm.doc.name,
    //                             "fieldname": "print",
    //                             "value": me.frm.doc.print + 1
    //                         }	
    //             });
    
    //         }
    //     },
    
});
var set_wp_status = function(frm){
    frappe.call({
        method:"frappe.client.get_value",//api calls
        args: {
            doctype:"Work Permit",
            filters: {
            name: frm.doc.employee
            },
            fieldname:["work_permit_status"]
        }, 
        callback: function(r) { 
            frm.set_value('work_permit_status', r.message.work_permit_status);
        }
    })
}
