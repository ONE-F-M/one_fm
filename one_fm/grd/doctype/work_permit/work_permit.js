// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Permit', {
    onload: function(frm) {
		if (!frm.is_new()){
            set_employee_details(frm);     
        }      
    },
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
    refresh: function(frm) {
        set_grd_supervisor(frm);
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
    // upload_work_permit:function(frm){    //testing reading file
	// 	let file_url = frm.doc.upload_work_permit;
    //     if (file_url){
    //         frappe.call("one_fm.grd.doctype.work_permit.work_permit.import_pdf_wp_file",{file_url})
    //         .then(res => 
    //                 console.log(res)
    //         )}    
	// }

    
});
// var set_wp_status_read_only = function(frm){
//     if (frm.doc.work_permit_status == "Rejected"){
//         cur_frm.set_df_property("work_permit_status","read_only",1);
//     }
// };
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
                fieldname:["one_fm_duration_of_work_permit","employee_name","one_fm_nationality","one_fm_civil_id","gender","date_of_birth","work_permit_salary","pam_file_number","employee_id","valid_upto"]
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
            }
        })
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
