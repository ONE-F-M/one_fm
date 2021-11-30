// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Permit', {
    // onload: function(frm){
    //     set_employee_details(frm); 
    // },
    work_permit_status: function(frm){
        if (frm.doc.work_permit_status == "Rejected"){
            frm.set_value("work_permit_status","read_only",1);
        }
    },
    employee: function(frm){
        let {employee} = frm.doc.employee;
        // console.log("hi")
        if(employee){
			frappe.db.get_doc("Employee", employee)
            .then(res => {
				let {one_fm_employee_documents} = res;
				one_fm_employee_documents.forEach(function(i, v){
					if(i.document_name == "Salary Certificate"){
						frm.set_value("salary_certificate", i.attach);
					}else if(i.document_name == "Iqrar"){
						frm.set_value("iqrar", i.attach);	
					}else if(i.document_name == "Work Contract"){
						frm.set_value("work_contract", i.attach);
					}
				})
			})
        }
        set_employee_details(frm); 
    },
    work_permit_type: function(frm) {
        set_required_documents(frm);
    },
    employee: function(frm) {
        set_required_documents(frm);
    },
    refresh(frm) {
        set_button_for_medical_insurance_transfer(frm);
        set_restart_application(frm);
        set_grd_supervisor(frm);
        set_mgrp(frm);
        
    },
    pam_file: function(frm) {
        set_authorized_signatory_name_arabic(frm);
    },
    grd_operator_apply_work_permit_on_ashal: function(frm){
        set_dates_grd_operator(frm);
    },
    upload_work_permit: function(frm){
        set_upload_work_permit(frm);
    },
    attach_invoice: function(frm){
        set_upload_work_permit_invoice(frm);
    },
    approve_previous_company: function(frm){
        set_approve_previous_company(frm);
    },
    reference_number_on_pam: function(frm){
        set_work_permit_reference_time(frm);
    },
    reference_number_on_pam_registration: function(frm){
        set_work_permit_registration_reference_time(frm);
    },
    work_permit_cancellation: function(frm){
        set_attach_cancellation_on(frm);
    },
    work_permit_registration: function(frm){
        set_attach_registration_on(frm);
    },
    attach_payment_invoice: function(frm){
        set_attach_payment_time(frm);
    },
    previous_company_status: function(frm){
        set_inform_previous_company_time(frm);
    },
    attach_work_permit: function(frm){
        set_time(frm);
    },
    // reason_of_rejection: function(frm){
    //     inform_previous_company_for_rejection(frm);
    // }

   

    
});
var set_button_for_medical_insurance_transfer = function(frm){
    if(frm.doc.docstatus === 1 && frm.doc.work_permit_type == "Local Transfer" && frm.doc.workflow_state == "Completed"){
        frm.add_custom_button(__('Go to Medical Insurance'),
          	function () {
            frappe.db.get_value('Medical Insurance', {'work_permit':frm.doc.name}, 'name', (r) => {
			if (r && r.name) {
				frappe.set_route("Form", "Medical Insurance", r.name);
			}
		});
    }
).addClass('btn-primary');
}
};
var set_restart_application = function(frm){
    if(frm.doc.docstatus == 1 && frm.doc.work_permit_status == "Rejected"){
        frm.add_custom_button(__('Restart Application'), function(){
            frappe.call({
                method: "one_fm.hiring.utils.create_new_work_permit", 
                args: {
                    'work_permit': frm.doc.name
                },
                callback: function(r){
                    if(r.message){
                        var doclist = frappe.model.sync(r.message);
                        console.log(doclist)
                        frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
                    }
                },
                freeze: true,
                freeze_message: __("Creating New Work Permit ...!")
                  });
            }).addClass('btn-primary');	
    }
};
var set_mgrp = function(frm){
if (frm.doc.docstatus == 1 && frm.doc.work_permit_type == "Cancellation" && frm.doc.nationality == "Kuwaiti") {
    
    frm.add_custom_button(__('MGRP Cancellation'),
      function() {
          frappe.model.open_mapped_doc({
          method: "one_fm.grd.utils.map_to_mgrp",
          frm: frm
            });
      }).addClass('btn-primary');	
    
   
} if (frm.doc.docstatus == 1 && frm.doc.work_permit_type == "New Kuwaiti" && frm.doc.nationality == "Kuwaiti") {
    frm.add_custom_button(__('MGRP Registration'),
      function() {
          frappe.model.open_mapped_doc({
          method: "one_fm.grd.utils.map_to_mgrp",
          frm: frm
            });
      }).addClass('btn-primary');	
} 
};
var set_employee_details = function(frm){
    let {employee} = frm.doc;
    if(frm.doc.employee){
        
        frappe.db.get_doc("Employee", employee)
        .then(res => {
            let {one_fm_employee_documents} = res;
            one_fm_employee_documents.forEach(function(i, v){
                if(i.document_name == "Salary Certificate"){
                    frm.set_value("salary_certificate", i.attach);
                }else if(i.document_name == "Iqrar"){
                    frm.set_value("iqrar", i.attach);	
                }else if(i.document_name == "Work Contract"){
                    frm.set_value("work_contract", i.attach);
                }
            })
        })

        frappe.call({
            method:"frappe.client.get_value",//api calls
            args: {
                doctype:"Employee",
                filters: {
                name: frm.doc.employee
                },
                fieldname:["one_fm_duration_of_work_permit","employee_name","one_fm_nationality","one_fm_civil_id","gender","date_of_birth","work_permit_salary","pam_file_number","employee_id","valid_upto","first_name","middle_name","one_fm_third_name","last_name","one_fm_first_name_in_arabic","one_fm_second_name_in_arabic","one_fm_third_name_in_arabic","one_fm_last_name_in_arabic","one_fm_religion","marital_status","one_fm_passport_type","passport_number","one_fm_date_of_entry_in_kuwait","one_fm__highest_educational_qualification","one_fm_date_of_issuance_of_visa","one_fm_pam_designation","one_fm_salary_type","work_permit_salary","one_fm_visa_reference_number"]
            }, 
            callback: function(r) { 
        
                // set the returned value in a field
                frm.set_value('duration_of_work_permit', r.message.one_fm_duration_of_work_permit);
                frm.set_value('nationality', r.message.one_fm_nationality);
                frm.set_value('civil_id', r.message.one_fm_civil_id);
                frm.set_value('gender',r.message.gender);
                frm.set_value('date_of_birth', r.message.date_of_birth);
                frm.set_value('work_permit_salary', r.message.work_permit_salary);
                frm.set_value('pam_file_number', r.message.pam_file_number);
                frm.set_value('employee_id', r.message.employee_id);
                frm.set_value('passport_expiry_date', r.message.valid_upto);
                frm.set_value('religion', r.message.one_fm_religion);
                frm.set_value('marital_status', r.message.work_permit_salary);
                frm.set_value('passport_type', r.message.one_fm_passport_type);
                frm.set_value('passport_number', r.message.passport_number);
                frm.set_value('date_of_entry_in_kuwait', r.message.one_fm_date_of_entry_in_kuwait);
                frm.set_value('pratical_qualification', r.message.one_fm__highest_educational_qualification);
                frm.set_value('date_of_issuance_of_visa', r.message.one_fm_date_of_issuance_of_visa);
                frm.set_value('pam_designation', r.message.one_fm_pam_designation);
                frm.set_value('salary_type', r.message.one_fm_salary_type);
                frm.set_value('work_permit_salary', r.message.work_permit_salary);
                frm.set_value('first_name', r.message.first_name);
                frm.set_value('second_name', r.message.middle_name);
                frm.set_value('third_name', r.message.one_fm_third_name);
                frm.set_value('last_name', r.message.last_name);
                frm.set_value('first_name_in_arabic', r.message.one_fm_first_name_in_arabic);
                frm.set_value('second_name_in_arabic', r.message.one_fm_second_name_in_arabic);
                frm.set_value('third_name_in_arabic', r.message.one_fm_third_name_in_arabic);
                frm.set_value('last_name_in_arabic', r.message.one_fm_last_name_in_arabic);
                frm.set_value('visa_reference_number', r.message.one_fm_visa_reference_number);

            }
        })
    }
};
var set_attach_cancellation_on = function(frm){
    if(frm.doc.work_permit_cancellation){
        frm.set_value('attach_cancellation_on',frappe.datetime.now_datetime());    
    }
};
var set_attach_registration_on = function(frm){
    if(frm.doc.work_permit_registration){
        frm.set_value('attach_registration_on',frappe.datetime.now_datetime());    
    }
};
var set_approve_previous_company = function(frm){
    if(((frm.doc.approve_previous_company == "Yes") && (!frm.doc.approve_previous_company_on)))
    {
        frm.set_value('approve_previous_company_on',frappe.datetime.now_datetime());    
    }
};
var set_authorized_signatory_name_arabic = function(frm) {
    if(frm.doc.pam_file){
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: "PAM Authorized Signatory List",
                filters: { pam_file_name: frm.doc.pam_file }
            },
            callback: function(r) {
                if(r && r.message && r.message.authorized_signatory && r.message.authorized_signatory.length > 0){
                    let authorized_signatory = r.message.authorized_signatory[0];
                    frm.set_value('authorized_signatory_name_arabic', authorized_signatory.authorized_signatory_name_arabic);
                    frm.set_value('issuer_number', r.message.issuer_number);
                }
                else{
                    frm.set_value('authorized_signatory_name_arabic', '');
                    frm.set_value('issuer_number', '');
                }
            }
        });
    }
    else{
        frm.set_value('authorized_signatory_name_arabic', '');
    }
};

var set_grd_supervisor = function(frm) {
    if(frm.is_new()){
        frappe.db.get_value('GRD Settings', {name: 'GRD Settings'}, 'default_grd_supervisor', function(r) {
            if(r && r.default_grd_supervisor){
                frm.set_value('grd_supervisor', r.default_grd_supervisor);//the field in the work permit will be set based on the default_grd_supervisor field in GRD settings
            }
        });
    }
};

var set_dates_grd_operator = function(frm) 
{
	if(((frm.doc.grd_operator_apply_work_permit_on_ashal == "Yes") && (!frm.doc.grd_operator_apply_work_permit_on_ashal_date)))
    {
        frm.set_value('grd_operator_apply_work_permit_on_ashal_date',frappe.datetime.now_datetime());
        frm.set_value('work_permit_status',"Pending by Supervisor");
    }
};
var set_upload_work_permit = function(frm) //3
{
	if(((frm.doc.upload_work_permit)&&(!frm.doc.upload_work_permit_on)))
    {
        frm.set_value('upload_work_permit_on',frappe.datetime.now_datetime());
    }if(((!frm.doc.upload_work_permit)&&(frm.doc.upload_work_permit_on)))
    {
        frm.set_value('upload_work_permit_on',null);
    }
};
var set_upload_work_permit_invoice = function(frm){
    if((frm.doc.attach_invoice)&&(!frm.doc.upload_payment_invoice_on))
    {
        frm.set_value('upload_payment_invoice_on',frappe.datetime.now_datetime());
    } if((!frm.doc.attach_invoice)&&(frm.doc.upload_payment_invoice_on))
    {
        frm.set_value('upload_payment_invoice_on',null);
    }

};
var set_work_permit_reference_time = function(frm)
{
	if(frm.doc.reference_number_on_pam && !frm.doc.reference_number_set_on)
    {
        frm.set_value('reference_number_set_on',frappe.datetime.now_datetime());
    }
};
var set_work_permit_registration_reference_time = function(frm)
{
	if(frm.doc.reference_number_on_pam_registration && !frm.doc.reference_number_registration_set_on)
    {
        frm.set_value('reference_number_registration_set_on',frappe.datetime.now_datetime());
    }
};
var set_attach_payment_time = function(frm){
    if(frm.doc.attach_payment_invoice && !frm.doc.datetime_17){
        frm.set_value('datetime_17',frappe.datetime.now_datetime());
    }
};
var set_inform_previous_company_time = function(frm){
    if(frm.doc.previous_company_status && !frm.doc.inform_previous_company_on){
        frm.set_value('inform_previous_company_on',frappe.datetime.now_datetime());
    }
};
var set_time = function(frm){
    if(frm.doc.attach_work_permit && !frm.doc.attach_on){
        frm.set_value('attach_on',frappe.datetime.now_datetime());
    }
};
var set_required_documents = function(frm) {
    frm.clear_table("documents_required");
    if(frm.doc.work_permit_type && frm.doc.employee){
        frappe.call({
            doc: frm.doc,
            method: 'get_required_documents',
            callback: function(r) {
                frm.refresh_field('documents_required');
            },
            freeze: true,
            freeze_message: __('Fetching Data.')
        });
  }
    frm.refresh_field('documents_required');
};
