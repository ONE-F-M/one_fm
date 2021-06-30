frappe.ui.form.on('PIFSS Form 103', {
	onload: function(frm){
		frm.set_query("employee", function() {
			return {
				"filters": {
					"one_fm_nationality": "Kuwaiti",
				}
			};
		});
		frm.set_query("pifss_authorized_signatory", function() {
			return {
				"filters": {
					"company": "ONE Facilities Management",
					"is_active": 1,
				}
			};
		})
		// if(frm.doc.__islocal){
		// 	frappe.db.get_value("Company", {"name": frappe.user_defaults.company} ,["company_name_arabic", "pifss_registration_no"], 
		// 	function(res){
		// 		console.log(res)
		// 		let {company_name_arabic, pifss_registration_no} = res;
		// 		frm.set_value("company_name_arabic", company_name_arabic);
		// 		frm.set_value("company_pifss_registration_no", pifss_registration_no);
		// 	})

		// }	
	},
	
	refresh: function(frm){
		if(!frm.doc.__islocal){
			frm.set_df_property("request_type","read_only", 1);
		} 
		if(frm.doc.pifss_authorized_signatory){
			frappe.call({
				method: "one_fm.grd.doctype.pifss_form_103.pifss_form_103.get_signatory_name",
				args:{
					'parent': frm.doc.pifss_authorized_signatory,
					},
				callback:function(r){
					console.log(r.message);
					frm.set_df_property('signatory_name', "options", r.message);
					frm.refresh_field("signatory_name");
					}
				});
		}
		else{
			frm.set_df_property('signatory_name', "options", null);
			frm.refresh_field("signatory_name");
		}
	},
	pifss_authorized_signatory: function(frm){
		if(frm.doc.pifss_authorized_signatory){
			frappe.call({
				method: "one_fm.grd.doctype.pifss_form_103.pifss_form_103.get_signatory_name",
				args:{
					'parent': frm.doc.pifss_authorized_signatory,
					},
				callback:function(r){
					console.log(r.message);
					frm.set_df_property('signatory_name', "options", r.message);
					frm.refresh_field("signatory_name");
					}
				});
		}
		else{
			frm.set_df_property('signatory_name', "options", null);
			frm.refresh_field("signatory_name");
		}
	},
	employee: function(frm) {
		let {employee, request_type} = frm.doc;
		if(employee && request_type === "Registration"){
			frappe.db.get_doc("Employee", employee)
			.then(res => {
				let {one_fm_employee_documents} = res;
				one_fm_employee_documents.forEach(function(i, v){
					if(i.document_name == "Birth Certificate"){
						frm.set_value("date_of_birth_certificate", i.attach);
					}else if(i.document_name == "Nationality Proof"){
						frm.set_value("nationality_proof", i.attach);	
					}else if(i.document_name == "Civil ID"){
						frm.set_value("civil_id_copy", i.attach);
					}else if(i.document_name == "Work Contract"){
						frm.set_value("employment_contract", i.attach);
					}else if(i.document_name == "Social Security Clearance"){
						frm.set_value("social_security_clearance", i.attach);
					}
				})
			})
		}
		set_employee_details(frm);

	},
	request_type: function(frm) {
		let {request_type} = frm.doc;
		if(request_type === "Registration"){
			frm.set_value("naming_series", "REG-.{employee}.-");
		}else if(request_type === "End of Service"){
			frm.set_value("naming_series", "END-.{employee}.-");
		}
	},
	signatory_name: function(frm){
		if(frm.doc.signatory_name){
		frappe.call({
			method: "one_fm.grd.doctype.pifss_form_103.pifss_form_103.get_signatory_user",
			args:{
				'user_name':frm.doc.signatory_name,
				},
			callback:function(r){
				console.log(r.message)
				frm.set_value('user',r.message)
				frm.refresh_field("user");
				}
			});
	}
	else{
		//frm.set_df_property('user', "options", null);
		frm.set_value('user'," ")
		frm.refresh_field("user");
	}
},
user: function(frm){
	frm.set_value('notify_for_signature',0)
	frm.set_value('signature_date',frappe.datetime.now_date())
	frm.set_value('employee_signature_date',frappe.datetime.now_date())
	
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
                fieldname:["employee_name","one_fm_first_name_in_arabic","one_fm_second_name_in_arabic","one_fm_third_name_in_arabic","one_fm_last_name_in_arabic","one_fm_civil_id","cell_number","permanent_address","date_of_birth","nationality_no","nationality_subject","date_of_naturalization","date_of_joining","one_fm_pam_designation","one_fm_basic_salary"]
            }, 
            callback: function(r) { 
        
                // set the returned value in a field
				frm.set_value('employee_name', r.employee_name);
				frm.set_value('first_name', r.one_fm_first_name_in_arabic);
				frm.set_value('second_name', r.one_fm_second_name_in_arabic);
				frm.set_value('third_name', r.one_fm_third_name_in_arabic);
				frm.set_value('fourth_name', r.one_fm_last_name_in_arabic);
				frm.set_value('civil_id', r.message.one_fm_civil_id);
				frm.set_value('mobile', r.cell_number);
				frm.set_value('address', r.permanent_address);
				frm.set_value('date_of_birth', r.date_of_birth);
				frm.set_value('nationality_no', r.nationality_no);
				frm.set_value('nationality_subject', r.nationality_subject);
				frm.set_value('date_of_naturalization', r.date_of_naturalization);
                // frm.set_value('duration_of_work_permit', r.message.one_fm_duration_of_work_permit);
                frm.set_value('date_of_joining', r.message.date_of_joining);
				frm.set_value('subscription_start_date', r.message.date_of_joining);
				frm.set_value('position', r.message.one_fm_pam_designation);
				frm.set_value('employment_contract', r.message.one_fm_basic_salary);
            }
        })
    }
};
var set_draft_values = function(frm){
	if(frm.doc.status == "Draft"){
		frm.set_value('date_of_request',null)
		frm.set_value('date_of_registeration',null)
		frm.set_value('date_of_acceptance',null)
	}
};
var all_documents_are_attached = function(frm){
	if(!frm.doc.employment_contract && !frm.doc.civil_id_copy && !frm.doc.social_security_clearance && !frm.doc.date_of_birth_certificate && !frm.doc.nationality_proof){
		frappe.msgprint({
			title: __('Notification'),
			indicator: 'green',
			message: __('All attachments need to be set')
		});
	}
};
var  check_upload_signed_form = function(frm){
	if (frm.doc.status == "Draft" && !frm.doc.attach_signed_form){
		upload_signed_form(frm);
	}if (frm.doc.status == "Draft" && frm.doc.attach_signed_form){
		frm.set_value('date_of_request',frappe.datetime.now_date())
	}
};
var upload_signed_form = function(frm){
	frappe.msgprint({
		title: __('Notification'),
		indicator: 'green',
		message: __('You Need to Attach 103 form to notify GRD team to proceed')
	});
};
var set_register_number = function(frm){
	frappe.msgprint({
		title: __('Notification'),
		indicator: 'green',
		message: __('Registration Application Number is Required')
	});
};
