// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Permit', {
    
    onload: function(frm) {
		if (!frm.is_new()){
            set_employee_details(frm);
        }
    },
    employee: function(frm){
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
    grd_supervisor_check_and_approval_wp_online: function(frm){
        set_dates_grd_supervisor(frm);
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
                fieldname:["one_fm_duration_of_work_permit","employee_name","one_fm_nationality","one_fm_civil_id","gender","date_of_birth","work_permit_salary"]
            }, 
            callback: function(r) { 
        
                // set the returned value in a field
                frm.set_value('duration_of_work_permit', r.message.one_fm_duration_of_work_permit);
                frm.set_value('employee_name', r.message.employee_name);
                frm.set_value('nationality', r.message.one_fm_nationality);
                frm.set_value('civil_id', r.message.one_fm_civil_id);
                frm.set_value('gender',r.message.gender);
                frm.set_value('date_of_birth', r.message.date_of_birth);
                frm.set_value('work_permit_salary', r.message.work_permit_salary);
            }
        })
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
		frappe.call({
			method: 'one_fm.grd.doctype.work_permit.work_permit.set_dates',
			callback: function(r)
            {
				if(r.message)
                {
                    frm.set_value('grd_operator_apply_work_permit_on_ashal_date',r.message);
                }
            }
        });
    }
};
//Check the fixed time
var set_dates_grd_supervisor = function(frm) 
{
	if(((frm.doc.grd_supervisor_check_and_approval_wp_online == "Yes")&&(!frm.doc.grd_supervisor_check_and_approval_wp_online_date)))
    {
		frappe.call({
			method: 'one_fm.grd.doctype.work_permit.work_permit.set_dates',
			callback: function(r)
            {
				if(r.message)
                {
                    frm.set_value('grd_supervisor_check_and_approval_wp_online_date',r.message);
                    frm.set_value('work_permit_status','Submitted');
                }
            }
        });
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
